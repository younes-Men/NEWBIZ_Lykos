import logging
from typing import Optional, Tuple
import requests

logger = logging.getLogger(__name__)


def get_opco_and_idcc_from_ape(ape_code: str, siret: str = "") -> Tuple[Optional[str], Optional[str]]:
    """
    Récupère l'OPCO et l'IDCC pour une entreprise.

    Priorité :
    1. Appeler l'API France Compétences (site 'Quel est mon OPCO ?')
       https://quel-est-mon-opco.francecompetences.fr/
       via son endpoint public
       https://api.francecompetences.fr/siro/v1/nico/search/{siret}
    2. Si rien trouvé, utiliser un mapping approximatif APE -> IDCC -> OPCO.

    Args:
        ape_code: Code APE/NAF (ex: "47.11C", "56.10Z")
        siret: Numéro SIRET (14 chiffres)

    Returns:
        Tuple (OPCO, IDCC) ou (None, None) si non trouvé.
    """
    ape_code = (ape_code or "").strip()
    siret = (siret or "").strip()

    # 1) Essayer d'abord France Compétences si on a un SIRET
    if siret and siret.isdigit() and len(siret) >= 9:
        try:
            opco_api, idcc_api = _get_from_france_competences(siret)
            if opco_api or idcc_api:
                return opco_api, idcc_api
        except Exception as e:
            logger.debug(f"Erreur France Compétences pour SIRET {siret}: {e}")

    # 2) Fallback : mapping basique basé sur le code APE/NAF
    if ape_code:
        idcc = _get_idcc_from_ape(ape_code)
        if idcc:
            opco = _get_opco_from_idcc(idcc)
            return opco, idcc

    return None, None


