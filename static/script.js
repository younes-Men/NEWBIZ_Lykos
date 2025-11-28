let currentResults = [];

// Options de statut avec leurs couleurs
const statutOptions = {
    'A traiter': { color: '#6c757d', bg: '#e9ecef', border: '#ced4da' },
    'Repondeur': { color: '#28a745', bg: '#d4edda', border: '#c3e6cb' },
    'Occupé': { color: '#ffc107', bg: '#fff3cd', border: '#ffeaa7' },
    'Rdv': { color: '#17a2b8', bg: '#d1ecf1', border: '#bee5eb' },
    'Rappel': { color: '#fd7e14', bg: '#ffe5d0', border: '#ffcc99' },
    'Nrp': { color: '#dc3545', bg: '#f8d7da', border: '#f5c6cb' },
    'Hors Cible Opco': { color: '#6f42c1', bg: '#e2d9f3', border: '#d1c4e9' },
    'Hors cible salariés': { color: '#e83e8c', bg: '#f8d7da', border: '#f5c6cb' },
    'Hors cible Siège': { color: '#20c997', bg: '#d1f2eb', border: '#a3e4d7' },
    'Deja pec': { color: '#007bff', bg: '#cce5ff', border: '#99ccff' },
    'Absent': { color: '#6c757d', bg: '#f8f9fa', border: '#dee2e6' },
    'Pi': { color: '#343a40', bg: '#e2e3e5', border: '#d6d8db' }
};

// Charger les statuts sauvegardés depuis localStorage
function loadStatuts() {
    const saved = localStorage.getItem('entreprise_statuts');
    return saved ? JSON.parse(saved) : {};
}

// Sauvegarder les statuts dans localStorage
function saveStatuts(statuts) {
    localStorage.setItem('entreprise_statuts', JSON.stringify(statuts));
}

// Obtenir le statut et la date d'une entreprise (par SIRET)
function getStatut(siret) {
    const statuts = loadStatuts();
    if (statuts[siret]) {
        return {
            statut: statuts[siret].statut || statuts[siret] || 'A traiter', // Compatibilité ancien format
            date: statuts[siret].date || null
        };
    }
    return { statut: 'A traiter', date: null };
}

// Définir le statut d'une entreprise avec la date
function setStatut(siret, statut) {
    const statuts = loadStatuts();
    const now = new Date();
    const dateStr = now.toLocaleString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
    statuts[siret] = {
        statut: statut,
        date: dateStr
    };
    saveStatuts(statuts);
    return dateStr;
}

// Charger les données FunBooster et Observation depuis localStorage
function loadEntrepriseData() {
    const saved = localStorage.getItem('entreprise_data');
    return saved ? JSON.parse(saved) : {};
}

// Sauvegarder les données FunBooster et Observation
function saveEntrepriseData(data) {
    localStorage.setItem('entreprise_data', JSON.stringify(data));
}

// Obtenir FunBooster et Observation d'une entreprise
function getEntrepriseData(siret) {
    const data = loadEntrepriseData();
    return data[siret] || { funbooster: '', observation: '' };
}

// Sauvegarder FunBooster ou Observation
function saveField(siret, field, value) {
    const data = loadEntrepriseData();
    if (!data[siret]) {
        data[siret] = { funbooster: '', observation: '' };
    }
    data[siret][field] = value;
    saveEntrepriseData(data);
}

document.getElementById('searchBtn').addEventListener('click', searchCompanies);
document.getElementById('exportBtn').addEventListener('click', exportToExcel);

// Permettre la recherche avec Enter
document.getElementById('secteur').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') searchCompanies();
});
document.getElementById('departement').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') searchCompanies();
});

