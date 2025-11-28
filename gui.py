import os
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Dict
from datetime import datetime

from dotenv import load_dotenv
import pandas as pd

from scraper.sirene import SireneClient


def generate_pappers_url(siren: str) -> str:
    """
    Génère une URL de recherche Pappers pour trouver le dirigeant.
    Format: recherche par SIREN
    """
    if not siren or len(siren) < 9:
        return ""
    return f"https://www.pappers.fr/recherche?q={siren}"


class ScrapingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Recherche d'entreprises - Centre d'appels")
        self.root.geometry("1400x700")
        
        # Charger la clé API
        load_dotenv()
        self.api_key = os.getenv("SIRENE_API_KEY")
        self.client = SireneClient(api_key=self.api_key)
        self.current_results: List[Dict[str, str]] = []
        
        # Créer l'interface
        self.create_widgets()
        
        # Avertissement si pas de clé API
        if not self.api_key:
            messagebox.showwarning(
                "Clé API manquante",
                "Aucune clé API SIRENE trouvée.\n"
                "Le programme fonctionnera en mode démo avec des données factices.\n"
                "Pour activer les vraies données, créez un fichier .env avec :\n"
                "SIRENE_API_KEY=ta_cle_ici"
            )
    
    def create_widgets(self):
        # Frame pour les champs de saisie
        input_frame = ttk.Frame(self.root, padding="10")
        input_frame.pack(fill=tk.X)
        
        # Champ Secteur / Activité
        ttk.Label(input_frame, text="Secteur / Activité :", font=("Arial", 10, "bold")).grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.secteur_entry = ttk.Entry(input_frame, width=40, font=("Arial", 10))
        self.secteur_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Champ Département
        ttk.Label(input_frame, text="Département :", font=("Arial", 10, "bold")).grid(
            row=0, column=2, sticky=tk.W, padx=5, pady=5
        )
        self.departement_entry = ttk.Entry(input_frame, width=15, font=("Arial", 10))
        self.departement_entry.grid(row=0, column=3, padx=5, pady=5)
        
        # Bouton Recherche
        self.search_button = ttk.Button(
            input_frame,
            text="🔍 Rechercher",
            command=self.search_companies,
            style="Accent.TButton"
        )
        self.search_button.grid(row=0, column=4, padx=10, pady=5)
        
        # Bouton Télécharger Excel
        self.export_button = ttk.Button(
            input_frame,
            text="📥 Télécharger Excel",
            command=self.export_to_excel,
            state=tk.DISABLED
        )
        self.export_button.grid(row=0, column=5, padx=5, pady=5)
        
        # Frame pour le tableau
        table_frame = ttk.Frame(self.root, padding="10")
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        h_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Tableau (Treeview)
        columns = ("N°", "Nom", "Adresse", "Téléphone", "Secteur", "SIRET", "SIREN", "Dirigeant", "Effectif", "Pappers")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            height=20
        )
        
        v_scrollbar.config(command=self.tree.yview)
        h_scrollbar.config(command=self.tree.xview)
        
        # Configuration des colonnes
        self.tree.heading("N°", text="N°")
        self.tree.heading("Nom", text="Nom")
        self.tree.heading("Adresse", text="Adresse")
        self.tree.heading("Téléphone", text="Téléphone")
        self.tree.heading("Secteur", text="Secteur")
        self.tree.heading("SIRET", text="SIRET")
        self.tree.heading("SIREN", text="SIREN")
        self.tree.heading("Dirigeant", text="Dirigeant")
        self.tree.heading("Effectif", text="Effectif")
        self.tree.heading("Pappers", text="👤 Pappers")
        
        # Largeurs des colonnes
        self.tree.column("N°", width=40, anchor=tk.CENTER)
        self.tree.column("Nom", width=200)
        self.tree.column("Adresse", width=250)
        self.tree.column("Téléphone", width=120)
        self.tree.column("Secteur", width=100)
        self.tree.column("SIRET", width=120)
        self.tree.column("SIREN", width=100)
        self.tree.column("Dirigeant", width=150)
        self.tree.column("Effectif", width=150)
        self.tree.column("Pappers", width=100, anchor=tk.CENTER)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind double-click sur la colonne Pappers
        self.tree.bind("<Double-1>", self.on_double_click)
        
        # Label pour le statut
        self.status_label = ttk.Label(
            self.root,
            text="Prêt à rechercher",
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding="5"
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
    
    def search_companies(self):
        secteur = self.secteur_entry.get().strip()
        departement = self.departement_entry.get().strip()
        
        if not secteur or not departement:
            messagebox.showerror("Erreur", "Veuillez remplir les champs Secteur et Département.")
            return
        
        # Désactiver le bouton pendant la recherche
        self.search_button.config(state=tk.DISABLED)
        self.status_label.config(text="Recherche en cours...")
        self.root.update()
        
        try:
            # Vider le tableau
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Lancer la recherche
            results = self.client.search_by_secteur_and_departement(
                secteur=secteur,
                departement=departement,
                limit=300,
            )
            
            self.current_results = results
            
            # Afficher les résultats
            for idx, ent in enumerate(results, 1):
                siren = ent.get("siren", "")
                pappers_url = generate_pappers_url(siren)
                pappers_text = "Ouvrir" if pappers_url else "-"
                
                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        idx,
                        ent.get("nom", "")[:80],
                        ent.get("adresse", "")[:80],
                        ent.get("telephone", ""),
                        ent.get("secteur", ""),
                        ent.get("siret", ""),
                        siren,
                        ent.get("dirigeant", "")[:50],
                        ent.get("effectif", ""),
                        pappers_text,
                    ),
                    tags=(pappers_url,) if pappers_url else ()
                )
            
            # Activer le bouton d'export si on a des résultats
            if results:
                self.export_button.config(state=tk.NORMAL)
                self.status_label.config(
                    text=f"✓ {len(results)} entreprise(s) trouvée(s). Double-cliquez sur 'Ouvrir' dans la colonne Pappers pour ouvrir le lien."
                )
            else:
                self.export_button.config(state=tk.DISABLED)
                self.status_label.config(text="Aucune entreprise trouvée pour ces critères.")
        
        except Exception as e:
            messagebox.showerror("Erreur", f"Une erreur est survenue : {str(e)}")
            self.status_label.config(text="Erreur lors de la recherche.")
        
        finally:
            self.search_button.config(state=tk.NORMAL)
    
    def on_double_click(self, event):
        """Ouvre Pappers quand on double-clique sur une ligne avec un lien"""
        item = self.tree.selection()[0] if self.tree.selection() else None
        if item:
            values = self.tree.item(item, "values")
            if len(values) >= 10 and values[9] == "Ouvrir":
                # Récupérer le SIREN de la ligne
                siren = values[6] if len(values) > 6 else ""
                pappers_url = generate_pappers_url(siren)
                if pappers_url:
                    webbrowser.open(pappers_url)
    
    def export_to_excel(self):
        if not self.current_results:
            messagebox.showwarning("Avertissement", "Aucune donnée à exporter.")
            return
        
        # Demander où sauvegarder le fichier
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile=f"entreprises_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        
        if not filename:
            return
        
        try:
            # Filtrer uniquement les entreprises avec l'état "Actif"
            active_results = [ent for ent in self.current_results if str(ent.get("etat", "")).strip() == "Actif"]
            
            if not active_results:
                messagebox.showwarning("Avertissement", "Aucune entreprise active à exporter.")
                return
            
            # Préparer les données pour Excel
            data = []
            for ent in active_results:
                siren = ent.get("siren", "")
                pappers_url = generate_pappers_url(siren)
                
                data.append({
                    "Nom": ent.get("nom", ""),
                    "Adresse": ent.get("adresse", ""),
                    "Téléphone": ent.get("telephone", ""),
                    "Secteur": ent.get("secteur", ""),
                    "SIRET": ent.get("siret", ""),
                    "SIREN": siren,
                    "Dirigeant": ent.get("dirigeant", ""),
                    "Effectif": ent.get("effectif", ""),
                    "État": ent.get("etat", ""),
                    "Lien Pappers": pappers_url if pappers_url else "",
                })
            
            # Créer un DataFrame et exporter
            df = pd.DataFrame(data)
            df.to_excel(filename, index=False, engine='openpyxl')
            
            messagebox.showinfo("Succès", f"Fichier Excel sauvegardé :\n{filename}")
            self.status_label.config(text=f"✓ Fichier exporté : {filename}")
        
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'export : {str(e)}")


def main():
    root = tk.Tk()
    app = ScrapingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

