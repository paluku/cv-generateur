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

class Candidature(db.Model):
    __tablename__ = 'candidatures'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    cv_id = db.Column(db.Integer, db.ForeignKey('cvs.id'), nullable=True)

    # Info sur l'offre
    offre_id = db.Column(db.String(100))
    offre_titre = db.Column(db.String(255))
    offre_entreprise = db.Column(db.String(255))
    offre_lieu = db.Column(db.String(255))
    offre_url = db.Column(db.Text)

    # Contenu
    message = db.Column(db.Text)
    email_employeur = db.Column(db.String(150))

    # Statut
    statut = db.Column(db.String(30), default='envoyee')

    # PDF en base64 (stockage temporaire ou définitif)
    pdf_base64 = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    auteur = db.relationship('User', backref=db.backref('candidatures',
                                                         lazy=True,
                                                         cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'offre_titre': self.offre_titre,
            'offre_entreprise': self.offre_entreprise,
            'offre_lieu': self.offre_lieu,
            'offre_url': self.offre_url,
            'statut': self.statut,
            'date': self.created_at.strftime('%d/%m/%Y à %H:%M') if self.created_at else '',
        }        
    
    
    
class AlerteEmploi(db.Model):
    __tablename__ = 'alertes_emploi'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    mots_cles = db.Column(db.String(200), nullable=False)
    ville = db.Column(db.String(100))
    source = db.Column(db.String(30), default='adzuna')
    frequence = db.Column(db.String(20), default='quotidienne')
    active = db.Column(db.Boolean, default=True)
    derniere_envoi = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    auteur = db.relationship(
        'User',
        backref=db.backref('alertes_emploi', lazy=True, cascade='all, delete-orphan')
    )

    def to_dict(self):
        return {
            'id': self.id,
            'mots_cles': self.mots_cles,
            'ville': self.ville or '',
            'source': self.source,
            'frequence': self.frequence,
            'active': self.active,
            'derniere_envoi': self.derniere_envoi.strftime('%d/%m/%Y') if self.derniere_envoi else 'Jamais',
            'created_at': self.created_at.strftime('%d/%m/%Y') if self.created_at else '',
        }
        
        

# ================================================================
# RELEVÉ D'HEURES
# ================================================================

class Pointage(db.Model):
    __tablename__ = 'pointages'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
        index=True
    )

    date = db.Column(
        db.Date,
        nullable=False,
        index=True
    )

    total_minutes = db.Column(
        db.Integer,
        nullable=False,
        default=480
    )

    heure_debut = db.Column(
        db.String(5),
        nullable=False,
        default='08:00'
    )

    heure_fin = db.Column(
        db.String(5),
        nullable=False,
        default='17:00'
    )

    pause_minutes = db.Column(
        db.Integer,
        nullable=False,
        default=60
    )

    statut = db.Column(
        db.String(20),
        nullable=False,
        default='travail'
    )

    commentaire = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint(
            'user_id',
            'date',
            name='uq_pointage_user_date'
        ),
    )


# ================================================================
# RÉGLAGES DU RELEVÉ D'HEURES
# ================================================================

class ReleveHeuresSettings(db.Model):
    __tablename__ = 'releve_heures_settings'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
        unique=True,
        index=True
    )

    duree_defaut_minutes = db.Column(
        db.Integer,
        nullable=False,
        default=480
    )

    pause_defaut_minutes = db.Column(
        db.Integer,
        nullable=False,
        default=60
    )

    heure_debut_defaut = db.Column(
        db.String(5),
        nullable=False,
        default='08:00'
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )