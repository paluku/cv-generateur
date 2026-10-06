# ============================================================
# API APERÇU CV POUR FLUTTER
# ============================================================
from flask import Blueprint, request, jsonify, render_template
from datetime import datetime
import re

cv_render_bp = Blueprint('cv_render_api', __name__, url_prefix='/api/cv')


# ============================================================
# FILTRE format_date_full (comme dans ton backend web)
# ============================================================
_MOIS_FR = [
    '', 'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
    'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'
]


def format_date_full(value):
    """
    Filtre Jinja : '1990-03-15' ou '15/03/1990' → '15 mars 1990'.
    Utilisé par les templates web ET Flutter.
    """
    if not value:
        return ''

    value = str(value).strip()

    # Format ISO : 1990-03-15
    if '-' in value and len(value.split('-')) == 3:
        try:
            date_obj = datetime.strptime(value, '%Y-%m-%d')
            return f"{date_obj.day} {_MOIS_FR[date_obj.month]} {date_obj.year}"
        except Exception:
            pass

    # Format FR : 15/03/1990
    if '/' in value and len(value.split('/')) == 3:
        try:
            parts = value.split('/')
            j = int(parts[0])
            m = int(parts[1])
            a = int(parts[2])
            return f"{j} {_MOIS_FR[m]} {a}"
        except Exception:
            pass

    # Fallback : renvoie tel quel
    return value


# ============================================================
# LISTE DES MODÈLES
# ============================================================
@cv_render_bp.route('/modeles', methods=['GET'], strict_slashes=False)
def api_cv_modeles():
    modeles = [
        {'id': 'modele1', 'nom': 'Classique', 'premium': False},
        {'id': 'modele2', 'nom': 'Moderne', 'premium': False},
        {'id': 'modele3', 'nom': 'Créatif', 'premium': False},
        {'id': 'modele4', 'nom': 'Minimal', 'premium': False},
        {'id': 'modele5', 'nom': 'Élégant', 'premium': False},
        {'id': 'modele6', 'nom': 'Compact', 'premium': False},
        {'id': 'modele7', 'nom': 'Académique', 'premium': False},
        {'id': 'modele8', 'nom': 'Technique', 'premium': False},
        {'id': 'modele9', 'nom': 'Audacieux', 'premium': False},
        {'id': 'modele10', 'nom': 'Corporate', 'premium': False},
        {'id': 'modele11', 'nom': 'Executive', 'premium': True},
        {'id': 'modele12', 'nom': 'Luxe', 'premium': True},
        {'id': 'modele13', 'nom': 'Signature', 'premium': True},
    ]
    return jsonify({'success': True, 'modeles': modeles})


