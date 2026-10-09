// ================================================================
// CVPRO — Fichier JavaScript principal
// CV, Lettres, PDF, Premium, Stripe, Compteurs, Autosave
// ================================================================

// ==================== VARIABLES GLOBALES ====================
let modeleActif = 'modele1';
let photoData = null;
let modeleLettreActif = 'modele1';
let utilisateurPremium = false;
let utilisateurConnecte = false;
let timerSauvegardeAuto = null;
let dernierSauvegardeReussie = null;
let offreDetailEnCours = null;
const CLE_BROUILLON = 'cvpro_brouillon_v1';


// ==================== INITIALISATION ====================
document.addEventListener('DOMContentLoaded', () => {
  const annee = document.getElementById('annee');
  if (annee) annee.textContent = new Date().getFullYear();

  // ⭐ Vérifier statut AVANT tout
  verifierStatutPremium().then(() => {
    chargerModeles();
    initEvenements();
    ajouterExperience();
    ajouterFormation();
    ajouterLangue();
    majApercu();
  });

  chargerModelesLettres();
  initEvenementsLettre();
  majApercuLettre();

  initCouleur();
  initPolice();

  chargerBrouillon();
  initSauvegardeAuto();

  initPremium();
});


// ==================== STATUT PREMIUM ====================
async function verifierStatutPremium() {
  try {
    const res = await fetch('/api/premium/statut');
    const json = await res.json();
    utilisateurPremium = json.premium || false;
    utilisateurConnecte = json.connecte || false;
    document.body.dataset.premium = utilisateurPremium ? 'true' : 'false';
    document.body.dataset.connecte = utilisateurConnecte ? 'true' : 'false';
    console.log('👑 Premium :', utilisateurPremium, '| Connecté :', utilisateurConnecte);
  } catch (e) {
    console.error('Erreur statut premium', e);
    utilisateurPremium = false;
    utilisateurConnecte = false;
  }
}


// ==================== CHARGEMENT MODÈLES CV ====================
async function chargerModeles() {
  try {
    const res = await fetch('/api/modeles');
    const modeles = await res.json();
    const grille = document.getElementById('grille-modeles');
    if (!grille) return;
    grille.innerHTML = '';

    modeles.forEach(m => {
      const carte = document.createElement('div');
      const estVerrouille = m.premium && !utilisateurPremium;

      carte.className = 'carte-modele';
      if (m.id === modeleActif) carte.classList.add('actif');
      if (m.premium) carte.classList.add('premium');
      if (estVerrouille) carte.classList.add('verrouille');
      carte.dataset.modele = m.id;

      const badgePro = m.premium
        ? `<div class="badge-premium-carte">${estVerrouille ? '🔒' : '⭐'} PRO</div>`
        : '';

      carte.innerHTML = `
        ${badgePro}
        <div class="miniature-cadre">
          <iframe class="miniature-iframe"
                  src="/miniature/cv/${m.id}"
                  loading="lazy"
                  title="Aperçu ${m.nom}"
                  scrolling="no"
                  tabindex="-1"></iframe>
        </div>
        <div class="carte-modele-infos">
          <h4>${m.nom} ${m.premium ? '⭐' : ''}</h4>
          <p>${m.description}</p>
        </div>
      `;

      carte.addEventListener('click', () => {
        if (estVerrouille) {
          ouvrirModalePremium(`Modèle "${m.nom}"`);
          return;
        }
        document.querySelectorAll('#grille-modeles .carte-modele')
          .forEach(c => c.classList.remove('actif'));
        carte.classList.add('actif');
        modeleActif = m.id;
        const badge = document.getElementById('badge-modele');
        if (badge) badge.textContent =
          `Modèle ${m.id.replace('modele', '')} — ${m.nom}`;
        majApercu();
        declencherSauvegarde();
      });

      grille.appendChild(carte);
    });
  } catch (e) {
    console.error('Erreur chargement modèles CV', e);
  }
}


// ==================== CHARGEMENT MODÈLES LETTRES ====================
async function chargerModelesLettres() {
  const grille = document.getElementById('grille-lettres');
  if (!grille) return;

  try {
    const res = await fetch('/api/lettres/modeles');
    if (!res.ok) {
      grille.innerHTML = '<p style="color:#e74c3c;">Erreur de chargement</p>';
      return;
    }
    const modeles = await res.json();
    grille.innerHTML = '';

    modeles.forEach(m => {
      const carte = document.createElement('div');
      carte.className = 'carte-modele' +
        (m.id === modeleLettreActif ? ' actif' : '');
      carte.dataset.modele = m.id;
      carte.innerHTML = `
        <div class="miniature-cadre">
          <iframe class="miniature-iframe"
                  src="/miniature/lettre/${m.id}"
                  loading="lazy"
                  title="Aperçu ${m.nom}"
                  scrolling="no"
                  tabindex="-1"></iframe>
        </div>
        <div class="carte-modele-infos">
          <h4>${m.nom}</h4>
          <p>${m.description}</p>
        </div>
      `;
      carte.addEventListener('click', () => {
        document.querySelectorAll('#grille-lettres .carte-modele')
          .forEach(c => c.classList.remove('actif'));
        carte.classList.add('actif');
        modeleLettreActif = m.id;
        const badge = document.getElementById('badge-lettre');
        if (badge) badge.textContent =
          `Modèle ${m.id.replace('modele', '')} — ${m.nom}`;
        majApercuLettre();
      });
      grille.appendChild(carte);
    });
  } catch (e) {
    console.error('Erreur modèles lettres', e);
  }
}


// ==================== ÉVÉNEMENTS CV ====================
function initEvenements() {
  document.getElementById('burger')?.addEventListener('click', () => {
    document.getElementById('menu')?.classList.toggle('ouvert');
  });

  document.querySelectorAll('.soon').forEach(el => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      const sujet = el.dataset.soon || 'Cette section';
      ouvrirModale(sujet);
    });
  });

  document.getElementById('modale-x')?.addEventListener('click', fermerModale);
  document.getElementById('modale-ok')?.addEventListener('click', fermerModale);
  document.getElementById('modale')?.addEventListener('click', (e) => {
    if (e.target.id === 'modale') fermerModale();
  });

  document.querySelectorAll('[data-champ]').forEach(el => {
    el.addEventListener('input', () => { majApercu(); declencherSauvegarde(); });
    el.addEventListener('change', () => { majApercu(); declencherSauvegarde(); });
  });
  ['competences', 'certifications', 'interets'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('input', () => { majApercu(); declencherSauvegarde(); });
    }
  });

  document.getElementById('photo-input')?.addEventListener('change', gererPhoto);
  document.getElementById('photo-suppr')?.addEventListener('click', supprimerPhoto);

  document.querySelectorAll('[data-ajout]').forEach(btn => {
    btn.addEventListener('click', () => {
      const type = btn.dataset.ajout;
      if (type === 'experience') ajouterExperience();
      if (type === 'formation') ajouterFormation();
      if (type === 'langue') ajouterLangue();
      majApercu();
      declencherSauvegarde();
    });
  });

  document.addEventListener('click', (e) => {
    if (!e.target.classList.contains('date-toggle')) return;
    const btn = e.target;
    const inp = btn.previousElementSibling;
    if (!inp) return;

    if (inp.type === 'date') {
      inp.type = 'text';
      inp.placeholder = 'Ex : 01/2020';
      btn.textContent = '📝';
      btn.title = 'Revenir au calendrier';
      inp.value = '';
    } else {
      inp.type = 'date';
      inp.placeholder = '';
      btn.textContent = '📅';
      btn.title = 'Passer en saisie manuelle';
      inp.value = '';
    }
    majApercu();
    majApercuLettre();
  });

  document.getElementById('btn-pdf')?.addEventListener('click', genererPDF);
  document.getElementById('btn-effacer-brouillon')
    ?.addEventListener('click', effacerBrouillon);
}


