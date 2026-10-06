// ================================================================
// MES CV — Gestion professionnelle des CV sauvegardés
// ================================================================

let mesCvs = [];
let cvEnCoursId = null;
let filtres = { q: '', tri: 'recent' };


// ==================== INITIALISATION ====================
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('liste-cv')) {
    initPageMesCv();
  }

  // Bouton sur la page d'accueil
  document.getElementById('btn-sauvegarder-cv')
    ?.addEventListener('click', () => ouvrirModaleSauvegarde());
});


// ==================== PAGE MES CV ====================
function initPageMesCv() {
  chargerMesCvs();
  chargerStats();

  const recherche = document.getElementById('recherche-cv');
  let timer;
  recherche?.addEventListener('input', (e) => {
    filtres.q = e.target.value.trim();
    clearTimeout(timer);
    timer = setTimeout(chargerMesCvs, 300);
  });

  document.getElementById('tri-cv')?.addEventListener('change', (e) => {
    filtres.tri = e.target.value;
    chargerMesCvs();
  });
}


// ==================== CHARGER LA LISTE ====================
async function chargerMesCvs() {
  const zone = document.getElementById('liste-cv');
  if (!zone) return;

  zone.innerHTML = `
    <div class="chargement-cv">
      <div class="spinner"></div>
      <p>Chargement...</p>
    </div>
  `;

  try {
    const params = new URLSearchParams(filtres);
    const res = await fetch(`/api/mes-cv?${params}`);
    const json = await res.json();

    if (!json.success) {
      zone.innerHTML = `<p style="color:#e74c3c;">Erreur de chargement</p>`;
      return;
    }

    mesCvs = json.cvs;

    if (json.cvs.length === 0) {
      afficherEtatVide(zone, filtres.q);
      return;
    }

    zone.innerHTML = json.cvs.map(cv => carteCv(cv, json.premium)).join('');
    attacherEvenementsCv(json.premium);

  } catch (e) {
    console.error('Erreur', e);
    zone.innerHTML = `<p style="color:#e74c3c;">Erreur réseau</p>`;
  }
}


// ==================== CARTE CV ====================
function carteCv(cv, premium) {
  const dateAffichee = cv.updated_at;
  const couleur = cv.couleur || '#f39c12';

  return `
    <div class="cv-card" data-cv-id="${cv.id}">
      <div class="cv-card-preview" style="border-top: 4px solid ${couleur};">
        <div class="cv-preview-ico">📄</div>
        <div class="cv-preview-modele">${cv.modele.replace('modele', 'Modèle ')}</div>
        ${cv.has_photo ? '<div class="cv-photo-badge">📷</div>' : ''}
      </div>

      <div class="cv-card-contenu">
        <h3 class="cv-card-titre" title="${escapeHtml(cv.titre)}">${escapeHtml(cv.titre)}</h3>
        <div class="cv-card-meta">
          <span class="cv-meta-date">🕐 ${dateAffichee}</span>
        </div>
      </div>

      <div class="cv-card-actions">
        <button type="button" class="btn-action btn-charger" data-action="charger" data-cv-id="${cv.id}" title="Charger ce CV">
          📂 Ouvrir
        </button>
        ${premium ? `
          <button type="button" class="btn-action btn-dupliquer" data-action="dupliquer" data-cv-id="${cv.id}" title="Dupliquer">
            📋
          </button>
        ` : ''}
        <button type="button" class="btn-action btn-suppr" data-action="supprimer" data-cv-id="${cv.id}" title="Supprimer">
          🗑
        </button>
      </div>
    </div>
  `;
}


// ==================== ÉTAT VIDE ====================
function afficherEtatVide(zone, recherche) {
  if (recherche) {
    zone.innerHTML = `
      <div class="etat-vide">
        <div class="etat-vide-ico">🔍</div>
        <h3>Aucun résultat</h3>
        <p>Aucun CV ne correspond à "<b>${escapeHtml(recherche)}</b>"</p>
        <button type="button" class="btn-or" onclick="document.getElementById('recherche-cv').value=''; filtres.q=''; chargerMesCvs();">
          Effacer la recherche
        </button>
      </div>
    `;
  } else {
    zone.innerHTML = `
      <div class="etat-vide">
        <div class="etat-vide-ico">📂</div>
        <h3>Aucun CV sauvegardé</h3>
        <p>Créez votre premier CV et sauvegardez-le pour le retrouver à tout moment.</p>
        <a href="/#creer" class="btn-or" style="display:inline-block;padding:14px 28px;border-radius:12px;text-decoration:none;color:#fff;">
          ✨ Créer mon premier CV
        </a>
      </div>
    `;
  }
}


