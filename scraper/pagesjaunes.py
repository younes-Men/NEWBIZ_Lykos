import logging
import re
from typing import Optional, Dict, List
import requests
from urllib.parse import quote

logger = logging.getLogger(__name__)


class PagesJaunesClient:
    """
    Client pour l'API Pages Jaunes pour récupérer les numéros de téléphone des entreprises.
    """

    BASE_URL = "https://api.pagesjaunes.fr/v1"
    SEARCH_PATH = "/search"
    PRO_PATH = "/pros"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise le client Pages Jaunes.
        
        Args:
            api_key: Clé API Pages Jaunes (si nécessaire)
        """
        self.api_key = api_key

    def search_pro(self, nom: str, adresse: str = "", code_postal: str = "") -> Optional[str]:
        """
        Recherche une entreprise sur Pages Jaunes pour obtenir son pro_id.
        Essaie plusieurs méthodes de recherche.
        
        Args:
            nom: Nom de l'entreprise
            adresse: Adresse complète
            code_postal: Code postal (extrait de l'adresse si fourni)
            
        Returns:
            pro_id si trouvé, None sinon
        """
        if not nom:
            return None
        
        # Extraire le code postal de l'adresse si fourni
        if not code_postal and adresse:
            cp_match = re.search(r'\b(\d{5})\b', adresse)
            if cp_match:
                code_postal = cp_match.group(1)
        
        # Essayer différentes méthodes de recherche
        pro_id = None
        
        # Méthode 1: API de recherche Pages Jaunes
        try:
            params = {
                "what": nom,
                "where": code_postal if code_postal else adresse
            }
            
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            else:
                # Certaines API utilisent des headers différents
                headers["Accept"] = "application/json"
            
            # Essayer différents endpoints de recherche possibles
            search_endpoints = [
                f"{self.BASE_URL}{self.SEARCH_PATH}",
                f"{self.BASE_URL}/search",
                f"{self.BASE_URL}/pros/search"
            ]
            
            for url in search_endpoints:
                try:
                    response = requests.get(url, params=params, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Chercher le pro_id dans différentes structures de réponse
                        if isinstance(data, dict):
                            # Structure: {"results": [{"id": "...", ...}, ...]}
                            results = data.get("results") or data.get("data") or data.get("items") or []
                            if results and isinstance(results, list):
                                for result in results:
                                    if isinstance(result, dict):
                                        pro_id = result.get("id") or result.get("pro_id") or result.get("proId")
                                        if pro_id:
                                            return str(pro_id)
                            
                            # Structure: {"pro_id": "...", ...} directement
                            pro_id = data.get("id") or data.get("pro_id") or data.get("proId")
                            if pro_id:
                                return str(pro_id)
                        
                        elif isinstance(data, list):
                            # Structure: [{"id": "...", ...}, ...]
                            for result in data:
                                if isinstance(result, dict):
                                    pro_id = result.get("id") or result.get("pro_id") or result.get("proId")
                                    if pro_id:
                                        return str(pro_id)
                    
                    elif response.status_code == 404:
                        # Endpoint n'existe pas, essayer le suivant
                        continue
                        
                except requests.exceptions.RequestException:
                    # Erreur de requête, essayer le suivant
                    continue
            
        except Exception as e:
            logger.debug(f"Erreur lors de la recherche API Pages Jaunes pour {nom}: {e}")
        
        # Méthode 2: Essayer de trouver le pro_id via le site web (si nécessaire)
        # Cette méthode pourrait être ajoutée plus tard si l'API ne fonctionne pas
        
        return None

    def get_pro_phone(self, pro_id: str) -> Optional[str]:
        """
        Récupère le numéro de téléphone d'une entreprise via son pro_id.
        
        Args:
            pro_id: Identifiant de l'entreprise sur Pages Jaunes
            
        Returns:
            Numéro de téléphone formaté ou None
        """
        if not pro_id:
            return None
        
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            else:
                headers["Accept"] = "application/json"
            
            url = f"{self.BASE_URL}{self.PRO_PATH}/{pro_id}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extraire le numéro de téléphone selon différentes structures possibles
                phone = None
                
                if isinstance(data, dict):
                    # Chercher dans différents chemins possibles
                    paths_to_check = [
                        ["coordonnees", "telephone"],
                        ["coordonnees", "phone"],
                        ["coordonnees", "tel"],
                        ["contact", "telephone"],
                        ["contact", "phone"],
                        ["contact", "tel"],
                        ["phone"],
                        ["telephone"],
                        ["tel"],
                        ["phones", 0],  # Premier élément si c'est une liste
                        ["telephones", 0],
                    ]
                    
                    for path in paths_to_check:
                        value = data
                        try:
                            for key in path:
                                if isinstance(value, (list, tuple)) and isinstance(key, int):
                                    if 0 <= key < len(value):
                                        value = value[key]
                                    else:
                                        value = None
                                        break
                                elif isinstance(value, dict):
                                    value = value.get(key)
                                else:
                                    value = None
                                    break
                            
                            if value and isinstance(value, str) and value.strip():
                                phone = value.strip()
                                break
                        except (KeyError, IndexError, TypeError, AttributeError):
                            continue
                    
                    # Formater le numéro si trouvé
                    if phone:
                        return self._format_phone(phone)
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"Erreur de requête lors de la récupération du téléphone pour pro_id {pro_id}: {e}")
            return None
        except Exception as e:
            logger.debug(f"Erreur lors de la récupération du téléphone pour pro_id {pro_id}: {e}")
            return None

    def get_phone_for_company(self, nom: str, adresse: str = "") -> Optional[str]:
        """
        Récupère le numéro de téléphone d'une entreprise en combinant recherche et récupération.
        
        Args:
            nom: Nom de l'entreprise
            adresse: Adresse complète
            
        Returns:
            Numéro de téléphone formaté ou None
        """
        # Recherche du pro_id
        code_postal = ""
        if adresse:
            cp_match = re.search(r'\b(\d{5})\b', adresse)
            if cp_match:
                code_postal = cp_match.group(1)
        
        pro_id = self.search_pro(nom, adresse, code_postal)
        
        if not pro_id:
            return None
        
        # Récupération du téléphone
        return self.get_pro_phone(pro_id)

    @staticmethod
    def _format_phone(phone: str) -> str:
        """
        Formate un numéro de téléphone français.
        
        Args:
            phone: Numéro de téléphone brut
            
        Returns:
            Numéro formaté
        """
        if not phone:
            return ""
        
        # Nettoyer le numéro (garder uniquement les chiffres)
        digits = re.sub(r'\D', '', phone)
        
        # Si c'est un numéro français (10 chiffres commençant par 0)
        if len(digits) == 10 and digits.startswith('0'):
            return f"{digits[:2]} {digits[2:4]} {digits[4:6]} {digits[6:8]} {digits[8:10]}"
        
        # Si c'est un numéro international (11 chiffres commençant par 33)
        if len(digits) >= 10 and digits.startswith('33'):
            # Retirer le préfixe 33 et le 0
            if len(digits) == 11:
                digits = "0" + digits[2:]
                return f"{digits[:2]} {digits[2:4]} {digits[4:6]} {digits[6:8]} {digits[8:10]}"
        
        # Retourner tel quel si format non reconnu
        return phone