// ==================== ÉVÉNEMENTS LETTRE ====================
function initEvenementsLettre() {
  document.querySelectorAll('[data-champ-l]').forEach(el => {
    el.addEventListener('input', majApercuLettre);
    el.addEventListener('change', majApercuLettre);
  });

  const btnPdf = document.getElementById('btn-pdf-lettre');
  if (btnPdf) btnPdf.addEventListener('click', genererPDFLettre);

  const dateInput = document.querySelector('[data-champ-l="date_lettre"]');
  if (dateInput && !dateInput.value) {
    dateInput.value = new Date().toISOString().split('T')[0];
    majApercuLettre();
  }
}


// ==================== PREMIUM / STRIPE ====================
function initPremium() {
  document.getElementById('btn-debloquer')
    ?.addEventListener('click', () => ouvrirModalePremium());

  document.getElementById('premium-x')
    ?.addEventListener('click', fermerModalePremium);
  document.getElementById('modale-premium')?.addEventListener('click', (e) => {
    if (e.target.id === 'modale-premium') fermerModalePremium();
  });

  document.getElementById('btn-payer')
    ?.addEventListener('click', lancerPaiementStripe);

  document.getElementById('btn-code')?.addEventListener('click', () => {
    const zone = document.getElementById('premium-code-zone');
    if (zone) zone.style.display = zone.style.display === 'none' ? 'flex' : 'none';
  });

  document.getElementById('btn-activer-code')
    ?.addEventListener('click', activerPremiumParCode);
  document.getElementById('premium-code-input')
    ?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') activerPremiumParCode();
    });

  document.getElementById('btn-payer-premium')
    ?.addEventListener('click', lancerPaiementStripe);

  document.getElementById('btn-code-premium')?.addEventListener('click', () => {
    ouvrirModalePremium();
    const zone = document.getElementById('premium-code-zone');
    if (zone) zone.style.display = 'flex';
  });
}


function ouvrirModalePremium(contexte) {
  const modale = document.getElementById('modale-premium');
  if (!modale) return;
  modale.classList.add('ouverte');
  if (contexte) console.log('Premium requis pour :', contexte);
}


function fermerModalePremium() {
  document.getElementById('modale-premium')?.classList.remove('ouverte');
}


// ==================== PAIEMENT STRIPE (avec forçage inscription) ====================
async function lancerPaiementStripe() {
  // ⭐ ÉTAPE 1 : L'utilisateur est-il connecté ?
  if (!utilisateurConnecte) {
    // Fermer la modale Premium
    fermerModalePremium();

    // Ouvrir la modale "Compte requis"
    ouvrirModaleCompteRequis();
    return;
  }

  // ⭐ ÉTAPE 2 : L'utilisateur est-il déjà premium ?
  if (utilisateurPremium) {
    afficherToast('⭐ Vous êtes déjà Premium !');
    return;
  }

  // ⭐ ÉTAPE 3 : Lancer le paiement
  const btn = document.getElementById('btn-payer');
  const texteOriginal = btn ? btn.textContent : '';
  if (btn) {
    btn.disabled = true;
    btn.textContent = '⏳ Redirection vers Stripe...';
  }

  try {
    const res = await fetch('/api/stripe/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    const json = await res.json();

    if (json.success && json.checkout_url) {
      window.location.href = json.checkout_url;
    } else if (json.need_account) {
      // Cas de sécurité : le serveur exige un compte
      fermerModalePremium();
      ouvrirModaleCompteRequis();
    } else {
      afficherToast('❌ ' + (json.error || 'Erreur de paiement'));
      if (btn) {
        btn.disabled = false;
        btn.textContent = texteOriginal;
      }
    }
  } catch (e) {
    console.error('Erreur Stripe', e);
    afficherToast('❌ Erreur de connexion à Stripe');
    if (btn) {
      btn.disabled = false;
      btn.textContent = texteOriginal;
    }
  }
}


// ==================== MODALE "COMPTE REQUIS" ====================
function ouvrirModaleCompteRequis() {
  const modale = document.getElementById('modale');
  const titre = document.getElementById('modale-titre');
  const texte = document.getElementById('modale-texte');
  const btnOk = document.getElementById('modale-ok');
  const modaleIco = modale?.querySelector('.modale-ico');

  if (modaleIco) modaleIco.textContent = '🔐';
  if (titre) titre.textContent = 'Compte requis';
  if (texte) {
    texte.innerHTML = `
      <div style="text-align:center;">
        <p style="margin-bottom:16px; color:#34495e;">
          Pour passer à <b>CVPro Premium</b>, vous devez d'abord créer un compte gratuit.
        </p>

        <div style="background:#f9fbfc; padding:16px; border-radius:12px;
                    margin-bottom:20px; text-align:left;">
          <p style="margin:0 0 8px 0; font-size:.85rem; color:#64748b;">
            <b>Pourquoi ?</b> Votre paiement sera lié à votre compte, ce qui vous permet de :
          </p>
          <ul style="margin:0; padding-left:20px; font-size:.85rem; color:#64748b;">
            <li>✅ Retrouver votre Premium à chaque connexion</li>
            <li>✅ Accéder depuis n'importe quel appareil</li>
            <li>✅ Ne jamais perdre votre achat</li>
          </ul>
        </div>

        <a href="/register"
           style="display:inline-block; margin:6px 0; padding:14px 28px;
                  background:linear-gradient(135deg, #7c3aed, #f39c12);
                  color:#fff; border-radius:10px;
                  text-decoration:none; font-weight:700; font-size:.95rem;
                  box-shadow:0 6px 20px rgba(124,58,237,.3);">
          ✨ Créer un compte gratuit (30 sec)
        </a>
        <br>
        <a href="/login"
           style="display:inline-block; margin-top:12px; color:#f39c12;
                  font-weight:600; font-size:.9rem; text-decoration:none;">
          Déjà un compte ? Connectez-vous
        </a>
      </div>
    `;
  }
  if (btnOk) {
    btnOk.textContent = 'Plus tard';
    btnOk.onclick = fermerModale;
  }
  if (modale) modale.classList.add('ouverte');
}


// ==================== ACTIVATION PAR CODE ====================
async function activerPremiumParCode() {
  if (!utilisateurConnecte) {
    fermerModalePremium();
    ouvrirModaleCompteRequis();
    return;
  }

  const input = document.getElementById('premium-code-input');
  const code = (input?.value || '').trim().toUpperCase();
  if (!code) {
    afficherToast('⚠️ Entrez un code');
    return;
  }

  try {
    const res = await fetch('/api/premium/activer-code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code })
    });
    const json = await res.json();

    if (json.success) {
      afficherToast('🎉 Premium activé ! Rechargement...');
      setTimeout(() => location.reload(), 1200);
    } else {
      afficherToast('❌ ' + (json.message || 'Code invalide'));
    }
  } catch (e) {
    afficherToast('❌ Erreur lors de l\'activation');
  }
}


