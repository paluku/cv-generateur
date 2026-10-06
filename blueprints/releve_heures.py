from calendar import monthrange
from datetime import date, datetime

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
)
from flask_login import login_required, current_user

from extensions import db
from models import Pointage, ReleveHeuresSettings


# ================================================================
# BLUEPRINT
# ================================================================

releve_heures_bp = Blueprint(
    'releve_heures',
    __name__,
    url_prefix='/releve-heures'
)


# ================================================================
# OUTILS
# ================================================================

def obtenir_reglages():
    """
    Récupère les réglages de l'utilisateur.

    Si aucun réglage n'existe encore,
    les réglages par défaut sont créés.
    """

    reglages = ReleveHeuresSettings.query.filter_by(
        user_id=current_user.id
    ).first()

    if reglages is None:
        reglages = ReleveHeuresSettings(
            user_id=current_user.id,
            duree_defaut_minutes=480,
            pause_defaut_minutes=60,
            heure_debut_defaut='08:00',
        )

        db.session.add(reglages)
        db.session.commit()

    return reglages


def convertir_minutes_heure(minutes):
    """
    Convertit un nombre de minutes en HH:MM.
    """

    minutes = minutes % (24 * 60)

    heures = minutes // 60
    minutes_restantes = minutes % 60

    return (
        f'{heures:02d}:'
        f'{minutes_restantes:02d}'
    )


def convertir_heure_minutes(heure):
    """
    Convertit HH:MM en nombre de minutes.
    """

    try:
        heures, minutes = heure.split(':')
        return int(heures) * 60 + int(minutes)
    except (ValueError, AttributeError):
        return 0


def formater_minutes(minutes):
    """
    Format identique à l'application Flutter.

    480  -> 8h
    495  -> 8h15
    """

    heures = minutes // 60
    minutes_restantes = minutes % 60

    if minutes_restantes == 0:
        return f'{heures}h'

    return (
        f'{heures}h'
        f'{minutes_restantes:02d}'
    )


def obtenir_mois(request):
    """
    Récupère le mois demandé.

    Format attendu :
    YYYY-MM

    Exemple :
    ?month=2026-10
    """

    valeur = request.args.get('month')

    if valeur:
        try:
            annee, mois = valeur.split('-')

            annee = int(annee)
            mois = int(mois)

            if 1 <= mois <= 12:
                return annee, mois

        except (ValueError, TypeError):
            pass

    maintenant = date.today()

    return maintenant.year, maintenant.month


def obtenir_pointages_mois(annee, mois):
    """
    Récupère uniquement les pointages
    de l'utilisateur connecté pour le mois.
    """

    debut = date(
        annee,
        mois,
        1
    )

    dernier_jour = monthrange(
        annee,
        mois
    )[1]

    fin = date(
        annee,
        mois,
        dernier_jour
    )

    return Pointage.query.filter(
        Pointage.user_id == current_user.id,
        Pointage.date >= debut,
        Pointage.date <= fin,
    ).order_by(
        Pointage.date.asc()
    ).all()


def pointage_dict(pointages):
    """
    Transforme les pointages en dictionnaire
    utilisable facilement par le template.
    """

    return {
        pointage.date.isoformat(): pointage
        for pointage in pointages
    }


# ================================================================
# PAGE PRINCIPALE
# ================================================================

@releve_heures_bp.route('/')
@login_required
def index():

    annee, mois = obtenir_mois(request)

    reglages = obtenir_reglages()

    pointages = obtenir_pointages_mois(
        annee,
        mois
    )

    pointages_par_date = pointage_dict(
        pointages
    )

    nombre_jours = monthrange(
        annee,
        mois
    )[1]

    premier_jour = date(
        annee,
        mois,
        1
    )

    # Python :
    # lundi = 0
    # dimanche = 6
    decalage = premier_jour.weekday()

    total_minutes = sum(
        pointage.total_minutes
        for pointage in pointages
        if pointage.statut in (
            'travail',
            'modifie',
        )
    )

    jours_travailles = sum(
        1
        for pointage in pointages
        if pointage.statut in (
            'travail',
            'modifie',
        )
    )

    absences = sum(
        1
        for pointage in pointages
        if pointage.statut == 'absence'
    )

    conges = sum(
        1
        for pointage in pointages
        if pointage.statut == 'conge'
    )

    noms_mois = [
        'Janvier',
        'Février',
        'Mars',
        'Avril',
        'Mai',
        'Juin',
        'Juillet',
        'Août',
        'Septembre',
        'Octobre',
        'Novembre',
        'Décembre',
    ]

    return render_template(
        'releve_heures/index.html',

        annee=annee,
        mois=mois,
        nom_mois=noms_mois[mois - 1],

        nombre_jours=nombre_jours,
        decalage=decalage,

        reglages=reglages,

        pointages=pointages,
        pointages_par_date=pointages_par_date,

        total_minutes=total_minutes,
        total_formate=formater_minutes(
            total_minutes
        ),

        jours_travailles=jours_travailles,
        absences=absences,
        conges=conges,
    )