// ==================== ÉVÉNEMENTS ====================
function attacherEvenementsCv(premium) {
  document.querySelectorAll('.cv-card-actions .btn-action').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const action = btn.dataset.action;
      const cvId = parseInt(btn.dataset.cvId);
      if (action === 'charger') chargerCv(cvId);
      if (action === 'supprimer') supprimerCv(cvId);
      if (action === 'dupliquer') dupliquerCv(cvId);
    });
  });

  // Clic sur la carte → charger
  document.querySelectorAll('.cv-card').forEach(card => {
    card.addEventListener('click', () => {
      const cvId = parseInt(card.dataset.cvId);
      chargerCv(cvId);
    });
  });
}


// ==================== CHARGER UN CV ====================
async function chargerCv(cvId) {
  try {
    const res = await fetch(`/api/mes-cv/${cvId}`);
    const json = await res.json();

    if (!json.success) {
      afficherToast('❌ CV introuvable');
      return;
    }

    const cv = json.cv;
    const data = cv.donnees;

    // Sauvegarder dans localStorage pour transfert
    localStorage.setItem('cvpro_cv_a_charger', JSON.stringify({
      cv_id: cvId,
      donnees: data,
      photo: cv.photo,
      modele: cv.modele,
      couleur: cv.couleur,
    }));

    afficherToast(`📂 CV "${cv.titre}" chargé`);

    // Rediriger vers l'accueil
    window.location.href = '/#creer';

  } catch (e) {
    console.error(e);
    afficherToast('❌ Erreur de chargement');
  }
}


// ==================== SUPPRIMER UN CV ====================
async function supprimerCv(cvId) {
  const cv = mesCvs.find(c => c.id === cvId);
  const nom = cv ? cv.titre : 'ce CV';

  if (!confirm(`Supprimer "${nom}" ?\n\nCette action est irréversible.`)) return;

  try {
    const res = await fetch(`/api/mes-cv/${cvId}`, { method: 'DELETE' });
    const json = await res.json();

    if (json.success) {
      afficherToast('🗑 CV supprimé');
      // Animation de sortie
      const card = document.querySelector(`.cv-card[data-cv-id="${cvId}"]`);
      if (card) {
        card.style.transition = 'all .3s';
        card.style.opacity = '0';
        card.style.transform = 'scale(.9)';
        setTimeout(() => { chargerMesCvs(); chargerStats(); }, 300);
      } else {
        chargerMesCvs();
        chargerStats();
      }
    } else {
      afficherToast('❌ ' + (json.error || 'Erreur'));
    }
  } catch (e) {
    afficherToast('❌ Erreur');
  }
}


// ==================== DUPLIQUER UN CV ====================
async function dupliquerCv(cvId) {
  try {
    const res = await fetch(`/api/mes-cv/${cvId}/dupliquer`, { method: 'POST' });
    const json = await res.json();

    if (json.success) {
      afficherToast('📋 CV dupliqué !');
      chargerMesCvs();
    } else if (json.need_premium) {
      ouvrirModalePremium();
    } else {
      afficherToast('❌ ' + (json.error || 'Erreur'));
    }
  } catch (e) {
    afficherToast('❌ Erreur');
  }
}


// ==================== STATS ====================
async function chargerStats() {
  try {
    const res = await fetch('/api/mes-cv/stats');
    const json = await res.json();
    if (!json.success) return;

    document.getElementById('stat-total').textContent = json.total;
    document.getElementById('stat-dernier').textContent = json.dernier_ajout || '—';
  } catch (e) { /* silencieux */ }
}