// ==================== FILIGRANE ====================
function ajouterFiligrane(html) {
  if (utilisateurPremium) return html;

  const filigrane = `
    <div class="filigrane-cv">CVPRO GRATUIT</div>
    <div class="filigrane-bas">Généré avec CVPro — Version gratuite</div>
  `;
  return html.replace('</body>', filigrane + '</body>');
}


// ==================== APERÇU CV ====================
async function majApercu() {
  const data = collecterDonnees();
  try {
    const res = await fetch('/api/apercu', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const json = await res.json();
    const htmlAvecFiligrane = ajouterFiligrane(json.html);
    const iframe = document.getElementById('apercu');
    if (iframe) iframe.srcdoc = htmlAvecFiligrane;
  } catch (e) {
    console.error('Erreur aperçu CV', e);
  }
}


// ==================== APERÇU LETTRE ====================
async function majApercuLettre() {
  const iframe = document.getElementById('apercu-lettre');
  if (!iframe) return;

  const data = collecterDonneesLettre();
  try {
    const res = await fetch('/api/lettre/apercu', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const json = await res.json();
    iframe.srcdoc = json.html;
  } catch (e) {
    console.error('Erreur aperçu lettre', e);
  }
}


// ==================== COLLECTE CV ====================
function collecterDonnees() {
  const data = { modele: modeleActif };

  document.querySelectorAll('[data-champ]').forEach(el => {
    data[el.dataset.champ] = el.value.trim();
  });

  if (photoData) data.photo = photoData;

  const couleur = getCouleurChoisie();
  if (couleur) data.couleur_perso = couleur;
  const police = getPoliceChoisie();
  if (police) data.police_perso = police;

  data.competences = (document.getElementById('competences')?.value || '')
    .split('\n').map(s => s.trim()).filter(Boolean);
  data.certifications = (document.getElementById('certifications')?.value || '')
    .split('\n').map(s => s.trim()).filter(Boolean);
  data.interets = (document.getElementById('interets')?.value || '')
    .split('\n').map(s => s.trim()).filter(Boolean);

  data.experiences = [];
  document.querySelectorAll('#liste-experiences .item-dyn').forEach(item => {
    data.experiences.push({
      poste: item.querySelector('[data-exp="poste"]')?.value.trim() || '',
      entreprise: item.querySelector('[data-exp="entreprise"]')?.value.trim() || '',
      lieu: item.querySelector('[data-exp="lieu"]')?.value.trim() || '',
      debut: item.querySelector('[data-exp="debut"]')?.value.trim() || '',
      fin: item.querySelector('[data-exp="fin"]')?.value.trim() || '',
      description: item.querySelector('[data-exp="description"]')?.value.trim() || ''
    });
  });

  data.formations = [];
  document.querySelectorAll('#liste-formations .item-dyn').forEach(item => {
    data.formations.push({
      diplome: item.querySelector('[data-form="diplome"]')?.value.trim() || '',
      etablissement: item.querySelector('[data-form="etablissement"]')?.value.trim() || '',
      lieu: item.querySelector('[data-form="lieu"]')?.value.trim() || '',
      debut: item.querySelector('[data-form="debut"]')?.value.trim() || '',
      fin: item.querySelector('[data-form="fin"]')?.value.trim() || '',
      description: item.querySelector('[data-form="description"]')?.value.trim() || ''
    });
  });

  data.langues = [];
  document.querySelectorAll('#liste-langues .item-dyn').forEach(item => {
    data.langues.push({
      langue: item.querySelector('[data-lang="langue"]')?.value.trim() || '',
      niveau: item.querySelector('[data-lang="niveau"]')?.value.trim() || ''
    });
  });

  return data;
}


// ==================== COLLECTE LETTRE ====================
function collecterDonneesLettre() {
  const data = { modele: modeleLettreActif };
  document.querySelectorAll('[data-champ-l]').forEach(el => {
    data[el.dataset.champL] = el.value.trim();
  });
  return data;
}


// ==================== AJOUT DYNAMIQUE ====================
function ajouterExperience() {
  const conteneur = document.getElementById('liste-experiences');
  if (!conteneur) return;

  const div = document.createElement('div');
  div.className = 'item-dyn';
  div.innerHTML = `
    <button type="button" class="suppr" aria-label="Supprimer">×</button>
    <div class="grille-2">
      <label>Poste<input type="text" data-exp="poste" placeholder="Développeur"></label>
      <label>Entreprise<input type="text" data-exp="entreprise" placeholder="TechCorp"></label>
      <label>Lieu<input type="text" data-exp="lieu" placeholder="Paris"></label>
      <label>Début<span class="date-champ"><input type="date" data-exp="debut"><button type="button" class="date-toggle" title="Saisie manuelle">📅</button></span></label>
      <label>Fin<span class="date-champ"><input type="date" data-exp="fin"><button type="button" class="date-toggle" title="Saisie manuelle">📅</button></span></label>
      <label class="large">Description<textarea data-exp="description" rows="2" placeholder="Missions..."></textarea></label>
    </div>
  `;
  div.querySelector('.suppr').addEventListener('click', () => {
    div.remove(); majApercu(); declencherSauvegarde();
  });
  div.querySelectorAll('input, textarea').forEach(el => {
    el.addEventListener('input', () => { majApercu(); declencherSauvegarde(); });
    el.addEventListener('change', () => { majApercu(); declencherSauvegarde(); });
  });
  conteneur.appendChild(div);
}

function ajouterFormation() {
  const conteneur = document.getElementById('liste-formations');
  if (!conteneur) return;

  const div = document.createElement('div');
  div.className = 'item-dyn';
  div.innerHTML = `
    <button type="button" class="suppr" aria-label="Supprimer">×</button>
    <div class="grille-2">
      <label>Diplôme<input type="text" data-form="diplome" placeholder="Master Informatique"></label>
      <label>Établissement<input type="text" data-form="etablissement" placeholder="Université Paris"></label>
      <label>Lieu<input type="text" data-form="lieu" placeholder="Paris"></label>
      <label>Début<span class="date-champ"><input type="date" data-form="debut"><button type="button" class="date-toggle" title="Saisie manuelle">📅</button></span></label>
      <label>Fin<span class="date-champ"><input type="date" data-form="fin"><button type="button" class="date-toggle" title="Saisie manuelle">📅</button></span></label>
      <label class="large">Description<textarea data-form="description" rows="2" placeholder="Mention..."></textarea></label>
    </div>
  `;
  div.querySelector('.suppr').addEventListener('click', () => {
    div.remove(); majApercu(); declencherSauvegarde();
  });
  div.querySelectorAll('input, textarea').forEach(el => {
    el.addEventListener('input', () => { majApercu(); declencherSauvegarde(); });
    el.addEventListener('change', () => { majApercu(); declencherSauvegarde(); });
  });
  conteneur.appendChild(div);
}

function ajouterLangue() {
  const conteneur = document.getElementById('liste-langues');
  if (!conteneur) return;

  const div = document.createElement('div');
  div.className = 'item-dyn';
  div.innerHTML = `
    <button type="button" class="suppr" aria-label="Supprimer">×</button>
    <div class="grille-2">
      <label>Langue<input type="text" data-lang="langue" placeholder="Anglais"></label>
      <label>Niveau<input type="text" data-lang="niveau" placeholder="Courant (C1)"></label>
    </div>
  `;
  div.querySelector('.suppr').addEventListener('click', () => {
    div.remove(); majApercu(); declencherSauvegarde();
  });
  div.querySelectorAll('input').forEach(el => {
    el.addEventListener('input', () => { majApercu(); declencherSauvegarde(); });
  });
  conteneur.appendChild(div);
}


// ==================== PHOTO ====================
function gererPhoto(e) {
  const file = e.target.files[0];
  if (!file) return;
  if (file.size > 500 * 1024) {
    afficherToast('⚠️ Photo trop volumineuse (max 500 Ko)');
    return;
  }
  const reader = new FileReader();
  reader.onload = (ev) => {
    photoData = ev.target.result;
    const apercu = document.getElementById('photo-apercu');
    if (apercu) apercu.innerHTML = `<img src="${photoData}" alt="Photo">`;
    majApercu();
    declencherSauvegarde();
  };
  reader.readAsDataURL(file);
}

function supprimerPhoto() {
  photoData = null;
  const apercu = document.getElementById('photo-apercu');
  if (apercu) apercu.innerHTML = '👤';
  const input = document.getElementById('photo-input');
  if (input) input.value = '';
  majApercu();
  declencherSauvegarde();
}


// ==================== COULEUR ====================
function initCouleur() {
  const inputColor = document.getElementById('choix-couleur');
  const palette = document.querySelectorAll('.pastille-couleur');
  if (!inputColor) return;

  inputColor.addEventListener('input', () => {
    majApercu(); declencherSauvegarde();
  });

  palette.forEach(p => {
    p.addEventListener('click', () => {
      const couleur = p.dataset.couleur;
      inputColor.value = couleur;
      palette.forEach(x => x.classList.remove('actif'));
      p.classList.add('actif');
      majApercu();
      declencherSauvegarde();
    });
  });
}

function getCouleurChoisie() {
  const el = document.getElementById('choix-couleur');
  return el ? el.value : null;
}


// ==================== POLICE ====================
function initPolice() {
  const select = document.getElementById('choix-police');
  if (!select) return;
  select.addEventListener('change', () => {
    majApercu(); declencherSauvegarde();
  });
}

function getPoliceChoisie() {
  const el = document.getElementById('choix-police');
  return el ? el.value : null;
}


// ==================== SAUVEGARDE AUTO ====================
function initSauvegardeAuto() {
  document.addEventListener('input', (e) => {
    if (e.target.matches('[data-champ], [data-champ-l], #competences, #certifications, #interets, #choix-couleur, #choix-police')) {
      declencherSauvegarde();
    }
  });
  document.addEventListener('change', (e) => {
    if (e.target.matches('[data-champ], [data-champ-l]')) {
      declencherSauvegarde();
    }
  });
}

function sauvegarderBrouillon() {
  try {
    const data = collecterDonnees();
    const couleurChoisie = document.getElementById('choix-couleur')?.value;
    const policeChoisie = document.getElementById('choix-police')?.value;
    if (couleurChoisie) data.couleur_perso = couleurChoisie;
    if (policeChoisie) data.police_perso = policeChoisie;
    data._sauvegarde_le = new Date().toISOString();

    localStorage.setItem(CLE_BROUILLON, JSON.stringify(data));
    dernierSauvegardeReussie = new Date();
    majIndicateurSauvegarde('ok');
  } catch (e) {
    console.error('Erreur sauvegarde', e);
    majIndicateurSauvegarde('erreur');
  }
}

function declencherSauvegarde() {
  majIndicateurSauvegarde('encours');
  clearTimeout(timerSauvegardeAuto);
  timerSauvegardeAuto = setTimeout(sauvegarderBrouillon, 1500);
}

function majIndicateurSauvegarde(etat) {
  const barre = document.getElementById('sauvegarde-barre');
  const ico = document.getElementById('sauvegarde-ico');
  const txt = document.getElementById('sauvegarde-texte');
  if (!barre) return;

  barre.classList.remove('sauvegarde-encours', 'sauvegarde-erreur');

  if (etat === 'encours') {
    barre.classList.add('sauvegarde-encours');
    if (ico) ico.textContent = '⏳';
    if (txt) txt.textContent = 'Sauvegarde en cours...';
  } else if (etat === 'erreur') {
    barre.classList.add('sauvegarde-erreur');
    if (ico) ico.textContent = '❌';
    if (txt) txt.textContent = 'Erreur de sauvegarde';
  } else {
    if (ico) ico.textContent = '💾';
    const heure = dernierSauvegardeReussie
      ? dernierSauvegardeReussie.toLocaleTimeString('fr-FR',
          { hour: '2-digit', minute: '2-digit' })
      : '';
    if (txt) txt.textContent = heure
      ? `Sauvegardé à ${heure}`
      : 'Sauvegarde automatique activée';
  }
}

function chargerBrouillon() {
  try {
    const json = localStorage.getItem(CLE_BROUILLON);
    if (!json) return;
    const data = JSON.parse(json);

    Object.keys(data).forEach(key => {
      if (key.startsWith('_')) return;
      const el = document.querySelector(`[data-champ="${key}"]`);
      if (el && typeof data[key] === 'string') el.value = data[key];
    });

    if (data.competences) {
      const el = document.getElementById('competences');
      if (el) el.value = data.competences.join('\n');
    }
    if (data.certifications) {
      const el = document.getElementById('certifications');
      if (el) el.value = data.certifications.join('\n');
    }
    if (data.interets) {
      const el = document.getElementById('interets');
      if (el) el.value = data.interets.join('\n');
    }

    if (data.experiences && data.experiences.length > 0) {
      const conteneur = document.getElementById('liste-experiences');
      if (conteneur) {
        conteneur.innerHTML = '';
        data.experiences.forEach(exp => {
          ajouterExperience();
          const items = conteneur.querySelectorAll('.item-dyn');
          const last = items[items.length - 1];
          last.querySelector('[data-exp="poste"]').value = exp.poste || '';
          last.querySelector('[data-exp="entreprise"]').value = exp.entreprise || '';
          last.querySelector('[data-exp="lieu"]').value = exp.lieu || '';
          last.querySelector('[data-exp="debut"]').value = exp.debut || '';
          last.querySelector('[data-exp="fin"]').value = exp.fin || '';
          last.querySelector('[data-exp="description"]').value = exp.description || '';
        });
      }
    }

    if (data.formations && data.formations.length > 0) {
      const conteneur = document.getElementById('liste-formations');
      if (conteneur) {
        conteneur.innerHTML = '';
        data.formations.forEach(form => {
          ajouterFormation();
          const items = conteneur.querySelectorAll('.item-dyn');
          const last = items[items.length - 1];
          last.querySelector('[data-form="diplome"]').value = form.diplome || '';
          last.querySelector('[data-form="etablissement"]').value = form.etablissement || '';
          last.querySelector('[data-form="lieu"]').value = form.lieu || '';
          last.querySelector('[data-form="debut"]').value = form.debut || '';
          last.querySelector('[data-form="fin"]').value = form.fin || '';
          last.querySelector('[data-form="description"]').value = form.description || '';
        });
      }
    }

    if (data.langues && data.langues.length > 0) {
      const conteneur = document.getElementById('liste-langues');
      if (conteneur) {
        conteneur.innerHTML = '';
        data.langues.forEach(l => {
          ajouterLangue();
          const items = conteneur.querySelectorAll('.item-dyn');
          const last = items[items.length - 1];
          last.querySelector('[data-lang="langue"]').value = l.langue || '';
          last.querySelector('[data-lang="niveau"]').value = l.niveau || '';
        });
      }
    }

    if (data.couleur_perso) {
      const el = document.getElementById('choix-couleur');
      if (el) el.value = data.couleur_perso;
    }
    if (data.police_perso) {
      const el = document.getElementById('choix-police');
      if (el) el.value = data.police_perso;
    }

    if (data.modele) modeleActif = data.modele;

    if (data.photo) {
      photoData = data.photo;
      const apercu = document.getElementById('photo-apercu');
      if (apercu) apercu.innerHTML = `<img src="${photoData}" alt="Photo">`;
    }

    if (data._sauvegarde_le) {
      dernierSauvegardeReussie = new Date(data._sauvegarde_le);
    }
    majIndicateurSauvegarde('ok');
  } catch (e) {
    console.error('Erreur restauration brouillon', e);
  }
}

function effacerBrouillon() {
  if (!confirm('Effacer le brouillon sauvegardé ?\n\nToutes vos données actuelles seront perdues.')) return;
  localStorage.removeItem(CLE_BROUILLON);
  location.reload();
}


// ==================== PDF CV ====================
async function genererPDF() {
  const btn = document.getElementById('btn-pdf');
  const texteOriginal = btn.textContent;
  btn.disabled = true;
  btn.textContent = '⏳ Génération du PDF...';

  let conteneur = null;

  try {
    const data = collecterDonnees();
    if (!data.nom && !data.prenom) {
      afficherToast('⚠️ Saisissez au moins votre nom ou prénom');
      return;
    }

    const res = await fetch('/api/apercu', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const json = await res.json();

    conteneur = document.createElement('div');
    conteneur.style.cssText =
      'position:fixed;left:-9999px;top:0;width:210mm;background:#fff;';
    conteneur.innerHTML = json.html;

    if (!utilisateurPremium) {
      const filigrane = document.createElement('div');
      filigrane.className = 'filigrane-cv';
      filigrane.textContent = 'CVPRO GRATUIT';
      conteneur.appendChild(filigrane);

      const filigraneBas = document.createElement('div');
      filigraneBas.className = 'filigrane-bas';
      filigraneBas.textContent = 'Généré avec CVPro — Version gratuite';
      conteneur.appendChild(filigraneBas);
    }

    document.body.appendChild(conteneur);

    const images = conteneur.querySelectorAll('img');
    await Promise.all(Array.from(images).map(img => img.complete
      ? Promise.resolve()
      : new Promise(r => { img.onload = r; img.onerror = r; })));

    await new Promise(r => setTimeout(r, 150));

    const nom = (data.nom || 'CV').replace(/\s+/g, '_');
    const prenom = (data.prenom || '').replace(/\s+/g, '_');
    const nomFichier = `CV_${prenom}_${nom}.pdf`.replace(/__+/g, '_');

    await html2pdf().set({
      margin: [10, 10, 10, 10],
      filename: nomFichier,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true, letterRendering: true, logging: false, backgroundColor: '#ffffff' },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
      pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
    }).from(conteneur).save();

    document.body.removeChild(conteneur);
    conteneur = null;

    await incrementerTelechargement('cv');
    afficherToast('✅ PDF téléchargé sur votre ordinateur !');

  } catch (e) {
    console.error('Erreur PDF CV', e);
    afficherToast('❌ Erreur lors de la génération du PDF');
  } finally {
    if (conteneur && conteneur.parentNode) conteneur.parentNode.removeChild(conteneur);
    btn.disabled = false;
    btn.textContent = texteOriginal;
  }
}


// ==================== PDF LETTRE ====================
async function genererPDFLettre() {
  const btn = document.getElementById('btn-pdf-lettre');
  const texteOriginal = btn.textContent;
  btn.disabled = true;
  btn.textContent = '⏳ Génération de la lettre...';

  let conteneur = null;

  try {
    const data = collecterDonneesLettre();
    if (!data.nom && !data.prenom) {
      afficherToast('⚠️ Saisissez au moins votre nom ou prénom');
      return;
    }
    if (!data.entreprise) {
      afficherToast('⚠️ Saisissez le nom de l\'entreprise');
      return;
    }

    const res = await fetch('/api/lettre/apercu', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const json = await res.json();

    conteneur = document.createElement('div');
    conteneur.style.cssText =
      'position:fixed;left:-9999px;top:0;width:210mm;background:#fff;';
    conteneur.innerHTML = json.html;
    document.body.appendChild(conteneur);

    await new Promise(r => setTimeout(r, 150));

    const nom = (data.nom || 'Lettre').replace(/\s+/g, '_');
    const prenom = (data.prenom || '').replace(/\s+/g, '_');
    const nomFichier = `Lettre_${prenom}_${nom}.pdf`.replace(/__+/g, '_');

    await html2pdf().set({
      margin: [10, 10, 10, 10],
      filename: nomFichier,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true, letterRendering: true, logging: false, backgroundColor: '#ffffff' },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
      pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
    }).from(conteneur).save();

    document.body.removeChild(conteneur);
    conteneur = null;

    await incrementerTelechargement('lettre');
    afficherToast('✅ Lettre téléchargée sur votre ordinateur !');

  } catch (e) {
    console.error('Erreur PDF lettre', e);
    afficherToast('❌ Erreur lors de la génération de la lettre');
  } finally {
    if (conteneur && conteneur.parentNode) conteneur.parentNode.removeChild(conteneur);
    btn.disabled = false;
    btn.textContent = texteOriginal;
  }
}


// ==================== COMPTEURS ====================
async function incrementerTelechargement(type) {
  const url = type === 'lettre'
    ? '/api/stats/telechargement-lettre'
    : '/api/stats/telechargement';

  try {
    const res = await fetch(url, { method: 'POST' });
    if (!res.ok) return;
    const stats = await res.json();
    majCompteurs(stats);
  } catch (e) {
    console.error('Erreur compteur', e);
  }
}


// ==================== MODALE GÉNÉRIQUE ====================
function ouvrirModale(sujet) {
  const titre = document.getElementById('modale-titre');
  const texte = document.getElementById('modale-texte');
  const modale = document.getElementById('modale');
  const btnOk = document.getElementById('modale-ok');
  const ico = modale?.querySelector('.modale-ico');

  if (ico) ico.textContent = '🚧';
  if (titre) titre.textContent = sujet;
  if (texte) texte.textContent =
    `La section "${sujet}" est en cours de développement. Elle sera disponible très prochainement.`;
  if (btnOk) {
    btnOk.textContent = 'Compris';
    btnOk.onclick = fermerModale;
  }
  if (modale) modale.classList.add('ouverte');
}

function fermerModale() {
  document.getElementById('modale')?.classList.remove('ouverte');
}

// ==================== SAUVEGARDE CV EN BASE ====================



function ouvrirModaleSauvegarde() {
  console.log('🔵 Ouverture de la modale de sauvegarde');

  const modale = document.getElementById('modale-sauvegarde');
  if (!modale) {
    console.error('❌ Modale #modale-sauvegarde introuvable dans le HTML');
    alert('Erreur : la modale de sauvegarde n\'existe pas. Vérifiez index.html');
    return;
  }

  const input = document.getElementById('input-titre-cv');
  if (input) {
    // Suggestion automatique
    const nom = document.querySelector('[data-champ="nom"]')?.value.trim() || '';
    const prenom = document.querySelector('[data-champ="prenom"]')?.value.trim() || '';
    const titrePoste = document.querySelector('[data-champ="titre"]')?.value.trim() || '';

    if (prenom && nom) {
      input.value = `CV ${prenom} ${nom}${titrePoste ? ' — ' + titrePoste : ''}`;
    } else {
      input.value = '';
    }
    setTimeout(() => { input.focus(); input.select(); }, 100);
  }

  modale.classList.add('ouverte');
}


function fermerModaleSauvegarde() {
  document.getElementById('modale-sauvegarde')?.classList.remove('ouverte');
}


async function confirmerSauvegarde() {
  console.log('🔵 Tentative de sauvegarde');

  const input = document.getElementById('input-titre-cv');
  const titre = (input?.value || '').trim();

  if (!titre) {
    afficherToast('⚠️ Entrez un titre pour ce CV');
    input?.focus();
    return;
  }

  // Récupérer les données du formulaire
  const data = collecterDonnees();
  if (!data.nom && !data.prenom) {
    afficherToast('⚠️ Remplissez au moins le nom ou prénom');
    return;
  }

  const payload = {
    cv_id: cvEnCoursId,
    titre: titre,
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
      afficherToast(json.action === 'created'
        ? '✅ CV sauvegardé !'
        : '✅ CV mis à jour !');
    } else if (json.limite_atteinte) {
      fermerModaleSauvegarde();
      alert('⚠️ Limite de 3 CV atteinte.\n\nPassez à CVPro Premium pour en sauvegarder plus.');
    } else {
      afficherToast('❌ ' + (json.error || 'Erreur'));
    }
  } catch (e) {
    console.error('Erreur sauvegarde', e);
    afficherToast('❌ Erreur de connexion');
  } finally {
    btn.disabled = false;
    btn.textContent = texteOrig;
  }
}


// ==================== ÉCOUTEURS ====================
document.addEventListener('DOMContentLoaded', () => {
  // Bouton "Sauvegarder ce CV"
  document.getElementById('btn-sauvegarder-cv')
    ?.addEventListener('click', ouvrirModaleSauvegarde);

  // Fermer modale
  document.getElementById('modale-sauv-x')
    ?.addEventListener('click', fermerModaleSauvegarde);

  document.getElementById('btn-annuler-sauv')
    ?.addEventListener('click', fermerModaleSauvegarde);

  // Confirmer
  document.getElementById('btn-confirmer-sauv')
    ?.addEventListener('click', confirmerSauvegarde);

  // Entrée
  document.getElementById('input-titre-cv')
    ?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') confirmerSauvegarde();
    });

  // Clic en dehors
  document.getElementById('modale-sauvegarde')
    ?.addEventListener('click', (e) => {
      if (e.target.id === 'modale-sauvegarde') fermerModaleSauvegarde();
    });

  // Échap
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') fermerModaleSauvegarde();
  });
});
// ==================== TOAST ====================
function afficherToast(msg) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('visible');
  setTimeout(() => t.classList.remove('visible'), 3000);
}