def _get_from_france_competences(siret: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Appelle l'API France Compétences pour récupérer OPCO et IDCC
    à partir d'un SIRET.

    Endpoint observé dans le site :
    https://api.francecompetences.fr/siro/v1/nico/search/{siret}
    """
    url = f"https://api.francecompetences.fr/siro/v1/nico/search/{siret}"
    resp = requests.get(url, timeout=5)
    if resp.status_code != 200:
        return None, None

    try:
        data = resp.json()
    except ValueError:
        return None, None

    # La réponse peut être un objet ou une liste ; on parcours récursivement
    opco = _find_first_value_by_key(data, ["opco", "opco_nom", "opcoName", "opcoLibelle"])
    idcc = _find_first_value_by_key(data, ["idcc", "codeIdcc", "idccNumero"])

    # Si on a un IDCC mais pas d'OPCO, essayer de le retrouver via le mapping
    if idcc and not opco:
        opco = _get_opco_from_idcc(idcc)

    return opco, idcc


def _find_first_value_by_key(data, key_substrings) -> Optional[str]:
    """
    Parcourt récursivement un JSON (dict/list) et renvoie la première valeur
    dont la clé contient un des fragments donnés (insensible à la casse).
    """
    substrings = [s.lower() for s in key_substrings]

    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                k_low = str(k).lower()
                if any(sub in k_low for sub in substrings):
                    if isinstance(v, (str, int)):
                        return str(v).strip()
                res = walk(v)
                if res:
                    return res
        elif isinstance(obj, list):
            for item in obj:
                res = walk(item)
                if res:
                    return res
        return None

    return walk(data)


def _get_idcc_from_ape(ape_code: str) -> Optional[str]:
    """
    Mapping partiel code APE -> IDCC.
    Ce mapping devrait être étendu avec une vraie base de données complète.
    """
    # Normaliser le code APE (enlever les points et lettres)
    ape_normalized = ape_code.replace(".", "").upper()
    ape_prefix = ape_code.split(".")[0] if "." in ape_code else ape_code[:2]
    
    # Mapping partiel basé sur les grandes familles d'activités
    # Source: correspondances APE -> IDCC courantes
    mapping = {
        # Commerce de détail
        "4711": "2120",  # Commerce de détail alimentaire
        "4719": "2120",  # Autre commerce de détail
        "472": "2120",   # Commerce de détail alimentaire
        "473": "2120",   # Commerce de détail de carburants
        "474": "2120",   # Commerce de détail d'équipements
        "475": "2120",   # Commerce de détail de meubles
        "476": "2120",   # Commerce de détail de biens culturels
        "477": "2120",   # Commerce de détail non spécialisé
        
        # Hôtellerie-Restauration
        "551": "1979",   # Hôtels
        "552": "1979",   # Hébergement touristique
        "553": "1979",   # Terrain de camping
        "561": "1979",   # Restauration traditionnelle
        "562": "1979",   # Restauration rapide
        "563": "1979",   # Débits de boissons
        
        # BTP
        "41": "1596",    # Construction de bâtiments
        "42": "1596",    # Génie civil
        "43": "1596",    # Travaux spécialisés
        
        # Industrie
        "10": "1486",    # Industrie alimentaire
        "11": "1486",    # Fabrication de boissons
        "13": "1486",    # Fabrication de textiles
        "14": "1486",    # Industrie de l'habillement
        "15": "1486",    # Industrie du cuir
        "16": "1486",    # Travail du bois
        "17": "1486",    # Industrie du papier
        "18": "1486",    # Imprimerie
        "19": "1486",    # Cokéfaction
        "20": "1486",    # Industrie chimique
        "21": "1486",    # Industrie pharmaceutique
        "22": "1486",    # Industrie du caoutchouc
        "23": "1486",    # Industrie verrière
        "24": "1486",    # Métallurgie
        "25": "1486",    # Fabrication de produits métalliques
        "26": "1486",    # Fabrication d'équipements informatiques
        "27": "1486",    # Fabrication d'équipements électriques
        "28": "1486",    # Fabrication de machines
        "29": "1486",    # Fabrication de véhicules
        "30": "1486",    # Fabrication d'autres équipements de transport
        "31": "1486",    # Fabrication de meubles
        "32": "1486",    # Autres industries manufacturières
        "33": "1486",    # Réparation d'équipements
        
        # Services
        "68": "2120",    # Activités immobilières
        "69": "2120",    # Activités juridiques
        "70": "2120",    # Activités de sièges sociaux
        "71": "2120",    # Activités d'architecture
        "72": "2120",    # Recherche-développement
        "73": "2120",    # Publicité
        "74": "2120",    # Autres activités spécialisées
        "77": "2120",    # Location
        "78": "2120",    # Activités liées à l'emploi
        "79": "2120",    # Agences de voyage
        "80": "2120",    # Enquêtes et sécurité
        "81": "2120",    # Services relatifs aux bâtiments
        "82": "2120",    # Activités administratives
        "85": "2120",    # Enseignement
        "86": "2120",    # Activités pour la santé
        "87": "2120",    # Hébergement médico-social
        "88": "2120",    # Action sociale
        "90": "2120",    # Arts
        "91": "2120",    # Bibliothèques
        "92": "2120",    # Jeux
        "93": "2120",    # Activités sportives
        "94": "2120",    # Activités des organisations
        "95": "2120",    # Réparation d'ordinateurs
        "96": "2120",    # Autres services personnels
    }
    
    # Chercher d'abord le code complet
    if ape_normalized in mapping:
        return mapping[ape_normalized]
    
    # Chercher le préfixe à 2 chiffres
    if ape_prefix in mapping:
        return mapping[ape_prefix]
    
    # Chercher le préfixe à 3 chiffres
    if len(ape_normalized) >= 3:
        ape_3 = ape_normalized[:3]
        if ape_3 in mapping:
            return mapping[ape_3]
    
    return None


def _get_opco_from_idcc(idcc: str) -> Optional[str]:
    """
    Mapping IDCC -> OPCO.
    Ce mapping devrait être étendu avec une vraie base de données complète.
    """
    if not idcc:
        return None
    
    idcc = str(idcc).strip()
    
    # Mapping partiel IDCC -> OPCO
    # Source: correspondances IDCC -> OPCO courantes
    mapping = {
        # Commerce
        "2120": "OPCO 2i",
        
        # Hôtellerie-Restauration
        "1979": "OPCO 2i",
        
        # BTP
        "1596": "OPCO Constructys",
        
        # Industrie
        "1486": "OPCO 2i",
        
        # Services
        "2120": "OPCO 2i",
        
        # Autres conventions courantes
        "1518": "OPCO 2i",      # Commerce de gros
        "1501": "OPCO 2i",      # Commerce de détail
        "1502": "OPCO 2i",      # Commerce de détail
        "1503": "OPCO 2i",      # Commerce de détail
        "1504": "OPCO 2i",      # Commerce de détail
        "1505": "OPCO 2i",      # Commerce de détail
        "1506": "OPCO 2i",      # Commerce de détail
        "1507": "OPCO 2i",      # Commerce de détail
        "1508": "OPCO 2i",      # Commerce de détail
        "1509": "OPCO 2i",      # Commerce de détail
        "1510": "OPCO 2i",      # Commerce de détail
        "1511": "OPCO 2i",      # Commerce de détail
        "1512": "OPCO 2i",      # Commerce de détail
        "1513": "OPCO 2i",      # Commerce de détail
        "1514": "OPCO 2i",      # Commerce de détail
        "1515": "OPCO 2i",      # Commerce de détail
        "1516": "OPCO 2i",      # Commerce de détail
        "1517": "OPCO 2i",      # Commerce de détail
    }
    
    return mapping.get(idcc)


