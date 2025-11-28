import logging
from typing import List, Dict, Optional

import requests


logger = logging.getLogger(__name__)


TRANCHE_EFFECTIFS_LABELS = {
    "NN": "Unité non-employeuse ou effectif inconnu",
    "00": "0 salarié (ayant employé des salariés au cours de l'année)",
    "01": "1 ou 2 salariés",
    "02": "3 à 5 salariés",
    "03": "6 à 9 salariés",
    "11": "10 à 19 salariés",
    "12": "20 à 49 salariés",
    "21": "50 à 99 salariés",
    "22": "100 à 199 salariés",
    "31": "200 à 249 salariés",
    "32": "250 à 499 salariés",
    "41": "500 à 999 salariés",
    "42": "1 000 à 1 999 salariés",
    "51": "2 000 à 4 999 salariés",
    "52": "5 000 à 9 999 salariés",
    "53": "10 000 salariés et plus",
}


class SireneClient:
    """
    Client minimal pour l'API Sirene de l'INSEE.
    - Si aucune clé n'est fournie, le client renvoie des données factices (mode démo).
    - Sinon, il interroge l'API officielle (dans la limite des droits / quotas).

    Sur le portail `portail-api.insee.fr`, la clé affichée après souscription
    est passée dans l'en-tête HTTP `X-INSEE-Api-Key-Integration`.
    """

    # URL d'accès indiquée sur la page de l'API (ex: https://api.insee.fr/api-sirene/3.11)
    BASE_URL = "https://api.insee.fr/api-sirene/3.11"
    SIRET_SEARCH_PATH = "/siret"

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.api_key = api_key

    def _is_demo(self) -> bool:
        # En l'absence de clé, on reste en mode démo.
        return not self.api_key

    def search_by_secteur_and_departement(
        self, secteur: str, departement: str, limit: int = 300
    ) -> List[Dict[str, str]]:
        """
        Recherche d'entreprises par secteur (mot-clé ou code NAF) et département.
        - En mode démo : renvoie quelques entreprises factices.
        - En mode API : interroge l'API Sirene (simplifiée).
        """
        if self._is_demo():
            return self._demo_results(secteur, departement)

        # Construction d'une requête simple :
        # On fait l'hypothèse que "secteur" est un code NAF si ça ressemble à 2 chiffres + '.' + 2 chiffres...
        # Sinon, on pourrait faire une logique plus avancée (mapping mots-clés -> codes NAF).
        is_code_naf = any(char.isdigit() for char in secteur)

        if is_code_naf:
            # Recherche par code NAF activité principale + département sur le code postal
            # (la syntaxe exacte de l'API peut nécessiter des ajustements selon la doc officielle)
            q = f"activitePrincipaleUniteLegale:{secteur} AND codePostalEtablissement:{departement}*"
        else:
            # Recherche texte approximative sur la dénomination + département
            q = f"denominationUniteLegale:{secteur}* AND codePostalEtablissement:{departement}*"

        params = {
            "q": q,
            "nombre": min(limit, 1000),
        }
        # Clé telle qu'indiquée dans l'exemple cURL du portail :
        # curl --header "X-INSEE-Api-Key-Integration: VOTRE_CLE" ...
        headers = {"X-INSEE-Api-Key-Integration": self.api_key}

        try:
            url = f"{self.BASE_URL}{self.SIRET_SEARCH_PATH}"
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            # L'API peut retourner les établissements directement ou dans une structure imbriquée
            if "etablissements" in data:
                # Format: {"etablissements": [{"etablissement": {...}}, ...]}
                etablissements_raw = data.get("etablissements", [])
                # Si les établissements sont dans une structure {"etablissement": {...}}
                etablissements = []
                for item in etablissements_raw:
                    if "etablissement" in item:
                        etablissements.append(item["etablissement"])
                    else:
                        etablissements.append(item)
            else:
                etablissements = []
        except Exception as exc:
            logger.error("Erreur lors de l'appel à l'API SIRENE: %s", exc)
            return self._demo_results(secteur, departement)

        results: List[Dict[str, str]] = []

        for e in etablissements[:limit]:
            # Accéder à l'unité légale (peut être directement ou dans une structure)
            if "uniteLegale" in e:
                if isinstance(e["uniteLegale"], dict):
                    unite = e["uniteLegale"]
                else:
                    unite = {}
            else:
                unite = {}
            
            # Accéder à l'adresse
            if "adresseEtablissement" in e:
                adresse = e["adresseEtablissement"] if isinstance(e["adresseEtablissement"], dict) else {}
            else:
                adresse = {}

            nom = (
                unite.get("denominationUniteLegale")
                or unite.get("nomUniteLegale")
                or ""
            )

            voie = adresse.get("libelleVoieEtablissement", "") or ""
            cp = adresse.get("codePostalEtablissement", "") or ""
            commune = adresse.get("libelleCommuneEtablissement", "") or ""
            adresse_full = f"{voie}, {cp} {commune}".strip(", ")

            siret = e.get("siret", "") or ""
            # On essaie de récupérer le SIREN, sinon on le déduit des 9 premiers chiffres du SIRET
            siren = unite.get("siren") or (siret[:9] if len(siret) >= 9 else "")

            effectif_code = e.get("trancheEffectifsEtablissement", "") or ""
            # Si aucune info ou code 'NN' -> on affiche "0 à 1" au lieu de "NN"
            if not effectif_code or effectif_code == "NN":
                effectif_label = "0 à 1"
            else:
                # Sinon on essaie de traduire le code en texte lisible
                effectif_label = TRANCHE_EFFECTIFS_LABELS.get(
                    effectif_code, effectif_code
                )
            
            # Récupérer l'état administratif de l'établissement et de l'unité légale
            # Dans l'API Sirene v3, l'état est souvent dans periodesEtablissement (dernière période)
            etat_etablissement = ""
            etat_unite = ""
            
            # Essayer d'abord directement dans l'établissement
            etat_etablissement = e.get("etatAdministratifEtablissement") or ""
            
            # Si pas trouvé, chercher dans periodesEtablissement (dernière période = la plus récente)
            if not etat_etablissement and "periodesEtablissement" in e:
                periodes = e.get("periodesEtablissement", [])
                if periodes and isinstance(periodes, list) and len(periodes) > 0:
                    # Prendre la dernière période (la plus récente)
                    derniere_periode = periodes[-1]
                    if isinstance(derniere_periode, dict):
                        etat_etablissement = derniere_periode.get("etatAdministratifEtablissement", "") or ""
            
            # Pour l'unité légale, chercher directement ou dans periodesUniteLegale
            etat_unite = unite.get("etatAdministratifUniteLegale") or ""
            
            # Si pas trouvé, chercher dans periodesUniteLegale
            if not etat_unite and "periodesUniteLegale" in unite:
                periodes_ul = unite.get("periodesUniteLegale", [])
                if periodes_ul and isinstance(periodes_ul, list) and len(periodes_ul) > 0:
                    derniere_periode_ul = periodes_ul[-1]
                    if isinstance(derniere_periode_ul, dict):
                        etat_unite = derniere_periode_ul.get("etatAdministratifUniteLegale", "") or ""
            
            # Déterminer l'état affiché
            # "A" = Actif, "F" = Fermé, "C" = Cessé, etc.
            etat_labels = {
                "A": "Actif",
                "F": "Fermé",
                "C": "Cessé",
            }
            etat_etablissement_label = etat_labels.get(etat_etablissement, etat_etablissement or "Inconnu")
            etat_unite_label = etat_labels.get(etat_unite, etat_unite or "Inconnu")
            
            # Afficher l'état : si les deux sont actifs, afficher "Actif", sinon le statut de l'établissement
            if etat_etablissement == "A" and etat_unite == "A":
                etat_final = "Actif"
            elif etat_etablissement != "A":
                etat_final = etat_etablissement_label
            elif etat_etablissement == "A" and etat_unite != "A":
                # Si l'établissement est actif mais l'unité légale est cessée/fermée, considérer comme Fermé
                etat_final = "Fermé"
            else:
                etat_final = f"{etat_etablissement_label} / {etat_unite_label}"

            results.append(
                {
                    "nom": nom,
                    "adresse": adresse_full,
                    "telephone": "",  # L'API Sirene ne fournit pas le téléphone
                    "secteur": unite.get("activitePrincipaleUniteLegale", "") or "",
                    "siret": siret,
                    "siren": siren,
                    "dirigeant": "",  # Nécessiterait une autre source (INPI, Pappers, etc.)
                    "effectif": effectif_label,
                    "etat": etat_final,
                }
            )

        return results

    @staticmethod
    def _demo_results(secteur: str, departement: str) -> List[Dict[str, str]]:
        """
        Données factices pour démonstration/maquettage quand l'API réelle n'est pas configurée.
        """
        return [
            {
                "nom": f"Entreprise {secteur.title()} A ({departement})",
                "adresse": f"10 Rue de la Demo, 7500{departement} Ville-Demo",
                "telephone": "01 23 45 67 89",
                "secteur": secteur,
                "siret": "12345678900011",
                "siren": "123456789",
                "dirigeant": "M. Jean Dupont",
                "effectif": "03",
                "etat": "Actif",
            },
            {
                "nom": f"Entreprise {secteur.title()} B ({departement})",
                "adresse": f"25 Avenue Exemple, 7500{departement} Ville-Exemple",
                "telephone": "01 98 76 54 32",
                "secteur": secteur,
                "siret": "98765432100022",
                "siren": "987654321",
                "dirigeant": "Mme Marie Martin",
                "effectif": "10",
                "etat": "Actif",
            },
        ]


