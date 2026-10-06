# ============================================================
# API RESET MOT DE PASSE POUR FLUTTER
# Utilise un code alphanumérique à 6 caractères
# ============================================================
import time
import secrets
from flask import Blueprint, request, jsonify
from flask_mail import Message

from extensions import db, mail
from models import User

password_reset_api_bp = Blueprint(
    'password_reset_api',
    __name__,
    url_prefix='/api/password-reset'
)

# Stockage temporaire des codes (email → {code, expires})
# ⚠️ En mémoire : perdu si Flask redémarre.
PENDING_RESETS = {}

DUREE_CODE = 30 * 60  # 30 minutes

# Alphabet sans caractères ambigus (0/O, 1/I/l)
ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'


# ============================================================
# ÉTAPE 1 : DEMANDER UN RESET → envoie un code par email
# ============================================================
@password_reset_api_bp.route('/request', methods=['POST'], strict_slashes=False)
def api_request_reset():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()

    if not email:
        return jsonify({
            'success': False,
            'error': "L'email est obligatoire."
        }), 400

    user = User.query.filter_by(email=email).first()

    # ⚠️ On répond TOUJOURS pareil (sécurité : ne pas révéler si l'email existe)
    if user:
        # Génère un code alphanumérique à 6 caractères
        code = ''.join(secrets.choice(ALPHABET) for _ in range(6))
        PENDING_RESETS[email] = {
            'code': code,
            'expires': time.time() + DUREE_CODE
        }

        try:
            msg = Message(
                subject='🔐 Réinitialisation de votre mot de passe CVPro',
                recipients=[user.email],
                html=f"""
                <!DOCTYPE html>
                <html lang="fr">
                <head><meta charset="utf-8"></head>
                <body style="font-family:Arial,sans-serif;background:#f4f6f9;padding:30px;margin:0;">
                  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:16px;
                              overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.08);">

                    <div style="background:linear-gradient(135deg,#7c3aed,#f39c12);
                                padding:32px 40px;text-align:center;">
                      <h1 style="color:#fff;margin:0;font-size:1.6rem;">CVPro</h1>
                    </div>

                    <div style="padding:36px 40px;">
                      <h2 style="color:#2c3e50;margin:0 0 16px;">Bonjour {user.nom},</h2>

                      <p style="color:#475569;line-height:1.7;margin:0 0 20px;">
                        Vous avez demandé à réinitialiser votre mot de passe CVPro.
                        Voici votre code de vérification (valable <b>30 minutes</b>) :
                      </p>

                      <div style="text-align:center;margin:28px 0;">
                        <div style="display:inline-block;padding:18px 30px;
                                    background:#f7f8fc;border-radius:12px;
                                    font-size:30px;font-weight:800;
                                    letter-spacing:8px;color:#7c3aed;
                                    font-family:'Courier New',monospace;
                                    word-break:keep-all;">
                          {code}
                        </div>
                      </div>

                      <p style="color:#64748b;font-size:.85rem;line-height:1.6;">
                        Saisissez ce code dans l'application CVPro pour choisir un nouveau mot de passe.
                      </p>

                      <hr style="border:none;border-top:1px solid #e8ecf0;margin:24px 0;">

                      <p style="color:#94a3b8;font-size:.8rem;line-height:1.6;">
                        Vous n'avez pas demandé ce changement ? Ignorez simplement cet email.
                      </p>
                    </div>
                  </div>
                </body>
                </html>
                """
            )
            mail.send(msg)
            print(f"✅ Code reset envoyé à {user.email} : {code}")

        except Exception as e:
            print(f"❌ Erreur envoi mail : {e}")
            return jsonify({
                'success': False,
                'error': "Erreur d'envoi de l'email. Réessayez."
            }), 500

    return jsonify({
        'success': True,
        'message': 'Si cet email existe, un code vous a été envoyé.'
    })


# ============================================================
# ÉTAPE 2 : VÉRIFIER LE CODE + CHANGER LE MOT DE PASSE
# ============================================================
@password_reset_api_bp.route('/confirm', methods=['POST'], strict_slashes=False)
def api_confirm_reset():
    data = request.get_json() or {}

    email = (data.get('email') or '').strip().lower()
    code = (data.get('code') or '').strip().upper()   # ⬅️ majuscules forcées
    password = data.get('password') or ''
    password2 = data.get('password2') or ''

    # Validations
    if not email or not code:
        return jsonify({
            'success': False,
            'error': 'Email et code obligatoires.'
        }), 400

    if len(code) != 6:
        return jsonify({
            'success': False,
            'error': 'Le code doit faire 6 caractères.'
        }), 400

    if len(password) < 6:
        return jsonify({
            'success': False,
            'error': 'Mot de passe : 6 caractères minimum.'
        }), 400

    if password != password2:
        return jsonify({
            'success': False,
            'error': 'Les mots de passe ne correspondent pas.'
        }), 400

    # Vérification du code
    pending = PENDING_RESETS.get(email)

    if not pending:
        return jsonify({
            'success': False,
            'error': 'Aucune demande en cours. Recommencez.'
        }), 400

    if time.time() > pending['expires']:
        del PENDING_RESETS[email]
        return jsonify({
            'success': False,
            'error': 'Code expiré. Recommencez.'
        }), 400

    if pending['code'] != code:
        return jsonify({
            'success': False,
            'error': 'Code incorrect.'
        }), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({
            'success': False,
            'error': 'Utilisateur introuvable.'
        }), 404

    try:
        user.set_password(password)
        db.session.commit()

        # Code utilisé → on le supprime
        del PENDING_RESETS[email]

        return jsonify({
            'success': True,
            'message': 'Mot de passe modifié !'
        })
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur reset password : {e}")
        return jsonify({
            'success': False,
            'error': 'Erreur serveur.'
        }), 500