async function searchCompanies() {
    const secteur = document.getElementById('secteur').value.trim();
    const departement = document.getElementById('departement').value.trim();
    
    if (!secteur || !departement) {
        showStatus('Veuillez remplir les champs Secteur et Département.', 'error');
        return;
    }
    
    // Afficher le loading
    document.getElementById('loading').style.display = 'block';
    document.getElementById('resultsTable').style.display = 'none';
    document.getElementById('exportBtn').disabled = true;
    hideStatus();
    
    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ secteur, departement })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Erreur lors de la recherche');
        }
        
        currentResults = data.results || [];
        displayResults(currentResults);
        
        if (currentResults.length > 0) {
            document.getElementById('exportBtn').disabled = false;
            showStatus(`✓ ${currentResults.length} entreprise(s) trouvée(s).`, 'success');
        } else {
            showStatus('Aucune entreprise trouvée pour ces critères.', 'error');
        }
        
    } catch (error) {
        showStatus(`Erreur : ${error.message}`, 'error');
    } finally {
        document.getElementById('loading').style.display = 'none';
    }
}

function displayResults(results) {
    const tbody = document.getElementById('resultsBody');
    tbody.innerHTML = '';
    
    if (results.length === 0) {
        document.getElementById('resultsTable').style.display = 'none';
        return;
    }
    
    document.getElementById('resultsTable').style.display = 'block';
    
    results.forEach((ent, index) => {
        const row = document.createElement('tr');
        
        // Lien PagesJaunes pour le téléphone
        const pjLink = ent.pagesjaunes_url 
            ? `<a href="${ent.pagesjaunes_url}" target="_blank" class="pappers-link" style="background: #ffcc00; color: #000;">PagesJaunes</a>`
            : '-';
        
        // Lien OPCO (France Compétences)
        const opcoLink = ent.opco_url
            ? `<a href="${ent.opco_url}" target="_blank" class="pappers-link" style="background: linear-gradient(135deg, #2196f3 0%, #00bcd4 100%); color: #fff;">OPCO</a>`
            : '-';
        
        // Lien Pappers pour le dirigeant
        const dirigeantLink = ent.pappers_url 
            ? `<a href="${ent.pappers_url}" target="_blank" class="pappers-link" style="background: linear-gradient(135deg, #ff00ff 0%, #8b00ff 100%); color: #fff;">Pappers</a>`
            : '-';
        
        // Déterminer le style de l'état
        const etat = ent.etat || 'Inconnu';
        const etatClass = etat === 'Actif' ? 'etat-actif' : 'etat-inactif';
        const etatDisplay = `<span class="${etatClass}">${escapeHtml(etat)}</span>`;
        
        // Récupérer le statut sauvegardé ou utiliser "A traiter" par défaut
        const siret = ent.siret || '';
        const statutData = getStatut(siret);
        const currentStatut = statutData.statut;
        const dateModification = statutData.date || '-';
        const statutStyle = statutOptions[currentStatut] || statutOptions['A traiter'];
        
        // Récupérer FunBooster et Observation sauvegardés
        const entrepriseData = getEntrepriseData(siret);
        const funboosterValue = entrepriseData.funbooster || '';
        const observationValue = entrepriseData.observation || '';
        
        // Créer le select de statut
        let statutSelect = '<select class="statut-select" data-siret="' + escapeHtml(siret) + '">';
        Object.keys(statutOptions).forEach(opt => {
            const selected = opt === currentStatut ? 'selected' : '';
            statutSelect += `<option value="${escapeHtml(opt)}" ${selected}>${escapeHtml(opt)}</option>`;
        });
        statutSelect += '</select>';
        
        // Créer les inputs FunBooster et Observation avec icônes de sauvegarde
        const funboosterInput = `
            <div class="input-with-icon">
                <input type="text" class="funbooster-input" data-siret="${escapeHtml(siret)}" 
                       placeholder="Nom téléconseiller" value="${escapeHtml(funboosterValue)}">
                <span class="save-icon" data-siret="${escapeHtml(siret)}" data-field="funbooster" title="Enregistrer">💾</span>
            </div>
        `;
        
        const observationInput = `
            <div class="input-with-icon">
                <input type="text" class="observation-input" data-siret="${escapeHtml(siret)}" 
                       placeholder="Commentaire" value="${escapeHtml(observationValue)}">
                <span class="save-icon" data-siret="${escapeHtml(siret)}" data-field="observation" title="Enregistrer">💾</span>
            </div>
        `;
        
        row.innerHTML = `
            <td>${index + 1}</td>
            <td>${escapeHtml(ent.nom || '')}</td>
            <td>${escapeHtml(ent.adresse || '')}</td>
            <td>${escapeHtml(ent.secteur || '')}</td>
            <td>${escapeHtml(ent.siret || '')}</td>
            <td>${escapeHtml(ent.siren || '')}</td>
            <td>${escapeHtml(ent.effectif || '')}</td>
            <td>${etatDisplay}</td>
            <td>${opcoLink}</td>
            <td>${pjLink}</td>
            <td>${dirigeantLink}</td>
            <td>${statutSelect}</td>
            <td class="date-modification">${escapeHtml(dateModification)}</td>
            <td>${funboosterInput}</td>
            <td>${observationInput}</td>
        `;
        
        tbody.appendChild(row);
        
        // Ajouter l'événement onChange au select
        const select = row.querySelector('.statut-select');
        if (select) {
            select.addEventListener('change', function() {
                const siretValue = this.getAttribute('data-siret');
                const newStatut = this.value;
                const dateStr = setStatut(siretValue, newStatut);
                updateStatutStyle(this, newStatut);
                // Mettre à jour la date de modification dans la cellule
                const dateCell = row.querySelector('.date-modification');
                if (dateCell) {
                    dateCell.textContent = dateStr;
                }
            });
            updateStatutStyle(select, currentStatut);
        }
        
        // Ajouter les événements de sauvegarde pour FunBooster et Observation
        const saveIcons = row.querySelectorAll('.save-icon');
        saveIcons.forEach(icon => {
            icon.addEventListener('click', function() {
                const siretValue = this.getAttribute('data-siret');
                const field = this.getAttribute('data-field');
                const input = row.querySelector(`.${field}-input`);
                if (input) {
                    const value = input.value.trim();
                    saveField(siretValue, field, value);
                    // Feedback visuel
                    this.style.transform = 'scale(1.2)';
                    this.style.color = '#00bcd4';
                    setTimeout(() => {
                        this.style.transform = 'scale(1)';
                        this.style.color = '';
                    }, 300);
                }
            });
        });
    });
}

