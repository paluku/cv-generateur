"""
Gestion complète des statistiques avec :
- Compteurs globaux (visites, CV, lettres, inscriptions, premium, revenus)
- Historique quotidien (30 derniers jours)
- Visiteurs en ligne (temps réel)
- Top modèles utilisés
"""
import os
import json
import uuid
from datetime import datetime, timedelta

STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stats.json')
VISITEURS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'visiteurs.json')

DUREE_SESSION = 300  # 5 minutes


# ==================== STRUCTURE PAR DÉFAUT ====================
def _stats_vides():
    return {
        "visites": 0,
        "telechargements": 0,
        "telechargements_lettres": 0,
        "inscriptions": 0,
        "premium_achats": 0,
        "revenus_total": 0.0,
        "historique": {},
        "modeles_utilises": {},
    }


# ==================== LECTURE / ÉCRITURE ====================
def lire_stats():
    if not os.path.exists(STATS_FILE):
        stats = _stats_vides()
        ecrire_stats(stats)
        return stats
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            stats = json.load(f)

        # Compatibilité avec l'ancien format
        stats.setdefault("telechargements_lettres", 0)
        stats.setdefault("inscriptions", 0)
        stats.setdefault("premium_achats", 0)
        stats.setdefault("revenus_total", 0.0)
        stats.setdefault("historique", {})
        stats.setdefault("modeles_utilises", {})
        return stats
    except (json.JSONDecodeError, IOError):
        return _stats_vides()


def ecrire_stats(stats):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


# ==================== HISTORIQUE QUOTIDIEN ====================
def _aujourd_hui():
    return datetime.now().strftime('%Y-%m-%d')


def _incrementer_jour(stats, champ, valeur=1):
    """Incrémente un champ pour le jour courant."""
    date = _aujourd_hui()
    if date not in stats['historique']:
        stats['historique'][date] = {
            'visites': 0,
            'cv': 0,
            'lettres': 0,
            'inscriptions': 0,
            'premium': 0,
        }
    stats['historique'][date][champ] = stats['historique'][date].get(champ, 0) + valeur


# ==================== INCRÉMENTS ====================
def incrementer_visite():
    stats = lire_stats()
    stats['visites'] = stats.get('visites', 0) + 1
    _incrementer_jour(stats, 'visites')
    ecrire_stats(stats)


def incrementer_telechargement_cv():
    stats = lire_stats()
    stats['telechargements'] = stats.get('telechargements', 0) + 1
    _incrementer_jour(stats, 'cv')
    ecrire_stats(stats)


def incrementer_telechargement_lettre():
    stats = lire_stats()
    stats['telechargements_lettres'] = stats.get('telechargements_lettres', 0) + 1
    _incrementer_jour(stats, 'lettres')
    ecrire_stats(stats)


def incrementer_inscription():
    stats = lire_stats()
    stats['inscriptions'] = stats.get('inscriptions', 0) + 1
    _incrementer_jour(stats, 'inscriptions')
    ecrire_stats(stats)


def incrementer_premium(montant=4.99):
    stats = lire_stats()
    stats['premium_achats'] = stats.get('premium_achats', 0) + 1
    stats['revenus_total'] = round(stats.get('revenus_total', 0) + montant, 2)
    _incrementer_jour(stats, 'premium')
    ecrire_stats(stats)


def enregistrer_modele(modele_id):
    """Enregistre l'utilisation d'un modèle."""
    stats = lire_stats()
    stats['modeles_utilises'][modele_id] = stats['modeles_utilises'].get(modele_id, 0) + 1
    ecrire_stats(stats)


# ==================== PÉRIODES ====================
def stats_periode(jours=30):
    """Renvoie les stats des N derniers jours."""
    stats = lire_stats()
    historique = stats.get('historique', {})

    resultat = []
    aujourd_hui = datetime.now()

    for i in range(jours - 1, -1, -1):
        date = (aujourd_hui - timedelta(days=i)).strftime('%Y-%m-%d')
        jour_data = historique.get(date, {})

        resultat.append({
            'date': date,
            'jour': (aujourd_hui - timedelta(days=i)).strftime('%d/%m'),
            'visites': jour_data.get('visites', 0),
            'cv': jour_data.get('cv', 0),
            'lettres': jour_data.get('lettres', 0),
            'inscriptions': jour_data.get('inscriptions', 0),
            'premium': jour_data.get('premium', 0),
        })

    return resultat


def stats_resume():
    """Résumé des périodes clés."""
    historique = lire_stats().get('historique', {})
    maintenant = datetime.now()

    def somme_periode(jours, offset=0):
        total = {'visites': 0, 'cv': 0, 'lettres': 0, 'inscriptions': 0, 'premium': 0}
        for i in range(jours):
            date = (maintenant - timedelta(days=i + offset)).strftime('%Y-%m-%d')
            jour = historique.get(date, {})
            for key in total:
                total[key] += jour.get(key, 0)
        return total

    return {
        'aujourd_hui': somme_periode(1),
        'hier': somme_periode(1, offset=1),
        'semaine': somme_periode(7),
        'mois': somme_periode(30),
    }


# ==================== VISITEURS EN LIGNE ====================
def _charger_visiteurs():
    if not os.path.exists(VISITEURS_FILE):
        return {}
    try:
        with open(VISITEURS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _sauvegarder_visiteurs(visiteurs):
    with open(VISITEURS_FILE, 'w', encoding='utf-8') as f:
        json.dump(visiteurs, f, ensure_ascii=False)


def marquer_visiteur_en_ligne(session_id):
    """Marque un visiteur comme en ligne."""
    visiteurs = _charger_visiteurs()
    maintenant = datetime.now().timestamp()
    visiteurs[session_id] = maintenant
    _sauvegarder_visiteurs(visiteurs)


def compter_visiteurs_en_ligne():
    """Compte les visiteurs actifs (dernières 5 min)."""
    visiteurs = _charger_visiteurs()
    maintenant = datetime.now().timestamp()
    seuil = maintenant - DUREE_SESSION

    actifs = {sid: ts for sid, ts in visiteurs.items() if ts > seuil}
    _sauvegarder_visiteurs(actifs)

    return len(actifs)


# ==================== STATS TEMPS RÉEL ====================
def get_stats_temps_reel():
    """Renvoie toutes les stats en temps réel pour le widget live."""
    stats = lire_stats()
    visiteurs_en_ligne = compter_visiteurs_en_ligne()

    return {
        'visites': stats.get('visites', 0),
        'telechargements': stats.get('telechargements', 0),
        'telechargements_lettres': stats.get('telechargements_lettres', 0),
        'inscriptions': stats.get('inscriptions', 0),
        'premium_achats': stats.get('premium_achats', 0),
        'revenus_total': stats.get('revenus_total', 0),
        'visiteurs_en_ligne': visiteurs_en_ligne,
        'timestamp': datetime.now().isoformat(),
    }