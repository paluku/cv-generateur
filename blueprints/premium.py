import stripe
from flask import (Blueprint, request, jsonify, session, redirect,
                   url_for, render_template)
from flask_login import current_user

from config import Config
from extensions import db
from models import User

premium_bp = Blueprint('premium', __name__)


# ==================== STATUT PREMIUM ====================
@premium_bp.route('/api/premium/statut', strict_slashes=False)
def premium_statut():
    if current_user.is_authenticated:
        return jsonify({'premium': current_user.premium, 'connecte': True})
    return jsonify({'premium': False, 'connecte': False})


# ==================== ACTIVATION PAR CODE ====================
@premium_bp.route('/api/premium/activer-code', methods=['POST'], strict_slashes=False)
def premium_activer_code():
    if not current_user.is_authenticated:
        return jsonify({
            'success': False,
            'message': 'Créez un compte pour activer Premium.',
            'need_account': True,
        }), 401

    data = request.json or {}
    code = (data.get('code') or '').strip().upper()

    if code == 'PREMIUM2025':
        current_user.activer_premium()
        return jsonify({'success': True, 'message': 'Premium activé !'})

    return jsonify({'success': False, 'message': 'Code invalide'}), 403


# ==================== STRIPE CHECKOUT ====================
@premium_bp.route('/api/stripe/checkout', methods=['POST'], strict_slashes=False)
def stripe_checkout():
    if not current_user.is_authenticated:
        return jsonify({
            'success': False,
            'error': 'Vous devez créer un compte pour passer Premium.',
            'need_account': True,
        }), 401

    if current_user.premium:
        return jsonify({
            'success': False,
            'error': 'Vous êtes déjà Premium !',
        }), 400

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': Config.STRIPE_PRICE_ID, 'quantity': 1}],
            mode='payment',
            customer_email=current_user.email,
            success_url=f'{Config.BASE_URL}/paiement/succes?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{Config.BASE_URL}/paiement/annule',
            metadata={
                'produit': 'CVPro Premium',
                'user_id': str(current_user.id),
            },
            locale='fr',
            currency='eur',
        )

        return jsonify({
            'success': True,
            'checkout_url': checkout_session.url,
            'session_id': checkout_session.id,
        })

    except stripe.error.StripeError as e:
        print(f"❌ Erreur Stripe : {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500


# ==================== PAGES SUCCÈS / ANNULATION ====================
@premium_bp.route('/paiement/succes', strict_slashes=False)
def paiement_succes():
    session_id = request.args.get('session_id', '')
    montant = '4,99 €'
    email_client = ''
    paiement_verifie = False

    if current_user.is_authenticated:
        current_user.activer_premium()

    if session_id:
        try:
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            paiement_verifie = (checkout_session.payment_status == 'paid')
            if checkout_session.customer_details:
                email_client = checkout_session.customer_details.email or ''
            if checkout_session.amount_total:
                montant = f"{checkout_session.amount_total / 100:.2f} €".replace('.', ',')
        except Exception as e:
            print(f"⚠️ Vérif session : {e}")

    return render_template('succes_paiement.html',
                           montant=montant, email=email_client,
                           verifie=paiement_verifie, session_id=session_id)


@premium_bp.route('/paiement/annule', strict_slashes=False)
def paiement_annule():
    return render_template('annule_paiement.html')


# ==================== WEBHOOK STRIPE ====================
@premium_bp.route('/api/stripe/webhook', methods=['POST'], strict_slashes=False)
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    if not sig_header:
        return jsonify({'error': 'Signature manquante'}), 400

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, Config.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return jsonify({'error': 'Signature invalide'}), 400

    if event['type'] == 'checkout.session.completed':
        checkout_session = event['data']['object']
        print(f"✅ Paiement confirmé : {checkout_session['id']}")

        user_id = checkout_session.get('metadata', {}).get('user_id')
        if user_id:
            user = User.query.get(int(user_id))
            if user:
                user.activer_premium()
                print(f"👑 Premium activé pour {user.email}")

    return jsonify({'success': True}), 200


@premium_bp.route('/api/stripe/verifier-session/<session_id>', strict_slashes=False)
def stripe_verifier_session(session_id):
    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        if checkout_session.payment_status == 'paid':
            if current_user.is_authenticated:
                current_user.activer_premium()
            return jsonify({'success': True, 'premium': True})
        return jsonify({'success': False, 'message': checkout_session.payment_status})
    except stripe.error.StripeError as e:
        return jsonify({'success': False, 'error': str(e)}), 400