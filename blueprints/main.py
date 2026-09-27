"""
Routes principales : accueil, API CV/Lettres, miniatures, stats.
"""
import uuid
from flask import Blueprint, render_template, request, jsonify, session
from flask_login import current_user

from data import MODELES, LETTRES_MODELES, SAMPLE_CV, SAMPLE_LETTRE
from stats_utils import (lire_stats, incrementer_visite,
                         incrementer_telechargement_cv,
                         incrementer_telechargement_lettre,
                         enregistrer_modele,
                         marquer_visiteur_en_ligne)

main_bp = Blueprint('main', __name__)


# ==================== ACCUEIL ====================
@main_bp.route('/', strict_slashes=False)
def index():
    # Marquer le visiteur en ligne
    if 'visiteur_id' not in session:
        session['visiteur_id'] = str(uuid.uuid4())
    marquer_visiteur_en_ligne(session['visiteur_id'])

    # Compter une visite par session
    if not session.get('deja_visite'):
        incrementer_visite()
        session['deja_visite'] = True

    stats = lire_stats()
    return render_template('index.html',
                           modeles=MODELES,
                           lettres_modeles=LETTRES_MODELES,
                           stats=stats,
                           premium=(current_user.is_authenticated and current_user.premium))


# ==================== API CV ====================
@main_bp.route('/api/modeles', strict_slashes=False)
def api_modeles():
    return jsonify(MODELES)


@main_bp.route('/api/apercu', methods=['POST'], strict_slashes=False)
def apercu():
    data = request.json or {}
    modele_id = data.get('modele', 'modele1')
    modele = next((m for m in MODELES if m['id'] == modele_id), MODELES[0])

    data['couleur'] = data.get('couleur_perso') or modele['couleur']
    data['police'] = data.get('police_perso') or "'Segoe UI', Arial, sans-serif"

    if current_user.is_authenticated:
        data['premium'] = current_user.premium
    else:
        data['premium'] = False

    # Enregistrer l'utilisation du modèle (une fois par session)
    cle_modele = f'modele_utilise_{modele_id}'
    if not session.get(cle_modele):
        enregistrer_modele(modele_id)
        session[cle_modele] = True

    html_cv = render_template(f'cv/{modele_id}.html', data=data)
    return jsonify({'html': html_cv})


# ==================== API LETTRES ====================
@main_bp.route('/api/lettres/modeles', strict_slashes=False)
def api_lettres_modeles():
    return jsonify(LETTRES_MODELES)


@main_bp.route('/api/lettre/apercu', methods=['POST'], strict_slashes=False)
def api_lettre_apercu():
    data = request.json or {}
    modele_id = data.get('modele', 'modele1')
    modele = next((m for m in LETTRES_MODELES if m['id'] == modele_id), LETTRES_MODELES[0])

    data['couleur'] = modele['couleur']
    data['police'] = "'Segoe UI', Arial, sans-serif"

    html = render_template(f'lettre/{modele_id}.html', data=data)
    return jsonify({'html': html})


# ==================== MINIATURES ====================
@main_bp.route('/miniature/cv/<modele_id>', strict_slashes=False)
def miniature_cv(modele_id):
    modele = next((m for m in MODELES if m['id'] == modele_id), None)
    if not modele:
        return "Modèle introuvable", 404

    data = dict(SAMPLE_CV)
    data['couleur'] = modele['couleur']
    data['police'] = "'Segoe UI', Arial, sans-serif"
    data['modele'] = modele_id
    data['premium'] = False
    return render_template(f'cv/{modele_id}.html', data=data)


@main_bp.route('/miniature/lettre/<modele_id>', strict_slashes=False)
def miniature_lettre(modele_id):
    modele = next((m for m in LETTRES_MODELES if m['id'] == modele_id), None)
    if not modele:
        return "Modèle introuvable", 404

    data = dict(SAMPLE_LETTRE)
    data['couleur'] = modele['couleur']
    data['police'] = "'Segoe UI', Arial, sans-serif"
    data['modele'] = modele_id
    return render_template(f'lettre/{modele_id}.html', data=data)


# ==================== API STATS ====================
@main_bp.route('/api/stats', strict_slashes=False)
def api_stats():
    return jsonify(lire_stats())


@main_bp.route('/api/stats/telechargement', methods=['POST'], strict_slashes=False)
def api_stats_telechargement():
    incrementer_telechargement_cv()
    return jsonify(lire_stats())


@main_bp.route('/api/stats/telechargement-lettre', methods=['POST'], strict_slashes=False)
def api_stats_telechargement_lettre():
    incrementer_telechargement_lettre()
    return jsonify(lire_stats())