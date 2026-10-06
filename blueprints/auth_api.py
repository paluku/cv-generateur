# ============================================================
# API AUTHENTIFICATION POUR FLUTTER
# ============================================================
from flask import Blueprint, request, jsonify, current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from extensions import db
from models import User

auth_api_bp = Blueprint('auth_api', __name__, url_prefix='/api')


# ---------- HELPERS TOKEN ----------
def _serializer():
    return URLSafeTimedSerializer(
        current_app.config['SECRET_KEY'],
        salt='auth-api'
    )


def generer_token(user_id):
    return _serializer().dumps({'user_id': user_id})


def utilisateur_du_token():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None
    token = auth[7:]
    try:
        data = _serializer().loads(token, max_age=60 * 60 * 24 * 30)
    except (BadSignature, SignatureExpired):
        return None
    return User.query.get(data.get('user_id'))


# ---------- INSCRIPTION ----------
@auth_api_bp.route('/register', methods=['POST'], strict_slashes=False)
def api_register():
    data = request.get_json() or {}

    nom = (data.get('nom') or '').strip()
    email = (data.get('email') or '').strip().lower()
    telephone = (data.get('telephone') or '').strip()
    password = data.get('password') or ''
    password2 = data.get('password2') or ''

    erreurs = []
    if not nom: erreurs.append('Le nom est obligatoire.')
    if not email: erreurs.append("L'email est obligatoire.")
    if len(password) < 6: erreurs.append('Mot de passe : 6 caractères minimum.')
    if password != password2: erreurs.append('Les mots de passe ne correspondent pas.')
    if User.query.filter_by(email=email).first():
        erreurs.append('Cet email est déjà utilisé.')

    if erreurs:
        return jsonify({'success': False, 'errors': erreurs}), 400

    user = User(nom=nom, email=email, telephone=telephone)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Bienvenue {user.nom} !',
        'token': generer_token(user.id),
        'user': {
            'id': user.id,
            'nom': user.nom,
            'email': user.email,
            'telephone': getattr(user, 'telephone', None),
            'premium': getattr(user, 'premium', False),
        }
    }), 201


# ---------- CONNEXION ----------
@auth_api_bp.route('/login', methods=['POST'], strict_slashes=False)
def api_login():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({
            'success': False,
            'error': 'Email ou mot de passe incorrect.'
        }), 401

    return jsonify({
        'success': True,
        'message': f'Content de vous revoir, {user.nom} !',
        'token': generer_token(user.id),
        'user': {
            'id': user.id,
            'nom': user.nom,
            'email': user.email,
            'telephone': getattr(user, 'telephone', None),
            'premium': getattr(user, 'premium', False),
        }
    })


# ---------- PROFIL ----------
@auth_api_bp.route('/me', methods=['GET'], strict_slashes=False)
def api_me():
    user = utilisateur_du_token()
    if not user:
        return jsonify({'success': False, 'error': 'Non authentifié'}), 401

    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'nom': user.nom,
            'email': user.email,
            'telephone': getattr(user, 'telephone', None),
            'premium': getattr(user, 'premium', False),
        }
    })


# ---------- DÉCONNEXION ----------
@auth_api_bp.route('/logout', methods=['POST'], strict_slashes=False)
def api_logout():
    return jsonify({'success': True, 'message': 'Déconnecté'})