async function exportToExcel() {
    if (currentResults.length === 0) {
        showStatus('Aucune donnée à exporter.', 'error');
        return;
    }
    
    // Ajouter les statuts sauvegardés et les données FunBooster/Observation aux résultats avant l'export
    const statuts = loadStatuts();
    const entrepriseData = loadEntrepriseData();
    const resultsWithStatuts = currentResults.map(ent => {
        const siret = ent.siret || '';
        const statutData = statuts[siret];
        const data = entrepriseData[siret] || { funbooster: '', observation: '' };
        
        let statut = 'A traiter';
        let date_modification = '';
        
        if (statutData && typeof statutData === 'object') {
            statut = statutData.statut || 'A traiter';
            date_modification = statutData.date || '';
        } else if (statutData) {
            // Compatibilité ancien format
            statut = statutData || 'A traiter';
        }
        
        return {
            ...ent,
            statut: statut,
            date_modification: date_modification,
            funbooster: data.funbooster || '',
            observation: data.observation || ''
        };
    });
    
    try {
        const response = await fetch('/api/export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ results: resultsWithStatuts })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Erreur lors de l\'export');
        }
        
        // Télécharger le fichier
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `entreprises_${new Date().toISOString().slice(0, 10)}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showStatus('✓ Fichier Excel téléchargé avec succès !', 'success');
        
    } catch (error) {
        showStatus(`Erreur lors de l'export : ${error.message}`, 'error');
    }
}

function showStatus(message, type) {
    const statusEl = document.getElementById('status');
    statusEl.textContent = message;
    statusEl.className = `status-message ${type}`;
}

function hideStatus() {
    const statusEl = document.getElementById('status');
    statusEl.className = 'status-message';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Mettre à jour le style du select selon le statut sélectionné
function updateStatutStyle(select, statut) {
    const style = statutOptions[statut] || statutOptions['A traiter'];
    select.style.color = style.color;
    select.style.backgroundColor = style.bg;
    select.style.borderColor = style.border;
    select.style.fontWeight = '600';
}

