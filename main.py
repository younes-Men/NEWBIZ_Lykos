import os
import webbrowser
from typing import List, Dict
from urllib.parse import quote

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from scraper.sirene import SireneClient


console = Console()


def prompt_user_filters() -> Dict[str, str]:
    """
    Demande à l'utilisateur le secteur et le département.
    Secteur : soit mot-clé libre, soit code NAF (si l'utilisateur le connaît).
    Département : code à 2 chiffres (ex: 75, 13, 69) ou 2A/2B pour la Corse.
    """
    console.print("[bold cyan]=== Recherche d'entreprises (France) ===[/bold cyan]")
    secteur = console.input(
        "[bold]Secteur / activité[/bold] (mot-clé ou code NAF, ex: 'boulangerie' ou '47.11C') : "
    ).strip()

    departement = console.input(
        "[bold]Département[/bold] (code, ex: '75', '13', '69', '2A', '2B') : "
    ).strip()

    if not secteur or not departement:
        console.print("[bold red]Erreur : secteur et département sont obligatoires.[/bold red]")
        raise SystemExit(1)

    return {"secteur": secteur, "departement": departement}


def generate_search_url(nom: str, adresse: str) -> str:
    """
    Génère une URL de recherche Google pour trouver le téléphone de l'entreprise.
    Format: "nom entreprise adresse téléphone"
    """
    query = f"{nom} {adresse} téléphone"
    encoded_query = quote(query)
    return f"https://www.google.com/search?q={encoded_query}"


def generate_pappers_url(siren: str) -> str:
    """
    Génère une URL de recherche Pappers pour trouver le dirigeant.
    Format: recherche par SIREN
    """
    if not siren or len(siren) < 9:
        return ""
    # Pappers utilise le SIREN dans l'URL
    return f"https://www.pappers.fr/recherche?q={siren}"


def display_results(results: List[Dict[str, str]]) -> None:
    """
    Affiche les résultats dans un tableau lisible pour les téléconseillers.
    """
    if not results:
        console.print("[bold yellow]Aucune entreprise trouvée pour ces critères.[/bold yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("N°", style="dim", width=3)
    table.add_column("Nom", style="cyan", no_wrap=True)
    table.add_column("Adresse")
    table.add_column("Téléphone")
    table.add_column("Secteur")
    table.add_column("SIRET")
    table.add_column("SIREN")
    table.add_column("Dirigeant")
    table.add_column("Effectif")
    table.add_column("👤 Pappers", style="cyan", width=10)

    for idx, ent in enumerate(results, 1):
        nom = ent.get("nom", "")
        siren = ent.get("siren", "")
        
        # Générer le lien Pappers
        pappers_url = generate_pappers_url(siren)
        
        # Afficher le lien dans le tableau
        pappers_link = f"[link={pappers_url}]Ouvrir[/link]" if pappers_url else "-"
        
        table.add_row(
            str(idx),
            nom[:40],
            ent.get("adresse", "")[:50],
            ent.get("telephone", ""),
            ent.get("secteur", ""),
            ent.get("siret", ""),
            siren,
            ent.get("dirigeant", "")[:30],
            ent.get("effectif", ""),
            pappers_link,
        )

    console.print(table)
    console.print(f"[bold green]{len(results)} entreprise(s) affichée(s).[/bold green]")
    
    # Proposer d'ouvrir automatiquement les liens
    console.print("\n[bold cyan]Options :[/bold cyan]")
    console.print("  • Cliquez sur 'Ouvrir' dans la colonne '👤 Pappers' pour ouvrir le lien")
    console.print("  • Tapez le numéro de ligne (ex: '1') pour ouvrir Pappers automatiquement")
    console.print("  • Tapez 'all' pour ouvrir tous les liens Pappers dans le navigateur")
    console.print("  • Tapez 'exit' ou appuyez sur Entrée pour quitter\n")
    
    while True:
        choice = console.input("[bold]Votre choix[/bold] (numéro de ligne, 'all', ou 'exit') : ").strip().lower()
        
        if choice == "exit" or choice == "":
            break
        elif choice == "all":
            console.print("[bold cyan]Ouverture de tous les liens Pappers dans le navigateur...[/bold cyan]")
            for ent in results:
                siren = ent.get("siren", "")
                pappers_url = generate_pappers_url(siren)
                if pappers_url:
                    webbrowser.open(pappers_url)
            console.print(f"[bold green]✓ Liens Pappers ouverts dans votre navigateur.[/bold green]")
            break
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(results):
                ent = results[idx]
                nom = ent.get("nom", "")
                siren = ent.get("siren", "")
                pappers_url = generate_pappers_url(siren)
                if pappers_url:
                    webbrowser.open(pappers_url)
                    console.print(f"[bold green]✓ Pappers ouvert pour : {nom}[/bold green]")
                else:
                    console.print("[bold red]SIREN manquant, impossible d'ouvrir Pappers.[/bold red]")
            else:
                console.print(f"[bold red]Numéro invalide. Choisissez entre 1 et {len(results)}.[/bold red]")
        else:
            console.print("[bold red]Choix invalide. Utilisez un numéro, 'all', ou 'exit'.[/bold red]")


def main() -> None:
    # Charger les variables d'environnement (.env) pour l'API SIRENE
    load_dotenv()

    api_key = os.getenv("SIRENE_API_KEY")

    if not api_key:
        console.print(
            "[bold yellow]Attention : aucune clé API SIRENE trouvée (variable SIRENE_API_KEY).[/bold yellow]\n"
            "Le script va fonctionner en [bold]mode démo[/bold] avec des données factices.\n"
            "Pour activer les vraies données, copie la clé affichée sur le portail Insee\n"
            "dans un fichier .env sous la forme : SIRENE_API_KEY=ta_cle_ici"
        )

    filters = prompt_user_filters()

    client = SireneClient(api_key=api_key)

    console.print("\n[bold cyan]Recherche en cours...[/bold cyan]")
    results = client.search_by_secteur_and_departement(
        secteur=filters["secteur"],
        departement=filters["departement"],
        limit=300,
    )

    display_results(results)


if __name__ == "__main__":
    main()


