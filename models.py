from extensions import db
from flask_login import UserMixin
from datetime import datetime


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    telephone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    premium = db.Column(db.Boolean, default=False)
    premium_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

    def activer_premium(self):
        self.premium = True
        self.premium_date = datetime.utcnow()
        db.session.commit()


class CV(db.Model):
    __tablename__ = 'cvs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    titre = db.Column(db.String(150), nullable=False)
    modele = db.Column(db.String(30), nullable=False, default='modele1')
    donnees_json = db.Column(db.Text, nullable=False)
    photo = db.Column(db.Text)
    couleur = db.Column(db.String(10), default='#f39c12')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    auteur = db.relationship(
        'User',
        backref=db.backref('cvs', lazy=True, cascade='all, delete-orphan')
    )

    def to_dict(self, complet=False):
        import json
        base = {
            'id': self.id,
            'titre': self.titre,
            'modele': self.modele,
            'couleur': self.couleur,
            'has_photo': bool(self.photo),
            'created_at': self.created_at.strftime('%d/%m/%Y'),
            'updated_at': self.updated_at.strftime('%d/%m/%Y à %H:%M'),
            'updated_at_iso': self.updated_at.isoformat(),
        }
        if complet:
            base['donnees'] = json.loads(self.donnees_json)
            base['photo'] = self.photo
        return base        
        