// ==================== MODALE DÉTAIL ====================


function ouvrirModaleDetail(index) {
  const offres = window.offresActuelles || [];
  const offre = offres[index];
  if (!offre) return;

  offreDetailEnCours = offre;

  const contenu = document.getElementById('detail-contenu');

  // Construire les badges
  let badges = '';
  if (offre.type_contrat) {
    badges += `<span class="badge-detail badge-contrat">${escapeHtml(offre.type_contrat)}</span>`;
  }
  if (offre.lieu) {
    badges += `<span class="badge-detail badge-lieu">📍 ${escapeHtml(offre.lieu)}</span>`;
  }
  if (offre.salaire && offre.salaire !== 'Non précisé') {
    badges += `<span class="badge-detail badge-salaire">💰 ${escapeHtml(offre.salaire)}</span>`;
  }
  if (offre.date_creation) {
    badges += `<span class="badge-detail badge-date">📅 ${escapeHtml(offre.date_creation)}</span>`;
  }

  // Compétences
  let compHtml = '';
  if (offre.competences && offre.competences.length > 0) {
    compHtml = `
      <div class="detail-section">
        <h4>🎯 Compétences demandées</h4>
        <div class="detail-tags">
          ${offre.competences.map(c => `<span>${escapeHtml(c)}</span>`).join('')}
        </div>
      </div>
    `;
  }

  contenu.innerHTML = `
    <h2 class="detail-titre">${escapeHtml(offre.titre)}</h2>
    <p class="detail-entreprise">🏢 <b>${escapeHtml(offre.entreprise)}</b></p>
    <div class="detail-badges">${badges}</div>

    ${offre.description ? `
      <div class="detail-section">
        <h4>📋 Description du poste</h4>
        <div class="detail-description">${escapeHtml(offre.description)}</div>
      </div>
    ` : ''}

    ${compHtml}
  `;

  // Configurer le lien externe
  const lienExterne = document.getElementById('detail-lien-externe');
  if (lienExterne) {
    lienExterne.href = offre.url || '#';
  }

  // Ouvrir
  document.getElementById('modale-detail').classList.add('ouverte');
}