# ================================================================
# AJOUT / MODIFICATION RAPIDE
# ================================================================

@releve_heures_bp.route(
    '/pointage/<string:date_pointage>/toggle',
    methods=['POST']
)
@login_required
def toggle_pointage(date_pointage):

    try:
        jour = datetime.strptime(
            date_pointage,
            '%Y-%m-%d'
        ).date()

    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Date invalide',
        }), 400

    reglages = obtenir_reglages()

    pointage = Pointage.query.filter_by(
        user_id=current_user.id,
        date=jour
    ).first()

    # ============================================================
    # VIDE → TRAVAIL
    # ============================================================

    if pointage is None:

        debut = convertir_heure_minutes(
            reglages.heure_debut_defaut
        )

        fin = (
            debut
            + reglages.duree_defaut_minutes
            + reglages.pause_defaut_minutes
        )

        pointage = Pointage(
            user_id=current_user.id,
            date=jour,
            total_minutes=
                reglages.duree_defaut_minutes,
            heure_debut=
                reglages.heure_debut_defaut,
            heure_fin=
                convertir_minutes_heure(fin),
            pause_minutes=
                reglages.pause_defaut_minutes,
            statut='travail',
            commentaire='',
        )

        db.session.add(pointage)
        db.session.commit()

        return jsonify({
            'success': True,
            'statut': 'travail',
            'total_minutes':
                pointage.total_minutes,
            'total_formate':
                formater_minutes(
                    pointage.total_minutes
                ),
        })

    # ============================================================
    # TRAVAIL / MODIFIÉ → ABSENCE
    # ============================================================

    if pointage.statut in (
        'travail',
        'modifie',
    ):

        pointage.total_minutes = 0
        pointage.statut = 'absence'

        db.session.commit()

        return jsonify({
            'success': True,
            'statut': 'absence',
            'total_minutes': 0,
            'total_formate': 'ABS',
        })

    # ============================================================
    # ABSENCE / CONGÉ → VIDE
    # ============================================================

    db.session.delete(pointage)
    db.session.commit()

    return jsonify({
        'success': True,
        'statut': 'vide',
        'total_minutes': 0,
        'total_formate': '',
    })


# ================================================================
# MODIFICATION D'UNE JOURNÉE
# ================================================================