# ============================================================
# APERÇU D'UN CV
# ============================================================
@cv_render_bp.route('/apercu', methods=['POST'], strict_slashes=False)
def api_cv_apercu():
    payload = request.get_json() or {}

    modele = (payload.get('modele') or 'modele1').strip()
    donnees = payload.get('donnees') or {}
    couleur = payload.get('couleur') or donnees.get('couleur') or '#f39c12'

    # Sécurité
    if not re.match(r'^modele\d{1,2}$', modele):
        modele = 'modele1'

    # ---------- NORMALISATION ----------
    def norm_experiences(items):
        if not items:
            return []
        resultat = []
        for item in items:
            if isinstance(item, dict):
                resultat.append({
                    'poste': item.get('poste', ''),
                    'entreprise': item.get('entreprise', ''),
                    'lieu': item.get('lieu', ''),
                    'date_debut': item.get('date_debut', ''),
                    'date_fin': item.get('date_fin', ''),
                    'description': item.get('description', ''),
                })
            elif isinstance(item, str) and item.strip():
                resultat.append({
                    'poste': item.strip(),
                    'entreprise': '',
                    'lieu': '',
                    'date_debut': '',
                    'date_fin': '',
                    'description': '',
                })
        return resultat

    def norm_formations(items):
        if not items:
            return []
        resultat = []
        for item in items:
            if isinstance(item, dict):
                resultat.append({
                    'diplome': item.get('diplome', ''),
                    'etablissement': item.get('etablissement', ''),
                    'lieu': item.get('lieu', ''),
                    'date_debut': item.get('date_debut', ''),
                    'date_fin': item.get('date_fin', ''),
                    'description': item.get('description', ''),
                })
            elif isinstance(item, str) and item.strip():
                resultat.append({
                    'diplome': item.strip(),
                    'etablissement': '',
                    'lieu': '',
                    'date_debut': '',
                    'date_fin': '',
                    'description': '',
                })
        return resultat

    def norm_langues(items):
        if not items:
            return []
        resultat = []
        for item in items:
            if isinstance(item, dict):
                resultat.append({
                    'langue': item.get('langue', ''),
                    'niveau': item.get('niveau', ''),
                })
            elif isinstance(item, str) and item.strip():
                s = item.strip()
                langue, niveau = s, ''
                if '(' in s and s.endswith(')'):
                    langue = s[:s.index('(')].strip()
                    niveau = s[s.index('(') + 1:-1].strip()
                elif ' - ' in s:
                    partie = s.split(' - ', 1)
                    langue, niveau = partie[0].strip(), partie[1].strip()
                resultat.append({'langue': langue, 'niveau': niveau})
        return resultat

    def norm_comp_list(items):
        if not items:
            return []
        return [str(i).strip() for i in items if str(i).strip()]

    # ---------- OBJET DATA ----------
    data_obj = {
        'couleur': couleur,
        'police': donnees.get('police') or "'Segoe UI', Arial, sans-serif",
        'prenom': donnees.get('prenom', ''),
        'nom': donnees.get('nom', ''),
        'titre': donnees.get('titre', ''),
        'email': donnees.get('email', ''),
        'telephone': donnees.get('telephone', ''),
        'adresse': donnees.get('adresse', ''),
        'code_postal': donnees.get('code_postal', ''),
        'ville': donnees.get('ville', ''),
        'pays': donnees.get('pays', ''),
        'date_naissance': donnees.get('date_naissance', ''),   # ⬅️ brut, filtre s'occupe
        'photo': donnees.get('photo', ''),
        'profil': donnees.get('profil', ''),
        'experiences': norm_experiences(donnees.get('experiences')),
        'formations': norm_formations(donnees.get('formations')),
        'competences': norm_comp_list(donnees.get('competences')),
        'langues': norm_langues(donnees.get('langues')),
        'certifications': norm_comp_list(donnees.get('certifications')),
        'interets': norm_comp_list(donnees.get('interets')),
    }

    # ---------- RENDU ----------
    contexte = {'data': data_obj}

    # ⬇️ ENREGISTRE LE FILTRE À LA VOLÉE (au cas où il n'existe pas)
    _app = request.environ.get('werkzeug.request')  # placeholder
    from flask import current_app
    current_app.jinja_env.filters['format_date_full'] = format_date_full

    chemins_possibles = [
        f'cv/{modele}.html',
        f'modeles/{modele}.html',
        f'modeles_cv/{modele}.html',
        f'{modele}.html',
    ]

    html_rendu = None
    derniere_erreur = None

    for chemin in chemins_possibles:
        try:
            html_rendu = render_template(chemin, **contexte)
            break
        except Exception as e:
            derniere_erreur = e
            continue

    if html_rendu is None:
        html_rendu = _html_fallback(modele, data_obj)
        print(f"⚠️ Template {modele} introuvable : {derniere_erreur}")

    return jsonify({
        'success': True,
        'html': html_rendu,
        'modele': modele,
    })


# ============================================================
# FALLBACK HTML
# ============================================================
def _html_fallback(modele, data):
    couleur = data.get('couleur', '#6C5CE7')
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; padding: 30px; color: #2c3e50; }}
  h1 {{ color: {couleur}; border-bottom: 3px solid {couleur}; padding-bottom: 10px; }}
  h2 {{ color: {couleur}; font-size: 15px; margin-top: 20px; }}
  .contact {{ font-size: 12px; color: #64748b; }}
</style></head>
<body>
  <h1>{data.get('prenom','')} {data.get('nom','')}</h1>
  <div class="contact">
    {data.get('titre','')}<br/>
    {data.get('email','')}<br/>
    {data.get('telephone','')}
  </div>
  {f"<h2>Profil</h2><p>{data.get('profil','')}</p>" if data.get('profil') else ''}
  <p style="margin-top:30px;color:#94a3b8;font-size:12px;">Modèle {modele} — aperçu simplifié</p>
</body></html>"""