function fermerModaleDetail() {
  document.getElementById('modale-detail').classList.remove('ouverte');
}

function postulerDepuisDetail() {
  // Trouver l'index de l'offre dans la liste
  const offres = window.offresActuelles || [];
  const index = offres.findIndex(o => o.id === offreDetailEnCours.id);

  fermerModaleDetail();

  if (index >= 0) {
    ouvrirModalePostuler(index);
  }
}

// Fermer avec Échap
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') fermerModaleDetail();
});

// Clic en dehors
document.getElementById('modale-detail')?.addEventListener('click', (e) => {
  if (e.target.id === 'modale-detail') fermerModaleDetail();
});



// ==================== BANDEAU OFFRES ====================
async function chargerBandeauEmplois() {
  try {
    const res = await fetch('/api/emplois/apercu');
    const json = await res.json();

    const contenu = document.getElementById('bandeau-contenu');
    if (!contenu) return;

    if (!json.success || !json.offres || json.offres.length === 0) {
      contenu.innerHTML = `
        <span class="bandeau-offre">
          Aucune offre disponible pour le moment
        </span>
      `;
      return;
    }

    // Construire les offres
    let html = '';
    json.offres.forEach(o => {
      const titre = escapeHtml(o.titre || 'Sans titre');
      const entreprise = escapeHtml(o.entreprise || '');
      const lieu = escapeHtml((o.lieu || '').split(',')[0].trim());

      html += `
        <span class="bandeau-offre">
          🔥 <b>${titre}</b>
          ${entreprise ? ` · ${entreprise}` : ''}
          ${lieu ? ` · 📍 ${lieu}` : ''}
        </span>
        <span class="bandeau-sep">•</span>
      `;
    });

    // Dupliquer pour un défilement infini
    contenu.innerHTML = html + html;

  } catch (e) {
    console.error('Erreur bandeau', e);
  }
}

