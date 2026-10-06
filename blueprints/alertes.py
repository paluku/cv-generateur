"""
Blueprint pour les alertes email d'offres d'emploi.
"""
import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from flask_mail import Message

from extensions import db, mail
from models import AlerteEmploi, User
from adzuna_api import rechercher_offres_adzuna
from job_api import rechercher_offres, formater_offre

alertes_bp = Blueprint('alertes', __name__)


# ==================== PAGE ====================
@alertes_bp.route('/alertes', strict_slashes=False)
@login_required
def page_alertes():
    return render_template('alertes.html')


# ==================== API : LISTER ====================
@alertes_bp.route('/api/alertes', strict_slashes=False)
@login_required
def api_liste():
    alertes = (AlerteEmploi.query
               .filter_by(user_id=current_user.id)
               .order_by(AlerteEmploi.created_at.desc())
               .all())

    return jsonify({
        'success': True,
        'alertes': [a.to_dict() for a in alertes],
    })


# ==================== API : CRÉER ====================
@alertes_bp.route('/api/alertes', methods=['POST'], strict_slashes=False)
@login_required
def api_creer():
    data = request.json or {}
    mots_cles = (data.get('mots_cles') or '').strip()
    ville = (data.get('ville') or '').strip()
    source = data.get('source', 'adzuna')
    frequence = data.get('frequence', 'quotidienne')

    if not mots_cles:
        return jsonify({'success': False, 'error': 'Mots-clés obligatoires'}), 400

    # Limite : 3 alertes pour les gratuits, illimité pour Premium
    nb_alertes = AlerteEmploi.query.filter_by(user_id=current_user.id).count()
    if not current_user.premium and nb_alertes >= 3:
        return jsonify({
            'success': False,
            'error': 'Limite de 3 alertes atteinte (Premium pour illimité)',
            'limite_atteinte': True,
        }), 403

    alerte = AlerteEmploi(
        user_id=current_user.id,
        mots_cles=mots_cles,
        ville=ville,
        source=source,
        frequence=frequence,
        active=True,
    )
    db.session.add(alerte)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Alerte créée !',
        'alerte': alerte.to_dict(),
    }), 201


# ==================== API : SUPPRIMER ====================
@alertes_bp.route('/api/alertes/<int:alerte_id>', methods=['DELETE'], strict_slashes=False)
@login_required
def api_supprimer(alerte_id):
    alerte = AlerteEmploi.query.filter_by(id=alerte_id, user_id=current_user.id).first()
    if not alerte:
        return jsonify({'success': False, 'error': 'Alerte introuvable'}), 404

    db.session.delete(alerte)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Alerte supprimée'})


# ==================== API : ACTIVER/DÉSACTIVER ====================
@alertes_bp.route('/api/alertes/<int:alerte_id>/toggle', methods=['POST'], strict_slashes=False)
@login_required
def api_toggle(alerte_id):
    alerte = AlerteEmploi.query.filter_by(id=alerte_id, user_id=current_user.id).first()
    if not alerte:
        return jsonify({'success': False, 'error': 'Alerte introuvable'}), 404

    alerte.active = not alerte.active
    db.session.commit()
    return jsonify({'success': True, 'active': alerte.active})


