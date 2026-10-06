"""
Blueprint pour les offres d'emploi.
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from job_api import (rechercher_offres, extraire_mots_cles_cv,
                     formater_offre)
from models import CV

from adzuna_api import rechercher_offres_adzuna

from ai_helper_groq import generer_lettre_motivation

from flask import (Blueprint, render_template, request, jsonify,
                   flash, redirect, url_for)
emploi_bp = Blueprint('emploi', __name__)


@emploi_bp.route('/emplois', strict_slashes=False)
@login_required
def page_emplois():
    """Page des offres d'emploi."""
    return render_template('emplois.html')


@emploi_bp.route('/api/emplois/recherche', strict_slashes=False)
@login_required
def api_recherche():
    """API de recherche d'offres."""
    mots_cles = request.args.get('q', '').strip()
    departement = request.args.get('dep', '').strip()
    contrat = request.args.get('contrat', '').strip()
    cv_id = request.args.get('cv_id', type=int)

    # Si un CV est fourni, utiliser ses mots-clés
    if cv_id:
        cv = CV.query.filter_by(id=cv_id, user_id=current_user.id).first()
        if cv:
            import json
            donnees = json.loads(cv.donnees_json)
            mots_cles = extraire_mots_cles_cv(donnees)

    resultat = rechercher_offres(
        mots_cles=mots_cles,
        departement=departement,
        type_contrat=contrat,
        nb_resultats=20
    )

    if not resultat.get('success'):
        return jsonify({
            'success': False,
            'error': resultat.get('erreur', 'Erreur inconnue'),
            'offres': [],
        })

    offres = [formater_offre(o) for o in resultat.get('offres', [])]

    return jsonify({
        'success': True,
        'offres': offres,
        'total': len(offres),
        'mots_cles_utilises': mots_cles,
    })


@emploi_bp.route('/api/emplois/mes-cv', strict_slashes=False)
@login_required
def api_mes_cv():
    """Liste les CV de l'utilisateur pour le sélecteur."""
    cvs = CV.query.filter_by(user_id=current_user.id).order_by(
        CV.updated_at.desc()
    ).all()

    return jsonify({
        'success': True,
        'cvs': [{'id': cv.id, 'titre': cv.titre} for cv in cvs],
    })
    
    
    
    
    # ==================== RECHERCHE ADZUNA ====================
@emploi_bp.route('/api/emplois/recherche-adzuna', strict_slashes=False)
@login_required
def api_recherche_adzuna():
    """Recherche d'offres via Adzuna."""
    mots_cles = request.args.get('q', '').strip()
    ville = request.args.get('ville', '').strip()
    page = request.args.get('page', 1, type=int)

    resultat = rechercher_offres_adzuna(
        mots_cles=mots_cles,
        ville=ville,
        nb_resultats=20,
        page=page,
        pays='fr'
    )

    if not resultat.get('success'):
        return jsonify({
            'success': False,
            'error': resultat.get('erreur', 'Erreur inconnue'),
            'offres': [],
        })

    return jsonify({
        'success': True,
        'offres': resultat.get('offres', []),
        'total': resultat.get('total', 0),
        'page': page,
        'source': 'Adzuna',
    })
    
    
    # ==================== APERÇU POUR LE BANDEAU ====================
@emploi_bp.route('/api/emplois/apercu', strict_slashes=False)
def api_emplois_apercu():
    """
    Renvoie un mélange d'offres pour le bandeau de la page d'accueil.
    Pas besoin d'être connecté.
    """
    offres_finales = []

    # ---- France Travail (5 offres) ----
    try:
        resultat_ft = rechercher_offres(
            mots_cles='',
            nb_resultats=5
        )
        if resultat_ft.get('success'):
            for o in resultat_ft.get('offres', [])[:5]:
                offres_finales.append(formater_offre(o))
    except Exception as e:
        print(f"⚠️ Erreur France Travail aperçu : {e}")

    # ---- Adzuna (5 offres) ----
    try:
        resultat_adz = rechercher_offres_adzuna(
            mots_cles='',
            ville='',
            nb_resultats=5,
            page=1,
            pays='fr'
        )
        if resultat_adz.get('success'):
            for o in resultat_adz.get('offres', [])[:5]:
                offres_finales.append(o)
    except Exception as e:
        print(f"⚠️ Erreur Adzuna aperçu : {e}")

    return jsonify({
        'success': True,
        'offres': offres_finales,
        'total': len(offres_finales),
    })
    
# ==================== PAGE DÉTAIL D'UNE OFFRE ====================
@emploi_bp.route('/emploi/<offre_id>', strict_slashes=False)
@login_required
def page_detail_offre(offre_id):
    """Affiche le détail d'une offre (via Adzuna)."""
    # Récupérer les détails depuis Adzuna
    resultat = rechercher_offres_adzuna(
        mots_cles='',
        nb_resultats=50,
        page=1,
    )

    offre = None
    if resultat.get('success'):
        for o in resultat.get('offres', []):
            if str(o.get('id')) == str(offre_id):
                offre = o
                break

    # Si pas trouvée via recherche, on cherche directement par ID
    if not offre:
        import requests
        from adzuna_api import APP_ID, APP_KEY
        try:
            url = f"https://api.adzuna.com/v1/api/jobs/fr/search/1"
            params = {
                'app_id': APP_ID,
                'app_key': APP_KEY,
                'results_per_page': 50,
            }
            # Note : Adzuna ne permet pas la recherche par ID directement,
            # donc on retourne une erreur si non trouvée
        except Exception:
            pass

    if not offre:
        flash('Offre introuvable ou expirée.', 'error')
        return redirect(url_for('emploi.page_emplois'))

    return render_template('emploi_detail.html', offre=offre)   
  