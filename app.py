"""
CVPro — Générateur de CV & Lettres avec Premium
Application Flask modulaire avec Factory + Blueprints.
"""
import os
from datetime import datetime

from flask import (Flask, jsonify, request, redirect, url_for, g,
                   render_template)
from flask_login import current_user, login_required
from itsdangerous import URLSafeTimedSerializer

from config import Config
from extensions import db, login_manager, mail
from models import User, CV
from filters import register_filters
from blueprints.admin_db import admin_db_bp

# ================================================================
# FACTORY
# ================================================================
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ==================== EXTENSIONS ====================
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    # Configuration Flask-Login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Connectez-vous pour continuer."
    login_manager.login_message_category = 'warning'

    # Serializer pour les tokens de reset password (expire en 1h)
    app.password_reset_serializer = URLSafeTimedSerializer(
        app.config['SECRET_KEY'],
        salt='password-reset-salt'
    )

    # ==================== BASE DE DONNÉES ====================
    with app.app_context():
        db.create_all()
        print("✅ Base SQLite prête (cvpro.db)")

    # ==================== FILTRES JINJA ====================
    register_filters(app)

    # ==================== UTILISATEUR COURANT ====================
    @app.before_request
    def charger_utilisateur():
        g.user = current_user if current_user.is_authenticated else None

    @app.context_processor
    def injecter_user():
        return dict(current_user=g.get('user'))

    # ==================== BLUEPRINTS ====================
    from blueprints.main import main_bp
    from blueprints.auth import auth_bp
    from blueprints.premium import premium_bp
    from blueprints.admin import admin_bp
    from blueprints.password_reset import password_reset_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(premium_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(password_reset_bp)
    app.register_blueprint(admin_db_bp)

    # ================================================================
    # ⭐ ROUTE /mes-cv — PAGE HTML
    # ================================================================
    @app.route('/mes-cv', methods=['GET'], strict_slashes=False)
    @login_required
    def page_mes_cv():
        """Affiche la page HTML 'Mes CV sauvegardés'."""
        return render_template('mes_cv.html')

    # ================================================================
    # API : LISTER LES CV DE L'UTILISATEUR
    # ================================================================
    @app.route('/api/mes-cv', methods=['GET'], strict_slashes=False)
    @login_required
    def api_mes_cv_liste():
        MAX_CV_GRATUIT = 3
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

    # ================================================================
    # API : DÉTAIL D'UN CV
    # ================================================================
    @app.route('/api/mes-cv/<int:cv_id>', methods=['GET'], strict_slashes=False)
    @login_required
    def api_mes_cv_detail(cv_id):
        cv = CV.query.filter_by(id=cv_id, user_id=current_user.id).first()
        if not cv:
            return jsonify({'success': False, 'error': 'CV introuvable'}), 404
        return jsonify({'success': True, 'cv': cv.to_dict(complet=True)})

    # ================================================================
    # API : CRÉER / METTRE À JOUR UN CV
    # ================================================================
    @app.route('/api/mes-cv', methods=['POST'], strict_slashes=False)
    @login_required
    def api_mes_cv_sauvegarder():
        import json
        MAX_CV_GRATUIT = 3

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
            # ----- MODIFICATION -----
            if cv_id:
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

            # ----- CRÉATION -----
            total = CV.query.filter_by(user_id=current_user.id).count()
            if not current_user.premium and total >= MAX_CV_GRATUIT:
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
                'total': total + 1,
            }), 201

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur sauvegarde CV : {e}")
            return jsonify({'success': False, 'error': 'Erreur serveur'}), 500

    # ================================================================
    # API : SUPPRIMER UN CV
    # ================================================================
    @app.route('/api/mes-cv/<int:cv_id>', methods=['DELETE'], strict_slashes=False)
    @login_required
    def api_mes_cv_supprimer(cv_id):
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

    # ================================================================
    # API : DUPLIQUER UN CV (PREMIUM)
    # ================================================================
    @app.route('/api/mes-cv/<int:cv_id>/dupliquer', methods=['POST'], strict_slashes=False)
    @login_required
    def api_mes_cv_dupliquer(cv_id):
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

    # ================================================================
    # API : STATS UTILISATEUR
    # ================================================================
    @app.route('/api/mes-cv/stats', methods=['GET'], strict_slashes=False)
    @login_required
    def api_mes_cv_stats():
        MAX_CV_GRATUIT = 3
        total = CV.query.filter_by(user_id=current_user.id).count()
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

    # ==================== GESTION D'ERREURS ====================
    @app.errorhandler(404)
    def e404(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Ressource introuvable', 'code': 404}), 404
        return redirect(url_for('main.index'))

    @app.errorhandler(405)
    def e405(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Méthode non autorisée', 'code': 405}), 405
        return redirect(url_for('main.index'))

    @app.errorhandler(500)
    def e500(e):
        db.session.rollback()
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Erreur interne', 'code': 500}), 500
        return redirect(url_for('main.index'))

    return app


# ================================================================
# LANCEMENT
# ================================================================
app = create_app()

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🚀 CVPro — Serveur Flask")
    print("=" * 60)
    print("📄 Accueil          : http://127.0.0.1:5000")
    print("👤 Inscription      : http://127.0.0.1:5000/register")
    print("🔐 Connexion        : http://127.0.0.1:5000/login")
    print("🔑 Mot de passe oublié : http://127.0.0.1:5000/mot-de-passe-oublie")
    print("👤 Mon compte       : http://127.0.0.1:5000/mon-compte")
    print("📂 Mes CV           : http://127.0.0.1:5000/mes-cv")
    print("📊 Admin            : http://127.0.0.1:5000/admin")
    print("=" * 60 + "\n")
    app.run(debug=True)