# ==================== API : ENVOYER MAINTENANT (TEST) ====================
@alertes_bp.route('/api/alertes/<int:alerte_id>/envoyer-test', methods=['POST'], strict_slashes=False)
@login_required
def api_envoyer_test(alerte_id):
    """Envoie immédiatement l'alerte pour tester."""
    alerte = AlerteEmploi.query.filter_by(id=alerte_id, user_id=current_user.id).first()
    if not alerte:
        return jsonify({'success': False, 'error': 'Alerte introuvable'}), 404

    try:
        nb = envoyer_alerte(alerte, current_user)
        if nb > 0:
            alerte.derniere_envoi = datetime.utcnow()
            db.session.commit()
            return jsonify({'success': True, 'message': f'Email envoyé avec {nb} offres'})
        else:
            return jsonify({'success': True, 'message': 'Aucune nouvelle offre trouvée'})
    except Exception as e:
        print(f"❌ Erreur envoi alerte : {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== FONCTION D'ENVOI ====================
def envoyer_alerte(alerte, user):
    """Cherche les nouvelles offres et envoie l'email."""
    offres = []

    if alerte.source == 'adzuna':
        resultat = rechercher_offres_adzuna(
            mots_cles=alerte.mots_cles,
            ville=alerte.ville or '',
            nb_resultats=5,
        )
        if resultat.get('success'):
            offres = resultat.get('offres', [])
    else:  # france-travail
        resultat = rechercher_offres(
            mots_cles=alerte.mots_cles,
            nb_resultats=5,
        )
        if resultat.get('success'):
            offres = [formater_offre(o) for o in resultat.get('offres', [])]

    if not offres:
        return 0

    envoyer_email_alerte(user, alerte, offres)
    return len(offres)


# ==================== EMAIL ====================
def envoyer_email_alerte(user, alerte, offres):
    """Envoie l'email avec la liste détaillée des offres."""
    sujet = f"🔔 {len(offres)} nouvelle(s) offre(s) pour « {alerte.mots_cles} »"

    offres_html = ""
    for o in offres:
        titre = o.get('titre', 'Sans titre')
        entreprise = o.get('entreprise', 'Non précisé')
        lieu = o.get('lieu', '')
        salaire = o.get('salaire', '')
        contrat = o.get('type_contrat', '')
        # ⭐ Utiliser description_complete si dispo
        description = o.get('description_complete') or o.get('description', '')
        url = o.get('url', '')
        categorie = o.get('categorie', '')

        # Limiter à 500 caractères pour l'email
        if description and len(description) > 500:
            description = description[:500] + '...'

        if not url or url == '#':
            url = "https://cv-generateur-u8c8.onrender.com/emplois"

        # Badge contrat
        contrat_html = (
            f'<td style="text-align:right;white-space:nowrap;">'
            f'<span style="background:#fef3c7;color:#92400e;padding:4px 10px;'
            f'border-radius:12px;font-size:.7rem;font-weight:700;">{contrat}</span>'
            f'</td>'
        ) if contrat else ''

        # Badge catégorie
        categorie_html = (
            f'<span style="background:#fce7f3;color:#9d174d;padding:3px 10px;'
            f'border-radius:12px;font-size:.7rem;font-weight:700;'
            f'display:inline-block;margin-bottom:8px;">🏷️ {categorie}</span>'
        ) if categorie else ''

        salaire_html = (
            f'<div style="color:#16a34a;font-size:.9rem;font-weight:600;'
            f'margin-bottom:10px;">💰 {salaire}</div>'
        ) if salaire and salaire != 'Non précisé' else ''

        description_html = (
            f'<div style="color:#475569;font-size:.85rem;line-height:1.6;'
            f'margin-bottom:14px;padding:12px;background:#f9fbfc;'
            f'border-radius:8px;border-left:3px solid #f39c12;">'
            f'{description}</div>'
        ) if description else ''

        lieu_html = f' · 📍 {lieu}' if lieu else ''

        offres_html += f"""
        <div style="background:#fff;border:1px solid #e8ecf0;border-radius:14px;
                    padding:20px;margin-bottom:16px;">

          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:8px;">
            <tr>
              <td>
                <div style="font-size:1.05rem;font-weight:700;color:#2c3e50;
                            line-height:1.3;">
                  {titre}
                </div>
              </td>
              {contrat_html}
            </tr>
          </table>

          {categorie_html}

          <div style="color:#64748b;font-size:.9rem;margin-bottom:10px;">
            🏢 <b>{entreprise}</b>{lieu_html}
          </div>

          {salaire_html}
          {description_html}

          <div>
            <a href="{url}"
               style="display:inline-block;padding:10px 20px;background:#f39c12;
                      color:#fff;text-decoration:none;border-radius:8px;
                      font-weight:600;font-size:.85rem;">
              📄 Voir l'offre complète →
            </a>
          </div>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head><meta charset="utf-8"></head>
    <body style="font-family:Arial,sans-serif;background:#f4f6f9;
                 padding:30px 15px;margin:0;">
      <div style="max-width:640px;margin:0 auto;background:#fff;border-radius:16px;
                  overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.08);">

        <div style="background:linear-gradient(135deg,#7c3aed,#f39c12);
                    padding:32px 40px;text-align:center;">
          <h1 style="color:#fff;margin:0;font-size:1.5rem;">CVPro</h1>
          <p style="color:rgba(255,255,255,.9);margin:8px 0 0;font-size:.9rem;">
            🔔 Vos nouvelles offres d'emploi
          </p>
        </div>

        <div style="padding:32px 40px;">
          <h2 style="color:#2c3e50;margin:0 0 8px;font-size:1.3rem;">
            Bonjour {user.nom},
          </h2>
          <p style="color:#475569;line-height:1.7;margin:0 0 24px;font-size:.95rem;">
            Voici les <b>{len(offres)} dernières offres</b> correspondant à votre alerte
            <b style="color:#7c3aed;">« {alerte.mots_cles} »</b>{f" à <b>{alerte.ville}</b>" if alerte.ville else ""}.
          </p>

          {offres_html}

          <div style="text-align:center;margin-top:30px;padding-top:24px;
                      border-top:1px solid #e8ecf0;">
            <a href="https://cv-generateur-u8c8.onrender.com/emplois"
               style="display:inline-block;padding:14px 32px;background:#7c3aed;
                      color:#fff;text-decoration:none;border-radius:10px;
                      font-weight:700;font-size:.95rem;">
              🔍 Voir plus d'offres sur CVPro
            </a>
          </div>
        </div>

        <div style="background:#f9fbfc;padding:20px 40px;text-align:center;
                    border-top:1px solid #e8ecf0;">
          <p style="color:#94a3b8;font-size:.75rem;margin:0 0 8px;line-height:1.6;">
            Vous recevez cet email car vous avez créé une alerte sur CVPro.
          </p>
          <a href="https://cv-generateur-u8c8.onrender.com/alertes"
             style="color:#7c3aed;font-size:.8rem;text-decoration:none;">
            ⚙️ Gérer mes alertes
          </a>
        </div>
      </div>
    </body>
    </html>
    """

    msg = Message(
        subject=sujet,
        recipients=[user.email],
        html=html,
    )
    mail.send(msg)
    print(f"✅ Email alerte envoyé à {user.email} ({len(offres)} offres)")


# ==================== CRON : ENVOYER TOUTES LES ALERTES ====================
@alertes_bp.route('/api/cron/send-alerts', strict_slashes=False)
def cron_send_alerts():
    """
    Endpoint pour un cron externe.
    Sécurisé par une clé secrète.
    """
    cle_secrete = os.getenv('CRON_SECRET', 'changez-moi')
    cle_fournie = request.args.get('key', '')

    if cle_fournie != cle_secrete:
        return jsonify({'error': 'Non autorisé'}), 401

    alertes = AlerteEmploi.query.filter_by(active=True).all()

    total_envoyes = 0
    total_offres = 0

    for alerte in alertes:
        if alerte.derniere_envoi:
            heures = (datetime.utcnow() - alerte.derniere_envoi).total_seconds() / 3600
            if alerte.frequence == 'quotidienne' and heures < 20:
                continue
            elif alerte.frequence == 'hebdomadaire' and heures < 144:
                continue

        user = User.query.get(alerte.user_id)
        if not user:
            continue

        try:
            nb = envoyer_alerte(alerte, user)
            if nb > 0:
                alerte.derniere_envoi = datetime.utcnow()
                db.session.commit()
                total_envoyes += 1
                total_offres += nb
        except Exception as e:
            print(f"❌ Erreur alerte {alerte.id} : {e}")

    return jsonify({
        'success': True,
        'alertes_envoyees': total_envoyes,
        'total_offres': total_offres,
    })