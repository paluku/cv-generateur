"""
Module "Mes CV" — Sauvegarde professionnelle des CV.
"""
import json
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from extensions import db
from models import CV

mes_cv_bp = Blueprint('mes_cv', __name__, url_prefix='/api/mes-cv')

MAX_CV_GRATUIT = 3


# ==================== HELPERS ====================
def _compter(user_id):
    return CV.query.filter_by(user_id=user_id).count()


def _limite_atteinte(user):
    if user.premium:
        return False
    return _compter(user.id) >= MAX_CV_GRATUIT


# ==================== LISTER ====================
@mes_cv_bp.route('', methods=['GET'], strict_slashes=False)
@login_required
def liste():
    recherche = (request.args.get('q') or '').strip().lower()
    tri = request.args.get('tri', 'recent')

    query = CV.query.filter_by(user_id=current_user.id)

    if recherche:
        query = query.filter(CV.titre.ilike(f'%{recherche}%'))

    if tri == 'ancien':
        query = query.order_by(CV.updated_at.asc())
    elif tri == 'titre':
        query = query.order_by(CV.titre.asc())
    else:
        query = query.order_by(CV.updated_at.desc())

    cvs = query.all()
    total = len(cvs)

    return jsonify({
        'success': True,
        'cvs': [cv.to_dict() for cv in cvs],
        'total': total,
        'max': None if current_user.premium else MAX_CV_GRATUIT,
        'premium': current_user.premium,
        'peut_creer': (current_user.premium or total < MAX_CV_GRATUIT),
    })


# ==================== DÉTAIL ====================
@mes_cv_bp.route('/<int:cv_id>', methods=['GET'], strict_slashes=False)
@login_required
def detail(cv_id):
    cv = CV.query.filter_by(id=cv_id, user_id=current_user.id).first()
    if not cv:
        return jsonify({'success': False, 'error': 'CV introuvable'}), 404
    return jsonify({'success': True, 'cv': cv.to_dict(complet=True)})


# ==================== CRÉER / METTRE À JOUR ====================
@mes_cv_bp.route('', methods=['POST'], strict_slashes=False)
@login_required
def sauvegarder():
    data = request.json or {}
    cv_id = data.get('cv_id')
    titre = (data.get('titre') or '').strip()
    modele = data.get('modele', 'modele1')
    donnees = data.get('donnees') or {}
    photo = data.get('photo')
    couleur = data.get('couleur', '#f39c12')

    # Validation
    if not titre:
        return jsonify({'success': False, 'error': 'Le titre est obligatoire'}), 400
    if len(titre) > 150:
        return jsonify({'success': False, 'error': 'Titre trop long (150 max)'}), 400
    if not donnees:
        return jsonify({'success': False, 'error': 'Données manquantes'}), 400

    try:
        if cv_id:
            # Modification d'un CV existant
            cv = CV.query.filter_by(id=cv_id, user_id=current_user.id).first()
            if not cv:
                return jsonify({'success': False, 'error': 'CV introuvable'}), 404

            cv.titre = titre
            cv.modele = modele
            cv.donnees_json = json.dumps(donnees, ensure_ascii=False)
            cv.photo = photo
            cv.couleur = couleur
            db.session.commit()

            return jsonify({
                'success': True,
                'message': 'CV mis à jour !',
                'cv_id': cv.id,
                'action': 'updated',
            })

        # Création d'un nouveau
        if _limite_atteinte(current_user):
            return jsonify({
                'success': False,
                'error': f'Limite de {MAX_CV_GRATUIT} CV atteinte',
                'limite_atteinte': True,
                'max': MAX_CV_GRATUIT,
            }), 403

        cv = CV(
            user_id=current_user.id,
            titre=titre,
            modele=modele,
            donnees_json=json.dumps(donnees, ensure_ascii=False),
            photo=photo,
            couleur=couleur,
        )
        db.session.add(cv)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'CV sauvegardé !',
            'cv_id': cv.id,
            'action': 'created',
            'total': _compter(current_user.id),
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur sauvegarde CV : {e}")
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500


# ==================== SUPPRIMER ====================
@mes_cv_bp.route('/<int:cv_id>', methods=['DELETE'], strict_slashes=False)
@login_required
def supprimer(cv_id):
    cv = CV.query.filter_by(id=cv_id, user_id=current_user.id).first()
    if not cv:
        return jsonify({'success': False, 'error': 'CV introuvable'}), 404

    try:
        db.session.delete(cv)
        db.session.commit()
        return jsonify({'success': True, 'message': 'CV supprimé'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== DUPLIQUER (Premium) ====================
@mes_cv_bp.route('/<int:cv_id>/dupliquer', methods=['POST'], strict_slashes=False)
@login_required
def dupliquer(cv_id):
    if not current_user.premium:
        return jsonify({
            'success': False,
            'error': 'Fonctionnalité Premium',
            'need_premium': True,
        }), 403

    cv = CV.query.filter_by(id=cv_id, user_id=current_user.id).first()
    if not cv:
        return jsonify({'success': False, 'error': 'CV introuvable'}), 404

    try:
        nouveau = CV(
            user_id=current_user.id,
            titre=f"{cv.titre} (copie)",
            modele=cv.modele,
            donnees_json=cv.donnees_json,
            photo=cv.photo,
            couleur=cv.couleur,
        )
        db.session.add(nouveau)
        db.session.commit()
        return jsonify({'success': True, 'cv_id': nouveau.id, 'message': 'CV dupliqué'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== STATS UTILISATEUR ====================
@mes_cv_bp.route('/stats', methods=['GET'], strict_slashes=False)
@login_required
def stats():
    total = _compter(current_user.id)
    dernier = (CV.query
               .filter_by(user_id=current_user.id)
               .order_by(CV.updated_at.desc())
               .first())

    return jsonify({
        'success': True,
        'total': total,
        'max': None if current_user.premium else MAX_CV_GRATUIT,
        'premium': current_user.premium,
        'dernier_ajout': dernier.updated_at.strftime('%d/%m/%Y') if dernier else None,
    })