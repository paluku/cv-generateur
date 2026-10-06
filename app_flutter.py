# ============================================================
# LANCEUR FLUTTER — NE TOUCHE PAS app.py
# ============================================================
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask_cors import CORS   # ⬅️ AJOUT

from app import create_app
from extensions import login_manager
from models import User
from blueprints.cv_render_api import cv_render_bp
from blueprints.password_reset_api import password_reset_api_bp



# 1) On crée l'app
app = create_app()

# 2) CORS pour Flutter Web
CORS(app, supports_credentials=True, origins="*")   # ⬅️ AJOUT


# 3) Support des tokens Bearer pour Flutter
@login_manager.request_loader
def load_user_from_request(request):
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None
    token = auth[7:]
    serializer = URLSafeTimedSerializer(
        app.config['SECRET_KEY'],
        salt='auth-api'
    )
    try:
        data = serializer.loads(token, max_age=60 * 60 * 24 * 30)
    except (BadSignature, SignatureExpired):
        return None
    return User.query.get(data.get('user_id'))


# 4) Routes API auth
from blueprints.auth_api import auth_api_bp
app.register_blueprint(auth_api_bp)
app.register_blueprint(cv_render_bp)
app.register_blueprint(password_reset_api_bp)


# 5) Lancement
if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🚀 CVPro — Serveur Flask (mode Flutter)")
    print("=" * 60)
    print("📱 API Flutter : http://127.0.0.1:5000/api")
    print("📄 Site web    : http://127.0.0.1:5000")
    print("=" * 60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)