@releve_heures_bp.route(
    '/pointage/<string:date_pointage>/modifier',
    methods=['GET', 'POST']
)
@login_required
def modifier_pointage(date_pointage):

    try:
        jour = datetime.strptime(
            date_pointage,
            '%Y-%m-%d'
        ).date()

    except ValueError:
        flash(
            'Date invalide.',
            'danger'
        )

        return redirect(
            url_for(
                'releve_heures.index'
            )
        )

    reglages = obtenir_reglages()

    pointage = Pointage.query.filter_by(
        user_id=current_user.id,
        date=jour
    ).first()

    # ============================================================
    # POST
    # ============================================================

    if request.method == 'POST':

        statut = (
            request.form.get(
                'statut'
            )
            or 'travail'
        )

        heure_debut = (
            request.form.get(
                'heure_debut'
            )
            or reglages.heure_debut_defaut
        )

        heure_fin = (
            request.form.get(
                'heure_fin'
            )
            or '17:00'
        )

        try:
            pause = int(
                request.form.get(
                    'pause_minutes',
                    reglages.pause_defaut_minutes
                )
            )
        except ValueError:
            pause = reglages.pause_defaut_minutes

        commentaire = (
            request.form.get(
                'commentaire'
            )
            or ''
        ).strip()

        # --------------------------------------------------------
        # ABSENCE / CONGÉ
        # --------------------------------------------------------

        if statut in (
            'absence',
            'conge',
        ):
            total = 0

        else:
            debut_minutes = (
                convertir_heure_minutes(
                    heure_debut
                )
            )

            fin_minutes = (
                convertir_heure_minutes(
                    heure_fin
                )
            )

            difference = (
                fin_minutes
                - debut_minutes
            )

            # Passage après minuit
            if difference < 0:
                difference += 24 * 60

            total = difference - pause

            if total < 0:
                total = 0

        # --------------------------------------------------------
        # STATUT AUTOMATIQUE
        # --------------------------------------------------------

        if statut == 'travail':
            if total != reglages.duree_defaut_minutes:
                statut = 'modifie'

        # --------------------------------------------------------
        # CRÉATION
        # --------------------------------------------------------

        if pointage is None:

            pointage = Pointage(
                user_id=current_user.id,
                date=jour,
                total_minutes=total,
                heure_debut=heure_debut,
                heure_fin=heure_fin,
                pause_minutes=pause,
                statut=statut,
                commentaire=commentaire,
            )

            db.session.add(pointage)

        # --------------------------------------------------------
        # MODIFICATION
        # --------------------------------------------------------

        else:

            pointage.total_minutes = total
            pointage.heure_debut = heure_debut
            pointage.heure_fin = heure_fin
            pointage.pause_minutes = pause
            pointage.statut = statut
            pointage.commentaire = commentaire

        db.session.commit()

        flash(
            'Journée enregistrée.',
            'success'
        )

        return redirect(
            url_for(
                'releve_heures.index',
                month=jour.strftime('%Y-%m')
            )
        )

    # ============================================================
    # GET
    # ============================================================

    if pointage is None:

        heure_debut = (
            reglages.heure_debut_defaut
        )

        debut_minutes = (
            convertir_heure_minutes(
                heure_debut
            )
        )

        fin_minutes = (
            debut_minutes
            + reglages.duree_defaut_minutes
            + reglages.pause_defaut_minutes
        )

        valeurs = {
            'statut': 'travail',
            'heure_debut': heure_debut,
            'heure_fin':
                convertir_minutes_heure(
                    fin_minutes
                ),
            'pause_minutes':
                reglages.pause_defaut_minutes,
            'total_minutes':
                reglages.duree_defaut_minutes,
            'commentaire': '',
        }

    else:

        valeurs = {
            'statut': pointage.statut,
            'heure_debut':
                pointage.heure_debut,
            'heure_fin':
                pointage.heure_fin,
            'pause_minutes':
                pointage.pause_minutes,
            'total_minutes':
                pointage.total_minutes,
            'commentaire':
                pointage.commentaire or '',
        }

    return render_template(
        'releve_heures/modifier.html',
        date_pointage=jour,
        valeurs=valeurs,
        reglages=reglages,
    )


# ================================================================
# SUPPRIMER UNE JOURNÉE
# ================================================================

@releve_heures_bp.route(
    '/pointage/<string:date_pointage>/supprimer',
    methods=['POST']
)
@login_required
def supprimer_pointage(date_pointage):

    try:
        jour = datetime.strptime(
            date_pointage,
            '%Y-%m-%d'
        ).date()

    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Date invalide',
        }), 400

    pointage = Pointage.query.filter_by(
        user_id=current_user.id,
        date=jour
    ).first()

    if pointage:
        db.session.delete(pointage)
        db.session.commit()

    return jsonify({
        'success': True
    })


# ================================================================
# RÉGLAGES
# ================================================================

@releve_heures_bp.route(
    '/settings',
    methods=['GET', 'POST']
)
@login_required
def settings():

    reglages = obtenir_reglages()

    if request.method == 'POST':

        try:
            duree = int(
                request.form.get(
                    'duree_defaut_minutes',
                    480
                )
            )
        except ValueError:
            duree = 480

        try:
            pause = int(
                request.form.get(
                    'pause_defaut_minutes',
                    60
                )
            )
        except ValueError:
            pause = 60

        heure = (
            request.form.get(
                'heure_debut_defaut'
            )
            or '08:00'
        )

        # Limites raisonnables
        duree = max(
            60,
            min(duree, 720)
        )

        pause = max(
            0,
            min(pause, 240)
        )

        reglages.duree_defaut_minutes = duree
        reglages.pause_defaut_minutes = pause
        reglages.heure_debut_defaut = heure

        db.session.commit()

        flash(
            'Réglages enregistrés.',
            'success'
        )

        return redirect(
            url_for(
                'releve_heures.index'
            )
        )

    return render_template(
        'releve_heures/settings.html',
        reglages=reglages,
    )


# ================================================================
# API : DONNÉES DU MOIS
# ================================================================

@releve_heures_bp.route(
    '/api/<int:annee>/<int:mois>'
)
@login_required
def api_mois(annee, mois):

    if mois < 1 or mois > 12:
        return jsonify({
            'success': False,
            'error': 'Mois invalide',
        }), 400

    pointages = obtenir_pointages_mois(
        annee,
        mois
    )

    return jsonify({
        'success': True,
        'annee': annee,
        'mois': mois,
        'pointages': [
            pointage.to_dict()
            for pointage in pointages
        ],
    })