// ==================== MODALE SAUVEGARDE ====================
function ouvrirModaleSauvegarde() {
  const modale = document.getElementById('modale-sauvegarde');
  if (!modale) return;

  const input = document.getElementById('input-titre-cv');
  if (input) {
    // Suggestion auto
    const nom = document.querySelector('[data-champ="nom"]')?.value.trim() || '';
    const prenom = document.querySelector('[data-champ="prenom"]')?.value.trim() || '';
    const titrePoste = document.querySelector('[data-champ="titre"]')?.value.trim() || '';

    if (prenom && nom) {
      input.value = `CV ${prenom} ${nom}${titrePoste ? ' — ' + titrePoste : ''}`;
    } else {
      input.value = '';
    }
    input.focus();
    input.select();
  }

  document.getElementById('modale-sauv-titre').textContent =
    cvEnCoursId ? 'Mettre à jour ce CV' : 'Sauvegarder ce CV';

  modale.classList.add('ouverte');
}


function fermerModaleSauvegarde() {
  document.getElementById('modale-sauvegarde')?.classList.remove('ouverte');
}


// ==================== CONFIRMER SAUVEGARDE ====================
async function confirmerSauvegarde() {
  const input = document.getElementById('input-titre-cv');
  const titre = (input?.value || '').trim();

  if (!titre) {
    afficherToast('⚠️ Entrez un titre');
    input?.focus();
    return;
  }

  // Récupérer les données du CV
  const data = collecterDonnees();
  if (!data.nom && !data.prenom) {
    afficherToast('⚠️ Remplissez au moins le nom ou prénom');
    return;
  }

  const payload = {
    cv_id: cvEnCoursId,
    titre,
    modele: modeleActif,
    donnees: data,
    photo: photoData,
    couleur: data.couleur_perso || '#f39c12',
  };

  const btn = document.getElementById('btn-confirmer-sauv');
  const texteOrig = btn.textContent;
  btn.disabled = true;
  btn.textContent = '⏳ Sauvegarde...';

  try {
    const res = await fetch('/api/mes-cv', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const json = await res.json();

    if (json.success) {
      cvEnCoursId = json.cv_id;
      fermerModaleSauvegarde();
      afficherToast(json.action === 'created' ? '✅ CV sauvegardé !' : '✅ CV mis à jour !');
      mettreAJourBadgeCount();
    } else if (json.limite_atteinte) {
      fermerModaleSauvegarde();
      document.getElementById('modale-limite')?.classList.add('ouverte');
    } else {
      afficherToast('❌ ' + (json.error || 'Erreur'));
    }
  } catch (e) {
    console.error(e);
    afficherToast('❌ Erreur de connexion');
  } finally {
    btn.disabled = false;
    btn.textContent = texteOrig;
  }
}


// ==================== BADGE COUNT ====================
async function mettreAJourBadgeCount() {
  const badge = document.getElementById('badge-cv-count');
  if (!badge) return;
  try {
    const res = await fetch('/api/mes-cv/stats');
    const json = await res.json();
    if (json.success) {
      badge.textContent = json.max
        ? `(${json.total}/${json.max})`
        : `(${json.total})`;
    }
  } catch (e) { /* silencieux */ }
}


// ==================== UTILS ====================
function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}


// ==================== INIT DES MODALES ====================
document.addEventListener('DOMContentLoaded', () => {
  // Modale sauvegarde
  document.getElementById('modale-sauv-x')
    ?.addEventListener('click', fermerModaleSauvegarde);
  document.getElementById('btn-annuler-sauv')
    ?.addEventListener('click', fermerModaleSauvegarde);
  document.getElementById('btn-confirmer-sauv')
    ?.addEventListener('click', confirmerSauvegarde);
  document.getElementById('modale-sauvegarde')?.addEventListener('click', (e) => {
    if (e.target.id === 'modale-sauvegarde') fermerModaleSauvegarde();
  });
  document.getElementById('input-titre-cv')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') confirmerSauvegarde();
  });

  // Modale limite
  document.getElementById('modale-limite-x')
    ?.addEventListener('click', () => {
      document.getElementById('modale-limite')?.classList.remove('ouverte');
    });
  document.getElementById('modale-limite')?.addEventListener('click', (e) => {
    if (e.target.id === 'modale-limite') {
      document.getElementById('modale-limite')?.classList.remove('ouverte');
    }
  });

  // Badge count sur la page d'accueil
  if (window.utilisateurConnecte) mettreAJourBadgeCount();
});