// Échapper le HTML (sécurité XSS)
function escapeHtml(s) {
  if (!s) return '';
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

// Charger au démarrage
document.addEventListener('DOMContentLoaded', () => {
  chargerBandeauEmplois();
  // Rafraîchir toutes les 5 minutes
  setInterval(chargerBandeauEmplois, 300000);
});



(function(){
  const API = '/releve';
  const MOIS = ['Janvier','Février','Mars','Avril','Mai','Juin',
                'Juillet','Août','Septembre','Octobre','Novembre','Décembre'];

  const pad2 = n => String(n).padStart(2,'0');
  const iso  = (y,m,d) => y+'-'+pad2(m+1)+'-'+pad2(d);
  const todayIso = () => { const d=new Date(); return iso(d.getFullYear(),d.getMonth(),d.getDate()); };
  const hToMin = t => { const [h,m]=String(t||'00:00').split(':').map(Number); return h*60+(m||0); };
  const minToH = t => { const v=((t%1440)+1440)%1440; return pad2(Math.floor(v/60))+':'+pad2(v%60); };
  const fmtMin = m => { const h=Math.floor(m/60), mm=m%60; return mm===0? h+'h' : h+'h'+pad2(mm); };
  const dateLongue = k => { const [y,m,d]=k.split('-').map(Number); return pad2(d)+'/'+pad2(m)+'/'+y; };
  const diffMinutes = (d,f) => { let x=hToMin(f)-hToMin(d); return x<0? x+1440 : x; };

  let settings = { duree_defaut_minutes:480, pause_defaut_minutes:60, heure_debut_defaut:'08:00' };
  let days = {};
  let view = { y:0, m:0 };
  let editingDate = null;

  const $ = id => document.getElementById(id);
  const dayOverlay      = $('releve-dayOverlay');
  const settingsOverlay = $('releve-settingsOverlay');

  /* ============ Rendu ============ */
  function renderSettings(){
    $('releve-setLine1').textContent = fmtMin(settings.duree_defaut_minutes) + ' / jour';
    $('releve-setLine2').textContent = 'Pause : ' + fmtMin(settings.pause_defaut_minutes) +
                                       ' · Début : ' + settings.heure_debut_defaut;
  }

  function renderCalendar(){
    $('releve-monthTitle').textContent = MOIS[view.m] + ' ' + view.y;

    const grid = $('releve-calendar');
    grid.innerHTML = '';

    const premier = new Date(view.y, view.m, 1);
    const decalage = (premier.getDay() + 6) % 7;   // lundi = 0
    const nbJours = new Date(view.y, view.m + 1, 0).getDate();
    const today = todayIso();

    for (let i = 0; i < decalage; i++){
      const p = document.createElement('div');
      p.className = 'cell pad';
      grid.appendChild(p);
    }

    for (let j = 1; j <= nbJours; j++){
      const key = iso(view.y, view.m, j);
      const d = days[key];

      const cell = document.createElement('div');
      cell.className = 'cell'
        + (d ? ' ' + d.statut : '')
        + (key === today ? ' today' : '');
      cell.dataset.date = key;
      if (d && d.commentaire) cell.title = d.commentaire;

      const num = document.createElement('div');
      num.className = 'num';
      num.textContent = j;
      cell.appendChild(num);

      if (d){
        const val = document.createElement('div');
        val.className = 'val';
        val.textContent = d.statut === 'absence' ? 'ABS'
                       : d.statut === 'conge'   ? 'CONGÉ'
                       : fmtMin(d.total_minutes);
        cell.appendChild(val);
      }

      // Clic simple : cycle vide -> travail -> absence -> vide
      let pressTimer = null, pressFired = false;
      cell.addEventListener('click', () => {
        if (pressFired){ pressFired = false; return; }
        cycle(key);
      });
      cell.addEventListener('pointerdown', e => {
        if (e.button !== 0) return;
        pressFired = false;
        clearTimeout(pressTimer);
        pressTimer = setTimeout(() => { pressFired = true; openDay(key); }, 500);
      });
      ['pointerup','pointerleave','pointercancel'].forEach(ev =>
        cell.addEventListener(ev, () => clearTimeout(pressTimer)));
      cell.addEventListener('contextmenu', e => {
        e.preventDefault();
        openDay(key);
      });

      grid.appendChild(cell);
    }
  }

  function renderSummary(){
    let h = 0, t = 0, a = 0, c = 0;
    Object.values(days).forEach(d => {
      if (d.statut === 'absence') a++;
      else if (d.statut === 'conge') c++;
      else { t++; h += d.total_minutes; }
    });
    $('releve-sumHours').textContent = fmtMin(h);
    $('releve-sumDays').textContent  = t;
    $('releve-sumAbs').textContent   = a;
    $('releve-sumConge').textContent = c;
  }

  function render(){ renderCalendar(); renderSummary(); }

  /* ============ API ============ */
  async function chargerSettings(){
    try {
      settings = await fetch(API + '/api/settings').then(r => r.json());
      renderSettings();
    } catch(e){ console.error('settings', e); }
  }

  async function chargerMois(){
    const mois = view.y + '-' + pad2(view.m + 1);
    try {
      const liste = await fetch(API + '/api/days?month=' + mois).then(r => r.json());
      days = {};
      liste.forEach(d => { days[d.date] = d; });
      render();
    } catch(e){ console.error('mois', e); }
  }

  async function chargerTout(){ await chargerSettings(); await chargerMois(); }

  function nouvelleJournee(statut){
    const debut = hToMin(settings.heure_debut_defaut);
    const fin   = debut + settings.duree_defaut_minutes + settings.pause_defaut_minutes;
    return {
      statut,
      heure_debut: settings.heure_debut_defaut,
      heure_fin: minToH(fin),
      pause_minutes: settings.pause_defaut_minutes,
      total_minutes: settings.duree_defaut_minutes,
      commentaire: ''
    };
  }

  async function upsertDay(key, data){
    const res = await fetch(API + '/api/days', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify(Object.assign({}, data, {date:key}))
    });
    days[key] = await res.json();
    render();
  }

  async function deleteDay(key){
    await fetch(API + '/api/days/' + key, {method:'DELETE'});
    delete days[key];
    render();
  }

  async function cycle(key){
    const d = days[key];
    if (!d) await upsertDay(key, nouvelleJournee('travail'));
    else if (d.statut === 'travail' || d.statut === 'modifie')
      await upsertDay(key, Object.assign({}, d, {statut:'absence', total_minutes:0}));
    else await deleteDay(key);
  }

  /* ============ Modale journée ============ */
  function lireDayForm(){
    return {
      statut: $('releve-dStatut').value,
      heure_debut: $('releve-dHeureDebut').textContent,
      heure_fin:   $('releve-dHeureFin').textContent,
      pause_minutes: parseInt($('releve-dPause').value, 10) || 0,
      commentaire: $('releve-dCommentaire').value
    };
  }

  function majTotalDay(){
    const f = lireDayForm();
    const zone = $('releve-dHeuresZone');
    if (f.statut === 'absence' || f.statut === 'conge'){
      zone.style.opacity = '.35';
      zone.style.pointerEvents = 'none';
      $('releve-dTotal').textContent = '0h';
      return;
    }
    zone.style.opacity = '1';
    zone.style.pointerEvents = 'auto';
    const m = Math.max(0, diffMinutes(f.heure_debut, f.heure_fin) - f.pause_minutes);
    $('releve-dTotal').textContent = fmtMin(m);
  }

  async function pickTime(current){
    return new Promise(resolve => {
      const input = document.createElement('input');
      input.type = 'time';
      input.value = current;
      input.style.position = 'fixed';
      input.style.opacity = '0';
      input.style.pointerEvents = 'none';
      document.body.appendChild(input);
      input.addEventListener('change', () => { input.remove(); resolve(input.value); });
      input.addEventListener('blur',   () => { if (input.parentNode){ input.remove(); resolve(null); } });
      if (input.showPicker){ try { input.showPicker(); } catch(e){ input.click(); } }
      else input.click();
    });
  }

  function openDay(key){
    editingDate = key;
    const d = days[key] || nouvelleJournee('travail');

    $('releve-dayTitle').textContent       = 'Journée du ' + dateLongue(key);
    $('releve-dStatut').value               = d.statut;
    $('releve-dHeureDebut').textContent     = d.heure_debut;
    $('releve-dHeureFin').textContent       = d.heure_fin;
    $('releve-dPause').value                = d.pause_minutes;
    $('releve-dCommentaire').value          = d.commentaire || '';
    majTotalDay();
    dayOverlay.hidden = false;
  }

  $('releve-dStatut').addEventListener('change', majTotalDay);
  $('releve-dPause').addEventListener('input', majTotalDay);
  $('releve-dBtnDebut').addEventListener('click', async () => {
    const v = await pickTime($('releve-dHeureDebut').textContent);
    if (v){ $('releve-dHeureDebut').textContent = v; majTotalDay(); }
  });
  $('releve-dBtnFin').addEventListener('click', async () => {
    const v = await pickTime($('releve-dHeureFin').textContent);
    if (v){ $('releve-dHeureFin').textContent = v; majTotalDay(); }
  });
  $('releve-dAnnuler').addEventListener('click', () => dayOverlay.hidden = true);

  $('releve-dEnregistrer').addEventListener('click', async () => {
    const f = lireDayForm();
    let statut = f.statut;
    if (statut === 'travail' || statut === 'modifie'){
      const total = Math.max(0, diffMinutes(f.heure_debut, f.heure_fin) - f.pause_minutes);
      if (statut === 'travail' && total !== settings.duree_defaut_minutes) statut = 'modifie';
      await upsertDay(editingDate, Object.assign({}, f, {statut, total_minutes: total}));
    } else {
      await upsertDay(editingDate, Object.assign({}, f, {statut, total_minutes: 0}));
    }
    dayOverlay.hidden = true;
  });

  /* ============ Modale réglages ============ */
  function majSliderLabel(){
    const v = parseInt($('releve-sDuree').value, 10);
    $('releve-sDureeLabel').textContent = fmtMin(v);
  }
  $('releve-sDuree').addEventListener('input', majSliderLabel);

  function ouvrirReglages(){
    $('releve-sDuree').value = settings.duree_defaut_minutes;
    $('releve-sPause').value = String(settings.pause_defaut_minutes);
    $('releve-sHeureDebut').textContent = settings.heure_debut_defaut;
    majSliderLabel();
    settingsOverlay.hidden = false;
  }
  $('releve-btnSettings').addEventListener('click', ouvrirReglages);
  $('releve-btnSettings2').addEventListener('click', ouvrirReglages);

  $('releve-sBtnDebut').addEventListener('click', async () => {
    const v = await pickTime($('releve-sHeureDebut').textContent);
    if (v) $('releve-sHeureDebut').textContent = v;
  });

  $('releve-sAnnuler').addEventListener('click', () => settingsOverlay.hidden = true);

  $('releve-sEnregistrer').addEventListener('click', async () => {
    const payload = {
      duree_defaut_minutes: parseInt($('releve-sDuree').value, 10),
      pause_defaut_minutes: parseInt($('releve-sPause').value, 10),
      heure_debut_defaut:   $('releve-sHeureDebut').textContent
    };
    const res = await fetch(API + '/api/settings', {
      method: 'PUT',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    settings = await res.json();
    renderSettings();
    settingsOverlay.hidden = true;
  });

  /* Fermer les modales */
  [dayOverlay, settingsOverlay].forEach(ov => {
    ov.addEventListener('click', e => { if (e.target === ov) ov.hidden = true; });
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape'){
      dayOverlay.hidden = true;
      settingsOverlay.hidden = true;
    }
  });

  /* ============ Navigation mois ============ */
  $('releve-prevMonth').addEventListener('click', async () => {
    view.m--; if (view.m < 0){ view.m = 11; view.y--; }
    await chargerMois();
  });
  $('releve-nextMonth').addEventListener('click', async () => {
    view.m++; if (view.m > 11){ view.m = 0; view.y++; }
    await chargerMois();
  });
  $('releve-todayBtn').addEventListener('click', async () => {
    const n = new Date();
    view.y = n.getFullYear(); view.m = n.getMonth();
    await chargerMois();
  });

  /* ============ Actions ============ */
  function afficherStatut(msg, type){
    const el = $('releveActionStatus');
    el.textContent = msg;
    el.className = 'action-status ' + (type || 'info');
    el.hidden = false;
    clearTimeout(afficherStatut._t);
    afficherStatut._t = setTimeout(() => { el.hidden = true; }, 4000);
  }

  $('btnPdf').addEventListener('click', e => {
    e.preventDefault();
    window.open(API + '/export/pdf/' + view.y + '/' + (view.m + 1), '_blank');
    afficherStatut('📄 PDF ouvert — Ctrl+P pour enregistrer', 'info');
  });

  $('btnEmail').addEventListener('click', () => {
    const moisNom = MOIS[view.m] + ' ' + view.y;
    const lignes = [
      'Bonjour,', '',
      `Voici mon relevé d'heures pour ${moisNom} :`, '',
      `• Heures travaillées : ${$('releve-sumHours').textContent}`,
      `• Jours travaillés : ${$('releve-sumDays').textContent}`,
      `• Absences : ${$('releve-sumAbs').textContent}`,
      `• Congés : ${$('releve-sumConge').textContent}`,
      '', 'Détail par jour :'
    ];
    const prefix = view.y + '-' + pad2(view.m + 1) + '-';
    Object.values(days)
      .filter(d => d.date.startsWith(prefix))
      .sort((a,b) => a.date.localeCompare(b.date))
      .forEach(d => {
        const total = d.statut === 'absence' ? 'ABS'
                    : d.statut === 'conge'   ? 'CONGÉ'
                    : fmtMin(d.total_minutes);
        const comm = d.commentaire ? ' — ' + d.commentaire : '';
        lignes.push(`  ${dateLongue(d.date)} : ${d.statut} (${total})${comm}`);
      });
    lignes.push('', 'Cordialement.');
    const sujet = encodeURIComponent(`Relevé d'heures — ${moisNom}`);
    const corps = encodeURIComponent(lignes.join('\n'));
    window.location.href = `mailto:?subject=${sujet}&body=${corps}`;
    afficherStatut('📧 Votre client mail va s\'ouvrir', 'info');
  });

  $('btnSave').addEventListener('click', async () => {
    try {
      const res = await fetch(API + '/export/json');
      if (!res.ok) throw new Error('Erreur serveur');
      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'releve_backup.json';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(a.href);
      afficherStatut('💾 Sauvegarde téléchargée', 'ok');
    } catch (err) {
      afficherStatut('❌ ' + err.message, 'err');
    }
  });

  /* ============ Démarrage ============ */
  (function boot(){
    const n = new Date();
    view.y = n.getFullYear();
    view.m = n.getMonth();
    chargerTout();
  })();

})();








