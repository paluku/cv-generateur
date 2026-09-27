import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-temporaire-changez-moi')

    # Base de données
    SQLALCHEMY_DATABASE_URI = 'sqlite:///cvpro.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Stripe
    STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
    STRIPE_PRICE_ID = os.getenv('STRIPE_PRICE_ID')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
    BASE_URL = os.getenv('BASE_URL', 'http://127.0.0.1:5000')

    # Admin
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'cvpro-admin-2025')
    
    # ⭐ EMAIL (NOUVEAU)
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'CVPro <noreply@cvpro.fr>')
    
    
    # Stripe API Key
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY