"""
Réinitialisation de mot de passe par email.
"""
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, current_app, jsonify)
from flask_mail import Message
from flask_login import current_user
from itsdangerous import BadSignature, SignatureExpired

from extensions import db, mail
from models import User


password_reset_bp = Blueprint('password_reset', __name__)

# Durée de validité du lien : 1 heure
DUREE_TOKEN = 3600


# ==================== PAGE "MOT DE PASSE OUBLIÉ" ====================
@password_reset_bp.route('/mot-de-passe-oublie', methods=['GET', 'POST'],
                          strict_slashes=False)
def forgot_password():
    """Page où l'utilisateur saisit son email."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()

        if not email:
            flash('Entrez votre adresse email.', 'error')
            return render_template('forgot_password.html')

        user = User.query.filter_by(email=email).first()

        # ⚠️ Toujours afficher le même message (sécurité : ne pas révéler
        # si un email existe ou non dans la base)
        if user:
            try:
                envoyer_email_reset(user)
                print(f"✅ Email de réinitialisation envoyé à {user.email}")
            except Exception as e:
                print(f"❌ Erreur envoi email : {e}")
                flash('Erreur lors de l\'envoi de l\'email. Réessayez plus tard.', 'error')
                return render_template('forgot_password.html')

        flash(
            'Si un compte existe avec cet email, un lien de réinitialisation '
            'vous a été envoyé. Vérifiez votre boîte de réception (et les spams).',
            'success'
        )
        return redirect(url_for('auth.login'))

    return render_template('forgot_password.html')


# ==================== ENVOI DE L'EMAIL ====================
def envoyer_email_reset(user):
    """Génère un token et envoie l'email de réinitialisation."""
    serializer = current_app.password_reset_serializer
    token = serializer.dumps({'user_id': user.id, 'email': user.email})

    lien = url_for('password_reset.reset_password',
                   token=token,
                   _external=True)

    # Contenu de l'email
    sujet = "🔐 Réinitialisation de votre mot de passe CVPro"

    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head><meta charset="utf-8"></head>
    <body style="font-family:Arial,sans-serif;background:#f4f6f9;padding:30px;margin:0;">
      <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:16px;
                  overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.08);">

        <!-- EN-TÊTE -->
        <div style="background:linear-gradient(135deg,#7c3aed,#f39c12);
                    padding:32px 40px;text-align:center;">
          <h1 style="color:#fff;margin:0;font-size:1.6rem;">CVPro</h1>
          <p style="color:rgba(255,255,255,.9);margin:8px 0 0;font-size:.9rem;">
            Générateur de CV professionnel
          </p>
        </div>

        <!-- CORPS -->
        <div style="padding:36px 40px;">
          <h2 style="color:#2c3e50;margin:0 0 16px;">Bonjour {user.nom},</h2>

          <p style="color:#475569;line-height:1.7;margin:0 0 20px;">
            Vous avez demandé à réinitialiser votre mot de passe CVPro.
            Cliquez sur le bouton ci-dessous pour en choisir un nouveau.
          </p>

          <div style="text-align:center;margin:28px 0;">
            <a href="{lien}"
               style="display:inline-block;padding:16px 36px;background:#f39c12;
                      color:#fff;text-decoration:none;border-radius:10px;
                      font-weight:700;font-size:1rem;">
              🔐 Réinitialiser mon mot de passe
            </a>
          </div>

          <p style="color:#64748b;font-size:.85rem;line-height:1.6;margin:20px 0 0;">
            ⏱ Ce lien est valable <b>1 heure</b>. Passé ce délai, vous devrez
            refaire une demande.
          </p>

          <hr style="border:none;border-top:1px solid #e8ecf0;margin:24px 0;">

          <p style="color:#94a3b8;font-size:.8rem;line-height:1.6;margin:0;">
            Si le bouton ne fonctionne pas, copiez-collez ce lien dans votre navigateur :<br>
            <a href="{lien}" style="color:#7c3aed;word-break:break-all;">{lien}</a>
          </p>
        </div>

        <!-- PIED -->
        <div style="background:#f9fbfc;padding:20px 40px;text-align:center;
                    border-top:1px solid #e8ecf0;">
          <p style="color:#94a3b8;font-size:.75rem;margin:0;">
            Vous n'avez pas demandé ce changement ?<br>
            Ignorez simplement cet email — votre mot de passe reste inchangé.
          </p>
        </div>
      </div>
    </body>
    </html>
    """

    texte = f"""Bonjour {user.nom},

Vous avez demandé à réinitialiser votre mot de passe CVPro.

Cliquez sur ce lien pour en choisir un nouveau (valable 1 heure) :
{lien}

Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.

— L'équipe CVPro
"""

    msg = Message(
        subject=sujet,
        recipients=[user.email],
        html=html,
        body=texte,
    )
    mail.send(msg)


# ==================== PAGE DE RÉINITIALISATION ====================
@password_reset_bp.route('/reinitialiser-mot-de-passe/<token>',
                          methods=['GET', 'POST'], strict_slashes=False)
def reset_password(token):
    """Page où l'utilisateur saisit son nouveau mot de passe."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    serializer = current_app.password_reset_serializer

    try:
        data = serializer.loads(token, max_age=DUREE_TOKEN)
    except SignatureExpired:
        flash('⏱ Ce lien a expiré. Faites une nouvelle demande.', 'error')
        return redirect(url_for('password_reset.forgot_password'))
    except BadSignature:
        flash('❌ Lien invalide ou corrompu.', 'error')
        return redirect(url_for('password_reset.forgot_password'))

    user_id = data.get('user_id')
    user = User.query.get(user_id)
    if not user:
        flash('❌ Utilisateur introuvable.', 'error')
        return redirect(url_for('password_reset.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        erreurs = []
        if len(password) < 6:
            erreurs.append('Le mot de passe doit contenir au moins 6 caractères.')
        if password != password2:
            erreurs.append('Les mots de passe ne correspondent pas.')

        if erreurs:
            for e in erreurs:
                flash(e, 'error')
            return render_template('reset_password.html', token=token, email=user.email)

        # Mise à jour du mot de passe
        user.set_password(password)
        db.session.commit()

        flash('✅ Mot de passe modifié avec succès ! Vous pouvez vous connecter.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', token=token, email=user.email)