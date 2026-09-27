"""
Admin — Contrôle et gestion de la base de données.
"""
import os
import csv
from io import StringIO
from datetime import datetime
from functools import wraps

from flask import (Blueprint, render_template_string, request, redirect,
                   url_for, flash, session, jsonify, Response)
from flask_login import current_user

from extensions import db
from models import User, CV


admin_db_bp = Blueprint('admin_db', __name__)


# ==================== DÉCORATEUR ====================
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_connecte'):
            return redirect(url_for('admin.admin_login'))
        return f(*args, **kwargs)
    return decorated


# ==================== HELPERS ====================
def _chemin_db():
    possible = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'cvpro.db'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cvpro.db'),
    ]
    return next((p for p in possible if os.path.exists(p)), None)


def _taille_db():
    path = _chemin_db()
    return os.path.getsize(path) if path else 0


def _format_taille(octets):
    for unite in ['o', 'Ko', 'Mo', 'Go']:
        if octets < 1024:
            return f"{octets:.1f} {unite}"
        octets /= 1024
    return f"{octets:.1f} To"


# ==================== PAGE PRINCIPALE DB ====================
@admin_db_bp.route('/admin/database', strict_slashes=False)
@admin_required
def admin_database():
    path = _chemin_db()
    taille = _taille_db()
    nb_users = User.query.count()
    nb_premium = User.query.filter_by(premium=True).count()
    nb_cv = CV.query.count()

    taille_moyenne_cv = 0
    if nb_cv > 0:
        total_chars = db.session.execute(
            db.text("SELECT SUM(LENGTH(donnees_json)) FROM cvs")
        ).scalar() or 0
        taille_moyenne_cv = total_chars / nb_cv / 1024

    dernier_cv = CV.query.order_by(CV.updated_at.desc()).first()
    dernier_user = User.query.order_by(User.created_at.desc()).first()

    return render_template_string(DB_DASHBOARD_HTML,
                                  chemin=path or 'Non trouvé',
                                  taille=_format_taille(taille),
                                  taille_octets=taille,
                                  nb_users=nb_users,
                                  nb_premium=nb_premium,
                                  nb_cv=nb_cv,
                                  taille_moyenne=f"{taille_moyenne_cv:.1f} Ko",
                                  dernier_cv=dernier_cv,
                                  dernier_user=dernier_user,
                                  maintenant=datetime.now())


# ==================== EXPLORATEUR TABLE ====================
@admin_db_bp.route('/admin/database/table/<nom_table>', strict_slashes=False)
@admin_required
def admin_db_table(nom_table):
    TABLES_AUTORISEES = {
        'users': ['id', 'nom', 'email', 'telephone', 'premium', 'premium_date', 'created_at'],
        'cvs': ['id', 'user_id', 'titre', 'modele', 'couleur', 'created_at', 'updated_at'],
    }

    if nom_table not in TABLES_AUTORISEES:
        flash('Table non autorisée.', 'error')
        return redirect(url_for('admin_db.admin_database'))

    colonnes = TABLES_AUTORISEES[nom_table]
    page = request.args.get('page', 1, type=int)
    par_page = 25
    offset = (page - 1) * par_page
    recherche = request.args.get('q', '').strip()

    if nom_table == 'users':
        query = User.query
        if recherche:
            query = query.filter(
                db.or_(User.nom.ilike(f'%{recherche}%'),
                       User.email.ilike(f'%{recherche}%'))
            )
        query = query.order_by(User.created_at.desc())
        total = query.count()
        lignes = query.limit(par_page).offset(offset).all()
        rows = [{
            'id': u.id, 'nom': u.nom, 'email': u.email,
            'telephone': u.telephone or '—',
            'premium': '👑 Oui' if u.premium else 'Gratuit',
            'premium_date': u.premium_date.strftime('%d/%m/%Y') if u.premium_date else '—',
            'created_at': u.created_at.strftime('%d/%m/%Y %H:%M') if u.created_at else '—',
        } for u in lignes]

    else:  # cvs
        query = CV.query
        if recherche:
            query = query.filter(CV.titre.ilike(f'%{recherche}%'))
        query = query.order_by(CV.updated_at.desc())
        total = query.count()
        lignes = query.limit(par_page).offset(offset).all()
        rows = [{
            'id': cv.id, 'user_id': cv.user_id, 'titre': cv.titre,
            'modele': cv.modele, 'couleur': cv.couleur or '—',
            'created_at': cv.created_at.strftime('%d/%m/%Y') if cv.created_at else '—',
            'updated_at': cv.updated_at.strftime('%d/%m/%Y %H:%M') if cv.updated_at else '—',
        } for cv in lignes]

    total_pages = (total + par_page - 1) // par_page

    return render_template_string(TABLE_HTML,
                                  nom_table=nom_table,
                                  colonnes=colonnes,
                                  rows=rows,
                                  total=total,
                                  page=page,
                                  total_pages=total_pages,
                                  recherche=recherche)


# ==================== ACTIONS ====================
@admin_db_bp.route('/admin/database/user/<int:user_id>/supprimer',
                   methods=['POST'], strict_slashes=False)
@admin_required
def admin_db_supprimer_user(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('Utilisateur introuvable.', 'error')
        return redirect(url_for('admin_db.admin_db_table', nom_table='users'))
    try:
        email = user.email
        db.session.delete(user)
        db.session.commit()
        flash(f'Utilisateur {email} supprimé.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {e}', 'error')
    return redirect(url_for('admin_db.admin_db_table', nom_table='users'))


@admin_db_bp.route('/admin/database/user/<int:user_id>/toggle-premium',
                   methods=['POST'], strict_slashes=False)
@admin_required
def admin_db_toggle_premium(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('Utilisateur introuvable.', 'error')
        return redirect(url_for('admin_db.admin_db_table', nom_table='users'))
    try:
        if user.premium:
            user.premium = False
            user.premium_date = None
            flash(f'{user.email} — Premium retiré.', 'success')
        else:
            user.activer_premium()
            flash(f'{user.email} — Premium activé.', 'success')
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {e}', 'error')
    return redirect(url_for('admin_db.admin_db_table', nom_table='users'))


@admin_db_bp.route('/admin/database/cv/<int:cv_id>/supprimer',
                   methods=['POST'], strict_slashes=False)
@admin_required
def admin_db_supprimer_cv(cv_id):
    cv = CV.query.get(cv_id)
    if not cv:
        flash('CV introuvable.', 'error')
        return redirect(url_for('admin_db.admin_db_table', nom_table='cvs'))
    try:
        db.session.delete(cv)
        db.session.commit()
        flash('CV supprimé.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {e}', 'error')
    return redirect(url_for('admin_db.admin_db_table', nom_table='cvs'))


# ==================== REQUÊTE SQL ====================
@admin_db_bp.route('/admin/database/query', methods=['GET', 'POST'], strict_slashes=False)
@admin_required
def admin_db_query():
    resultat = None
    erreur = None
    requete = ''

    if request.method == 'POST':
        requete = (request.form.get('requete') or '').strip()

        if not requete.upper().startswith('SELECT'):
            erreur = '❌ Seules les requêtes SELECT sont autorisées.'
        elif any(mot in requete.upper() for mot in ['DROP ', 'DELETE ', 'UPDATE ', 'INSERT ', 'ALTER ', 'CREATE ']):
            erreur = '❌ Mots-clés non autorisés détectés.'
        elif len(requete) > 2000:
            erreur = '❌ Requête trop longue.'
        else:
            try:
                if 'LIMIT' not in requete.upper():
                    requete_limitee = requete.rstrip(';') + ' LIMIT 100'
                else:
                    requete_limitee = requete

                result = db.session.execute(db.text(requete_limitee))
                colonnes = list(result.keys())
                lignes = [dict(zip(colonnes, row)) for row in result.fetchall()]
                resultat = {'colonnes': colonnes, 'lignes': lignes, 'count': len(lignes)}
            except Exception as e:
                erreur = f'❌ Erreur SQL : {e}'

    return render_template_string(QUERY_HTML,
                                  resultat=resultat, erreur=erreur, requete=requete)


# ==================== EXPORT ====================
@admin_db_bp.route('/admin/database/export/<nom_table>', strict_slashes=False)
@admin_required
def admin_db_export(nom_table):
    if nom_table not in ['users', 'cvs']:
        return "Table non autorisée", 403

    def gen():
        data = StringIO()
        writer = csv.writer(data, delimiter=';')
        yield data.getvalue()
        data.seek(0); data.truncate(0)

        if nom_table == 'users':
            writer.writerow(['ID', 'Nom', 'Email', 'Téléphone', 'Premium', 'Premium_date', 'Inscription'])
            yield data.getvalue(); data.seek(0); data.truncate(0)
            for u in User.query.all():
                writer.writerow([
                    u.id, u.nom, u.email, u.telephone or '',
                    'Oui' if u.premium else 'Non',
                    u.premium_date.strftime('%Y-%m-%d') if u.premium_date else '',
                    u.created_at.strftime('%Y-%m-%d') if u.created_at else '',
                ])
                yield data.getvalue(); data.seek(0); data.truncate(0)
        else:
            writer.writerow(['ID', 'User_ID', 'Titre', 'Modèle', 'Couleur', 'Créé', 'Modifié'])
            yield data.getvalue(); data.seek(0); data.truncate(0)
            for cv in CV.query.all():
                writer.writerow([
                    cv.id, cv.user_id, cv.titre, cv.modele, cv.couleur or '',
                    cv.created_at.strftime('%Y-%m-%d') if cv.created_at else '',
                    cv.updated_at.strftime('%Y-%m-%d') if cv.updated_at else '',
                ])
                yield data.getvalue(); data.seek(0); data.truncate(0)

    fichier = f'cvpro_{nom_table}_{datetime.now().strftime("%Y-%m-%d")}.csv'
    return Response(gen(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename={fichier}'})


# ==================== MAINTENANCE ====================
@admin_db_bp.route('/admin/database/maintenance', methods=['POST'], strict_slashes=False)
@admin_required
def admin_db_maintenance():
    action = request.form.get('action', '')

    try:
        if action == 'vacuum':
            db.session.execute(db.text('VACUUM'))
            db.session.commit()
            flash('✅ Base compactée (VACUUM).', 'success')
        elif action == 'analyze':
            db.session.execute(db.text('ANALYZE'))
            db.session.commit()
            flash('✅ Base analysée (ANALYZE).', 'success')
        elif action == 'integrity':
            result = db.session.execute(db.text('PRAGMA integrity_check')).scalar()
            if result == 'ok':
                flash('✅ Intégrité : OK', 'success')
            else:
                flash(f'⚠️ Problèmes : {result}', 'error')
        else:
            flash('Action inconnue.', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erreur : {e}', 'error')

    return redirect(url_for('admin_db.admin_database'))


# ================================================================
# TEMPLATES HTML
# ================================================================

DB_DASHBOARD_HTML = '''
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Base de données — CVPro Admin</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: 'Segoe UI', Arial, sans-serif;
         background: #0f172a; color: #e2e8f0;
         min-height: 100vh; padding: 30px 20px; }
  .container { max-width: 1400px; margin: 0 auto; }
  .topbar { display: flex; justify-content: space-between;
            align-items: center; margin-bottom: 30px;
            flex-wrap: wrap; gap: 16px; }
  h1 { color: #f39c12; font-size: 1.9rem; }
  .date { color: #94a3b8; font-size: .85rem; margin-top: 4px; }
  .actions-top { display: flex; gap: 10px; flex-wrap: wrap; }
  .btn { padding: 10px 18px; border-radius: 10px; text-decoration: none;
         font-weight: 600; font-size: .85rem; cursor: pointer;
         border: none; font-family: inherit; transition: all .2s;
         display: inline-flex; align-items: center; gap: 6px; }
  .btn-or { background: #f39c12; color: #fff; }
  .btn-ghost { background: transparent; color: #94a3b8;
               border: 1px solid #334155; }
  .btn-ghost:hover { border-color: #f39c12; color: #f39c12; }
  .btn-danger { background: #ef4444; color: #fff; }

  .grille { display: grid;
            grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
            gap: 16px; margin-bottom: 26px; }
  .stat { background: #1e293b; border: 1px solid #334155;
          border-radius: 16px; padding: 20px; position: relative;
          overflow: hidden; }
  .stat::before { content: ''; position: absolute;
                  top: 0; left: 0; right: 0; height: 3px;
                  background: linear-gradient(90deg, #f39c12, #e67e22); }
  .stat .ico { font-size: 1.6rem; margin-bottom: 8px; display: block; }
  .stat .val { font-size: 1.8rem; font-weight: 800; color: #f39c12;
               line-height: 1; margin-bottom: 6px; }
  .stat .lbl { font-size: .7rem; color: #94a3b8;
               text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }
  .stat .sub { font-size: .72rem; color: #64748b; margin-top: 5px; }

  .section { background: #1e293b; border: 1px solid #334155;
             border-radius: 16px; padding: 22px; margin-bottom: 22px; }
  .section h2 { color: #f39c12; font-size: 1.1rem;
                margin-bottom: 16px; display: flex;
                align-items: center; gap: 10px; }

  .table-item { display: flex; justify-content: space-between;
                align-items: center; padding: 14px 18px;
                background: #0f172a; border-radius: 12px;
                margin-bottom: 10px; text-decoration: none;
                color: #e2e8f0; transition: all .2s;
                border-left: 3px solid #f39c12; }
  .table-item:hover { background: #1a2332; transform: translateX(4px); }
  .table-item .nom { font-weight: 700; font-size: 1rem;
                     font-family: monospace; color: #f39c12; }
  .table-item .lignes { color: #94a3b8; font-size: .85rem; }
  .table-item .lignes b { color: #e2e8f0; font-size: 1.1rem; }

  .actions-grille { display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                    gap: 12px; }
  .action-btn { background: #0f172a; border: 1px solid #334155;
                border-radius: 12px; padding: 16px;
                text-decoration: none; color: #e2e8f0;
                font-weight: 600; font-size: .85rem;
                text-align: center; transition: all .2s;
                display: block; cursor: pointer; font-family: inherit;
                width: 100%; }
  .action-btn:hover { border-color: #f39c12;
                      background: #1e293b;
                      transform: translateY(-2px); }
  .action-btn .ico { font-size: 1.5rem; display: block;
                     margin-bottom: 6px; }

  .info-box { background: #0f172a; border-left: 3px solid #3b82f6;
              border-radius: 8px; padding: 14px 18px;
              margin-bottom: 16px; font-size: .85rem;
              color: #94a3b8; line-height: 1.6; }
  .info-box code { background: #1e293b; color: #f39c12;
                   padding: 2px 8px; border-radius: 4px;
                   font-family: monospace; font-size: .82rem; }
</style></head><body>
<div class="container">
  <div class="topbar">
    <div>
      <h1>🗄️ Base de données</h1>
      <p class="date">🕐 {{ maintenant.strftime('%d/%m/%Y à %H:%M') }}</p>
    </div>
    <div class="actions-top">
      <a href="/admin/stats" class="btn btn-or">📊 Dashboard</a>
      <a href="/admin/database/query" class="btn btn-ghost">🔎 Requête SQL</a>
      <a href="/admin/logout" class="btn btn-danger">🚪</a>
    </div>
  </div>

  <div class="grille">
    <div class="stat">
      <span class="ico">💾</span>
      <div class="val">{{ taille }}</div>
      <div class="lbl">Taille base</div>
      <div class="sub">{{ taille_octets }} octets</div>
    </div>
    <div class="stat">
      <span class="ico">👤</span>
      <div class="val">{{ nb_users }}</div>
      <div class="lbl">Utilisateurs</div>
      <div class="sub">{{ nb_premium }} premium</div>
    </div>
    <div class="stat">
      <span class="ico">📂</span>
      <div class="val">{{ nb_cv }}</div>
      <div class="lbl">CV sauvegardés</div>
      <div class="sub">~{{ taille_moyenne }} / CV</div>
    </div>
    <div class="stat">
      <span class="ico">📋</span>
      <div class="val">2</div>
      <div class="lbl">Tables</div>
      <div class="sub">users, cvs</div>
    </div>
  </div>

  <div class="section">
    <h2>📁 Chemin de la base</h2>
    <div class="info-box">
      <b>Fichier SQLite :</b><br>
      <code>{{ chemin }}</code>
    </div>
  </div>

  <div class="section">
    <h2>📋 Tables</h2>
    <a href="/admin/database/table/users" class="table-item">
      <div>
        <div class="nom">users</div>
        <div class="lignes">{{ nb_users }} ligne(s)</div>
      </div>
      <div class="lignes">👤 <b>{{ nb_users }}</b></div>
    </a>
    <a href="/admin/database/table/cvs" class="table-item">
      <div>
        <div class="nom">cvs</div>
        <div class="lignes">{{ nb_cv }} ligne(s)</div>
      </div>
      <div class="lignes">📂 <b>{{ nb_cv }}</b></div>
    </a>
  </div>

  <div class="section">
    <h2>🕐 Dernières activités</h2>
    <div class="info-box">
      {% if dernier_user %}
        <b>Dernier inscrit :</b> {{ dernier_user.nom }} ({{ dernier_user.email }})
        le {{ dernier_user.created_at.strftime('%d/%m/%Y à %H:%M') }}<br>
      {% else %}
        <b>Dernier inscrit :</b> aucun<br>
      {% endif %}
      {% if dernier_cv %}
        <br><b>Dernier CV :</b> "{{ dernier_cv.titre }}"
        le {{ dernier_cv.updated_at.strftime('%d/%m/%Y à %H:%M') }}
      {% else %}
        <br><b>Dernier CV :</b> aucun
      {% endif %}
    </div>
  </div>

  <div class="section">
    <h2>🔧 Maintenance</h2>
    <div class="actions-grille">
      <form method="post" action="/admin/database/maintenance" style="display:contents;">
        <input type="hidden" name="action" value="vacuum">
        <button type="submit" class="action-btn"
                onclick="return confirm('Compacter la base ?')">
          <span class="ico">🗜️</span>Compacter (VACUUM)
        </button>
      </form>
      <form method="post" action="/admin/database/maintenance" style="display:contents;">
        <input type="hidden" name="action" value="analyze">
        <button type="submit" class="action-btn">
          <span class="ico">📊</span>Analyser (ANALYZE)
        </button>
      </form>
      <form method="post" action="/admin/database/maintenance" style="display:contents;">
        <input type="hidden" name="action" value="integrity">
        <button type="submit" class="action-btn">
          <span class="ico">✅</span>Vérifier l'intégrité
        </button>
      </form>
      <a href="/admin/backup" class="action-btn">
        <span class="ico">💾</span>Backup DB
      </a>
    </div>
  </div>
</div>
</body></html>
'''


TABLE_HTML = '''
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ nom_table }} — CVPro Admin</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: 'Segoe UI', Arial, sans-serif;
         background: #0f172a; color: #e2e8f0; padding: 30px 20px; }
  .container { max-width: 1400px; margin: 0 auto; }
  .topbar { display: flex; justify-content: space-between;
            align-items: center; margin-bottom: 20px;
            flex-wrap: wrap; gap: 12px; }
  h1 { color: #f39c12; font-size: 1.6rem; }
  h1 code { color: #e2e8f0; background: #1e293b;
            padding: 4px 12px; border-radius: 8px;
            font-family: monospace; font-size: 1.3rem; }
  .sub { color: #94a3b8; font-size: .85rem; margin-top: 6px; }
  .btn { padding: 10px 18px; border-radius: 10px;
         text-decoration: none; font-weight: 600; font-size: .85rem;
         border: none; cursor: pointer; font-family: inherit;
         display: inline-flex; align-items: center; gap: 6px; }
  .btn-or { background: #f39c12; color: #fff; }
  .btn-ghost { background: transparent; color: #94a3b8;
               border: 1px solid #334155; }

  .barre-recherche { background: #1e293b; padding: 16px;
                     border-radius: 12px; margin-bottom: 20px;
                     display: flex; gap: 12px; flex-wrap: wrap; }
  .barre-recherche input { flex: 1; min-width: 200px;
                           padding: 12px 16px; border: 1px solid #334155;
                           background: #0f172a; color: #e2e8f0;
                           border-radius: 8px; font-family: inherit;
                           font-size: .9rem; }
  .barre-recherche input:focus { outline: none; border-color: #f39c12; }

  .table-wrap { background: #1e293b; border-radius: 14px;
                overflow: auto; border: 1px solid #334155; }
  table { width: 100%; border-collapse: collapse; min-width: 700px; }
  th { text-align: left; color: #94a3b8; font-size: .7rem;
       text-transform: uppercase; letter-spacing: 1px;
       padding: 14px 16px; background: #0f172a; font-weight: 700;
       position: sticky; top: 0; z-index: 2; }
  td { padding: 12px 16px; border-top: 1px solid #334155;
       font-size: .85rem; vertical-align: middle; }
  tr:hover td { background: #0f172a; }
  td.actions { display: flex; gap: 6px; }
  .btn-xs { padding: 6px 10px; border-radius: 6px; border: none;
            cursor: pointer; font-family: inherit; font-size: .75rem;
            font-weight: 700; transition: all .2s; white-space: nowrap; }
  .btn-premium { background: #f59e0b; color: #fff; }
  .btn-demote { background: #64748b; color: #fff; }
  .btn-suppr { background: #ef4444; color: #fff; }

  .badge { display: inline-block; padding: 3px 10px;
           border-radius: 10px; font-size: .72rem; font-weight: 700; }
  .badge-premium { background: #fef3c7; color: #92400e; }
  .badge-gratuit { background: #e5e7eb; color: #374151; }
  .couleur-pastille { display: inline-block; width: 14px; height: 14px;
                      border-radius: 50%; vertical-align: middle;
                      margin-right: 6px; border: 1px solid #475569; }

  .pagination { display: flex; justify-content: center;
                gap: 8px; margin-top: 20px; flex-wrap: wrap; }
  .page-btn { padding: 8px 14px; background: #1e293b;
              color: #e2e8f0; border: 1px solid #334155;
              border-radius: 8px; text-decoration: none;
              font-size: .85rem; font-weight: 600; }
  .page-btn:hover { border-color: #f39c12; color: #f39c12; }
  .page-btn.actif { background: #f39c12; color: #fff;
                    border-color: #f39c12; }
  .vide { text-align: center; color: #64748b;
          padding: 40px; font-style: italic; }
</style></head><body>
<div class="container">
  <div class="topbar">
    <div>
      <h1>Table <code>{{ nom_table }}</code></h1>
      <p class="sub">{{ total }} ligne(s) au total</p>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;">
      <a href="/admin/database" class="btn btn-or">← Base</a>
      <a href="/admin/database/export/{{ nom_table }}" class="btn btn-ghost">📥 Export CSV</a>
    </div>
  </div>

  <form method="get" class="barre-recherche">
    <input type="text" name="q" value="{{ recherche }}" placeholder="🔍 Rechercher...">
    <button type="submit" class="btn btn-or">Rechercher</button>
    {% if recherche %}
      <a href="/admin/database/table/{{ nom_table }}" class="btn btn-ghost">Effacer</a>
    {% endif %}
  </form>

  <div class="table-wrap">
    <table>
      <thead><tr>
        {% for col in colonnes %}<th>{{ col }}</th>{% endfor %}
        <th>Actions</th>
      </tr></thead>
      <tbody>
        {% if rows %}
          {% for row in rows %}
            <tr>
              {% for col in colonnes %}
                <td>
                  {% if col == 'premium' %}
                    {% if 'Oui' in row[col]|string %}
                      <span class="badge badge-premium">👑 Premium</span>
                    {% else %}
                      <span class="badge badge-gratuit">Gratuit</span>
                    {% endif %}
                  {% elif col == 'couleur' and row[col] != '—' %}
                    <span class="couleur-pastille" style="background:{{ row[col] }};"></span>
                    {{ row[col] }}
                  {% elif col == 'titre' %}
                    <b>{{ row[col] }}</b>
                  {% else %}
                    {{ row[col] }}
                  {% endif %}
                </td>
              {% endfor %}
              <td class="actions">
                {% if nom_table == 'users' %}
                  <form method="post"
                        action="/admin/database/user/{{ row.id }}/toggle-premium"
                        style="display:inline;">
                    {% if 'Oui' in row.premium|string %}
                      <button type="submit" class="btn-xs btn-demote"
                              onclick="return confirm('Retirer le Premium ?')">
                        ⬇ Retirer
                      </button>
                    {% else %}
                      <button type="submit" class="btn-xs btn-premium"
                              onclick="return confirm('Promouvoir en Premium ?')">
                        👑 Premium
                      </button>
                    {% endif %}
                  </form>
                  <form method="post"
                        action="/admin/database/user/{{ row.id }}/supprimer"
                        style="display:inline;"
                        onsubmit="return confirm('⚠️ Supprimer DÉFINITIVEMENT cet utilisateur ?')">
                    <button type="submit" class="btn-xs btn-suppr">🗑</button>
                  </form>
                {% elif nom_table == 'cvs' %}
                  <form method="post"
                        action="/admin/database/cv/{{ row.id }}/supprimer"
                        style="display:inline;"
                        onsubmit="return confirm('Supprimer ce CV ?')">
                    <button type="submit" class="btn-xs btn-suppr">🗑</button>
                  </form>
                {% endif %}
              </td>
            </tr>
          {% endfor %}
        {% else %}
          <tr><td colspan="{{ colonnes|length + 1 }}" class="vide">
            Aucun résultat
          </td></tr>
        {% endif %}
      </tbody>
    </table>
  </div>

  {% if total_pages > 1 %}
    <div class="pagination">
      {% if page > 1 %}
        <a href="?page={{ page - 1 }}{% if recherche %}&q={{ recherche }}{% endif %}"
           class="page-btn">← Précédent</a>
      {% endif %}
      {% for p in range(1, total_pages + 1) %}
        {% if p == page or (p <= 3) or (p >= total_pages - 2) or (p >= page - 1 and p <= page + 1) %}
          <a href="?page={{ p }}{% if recherche %}&q={{ recherche }}{% endif %}"
             class="page-btn {% if p == page %}actif{% endif %}">{{ p }}</a>
        {% endif %}
      {% endfor %}
      {% if page < total_pages %}
        <a href="?page={{ page + 1 }}{% if recherche %}&q={{ recherche }}{% endif %}"
           class="page-btn">Suivant →</a>
      {% endif %}
    </div>
  {% endif %}
</div>
</body></html>
'''


QUERY_HTML = '''
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<title>Requête SQL — CVPro Admin</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: 'Segoe UI', Arial, sans-serif;
         background: #0f172a; color: #e2e8f0; padding: 30px 20px; }
  .container { max-width: 1200px; margin: 0 auto; }
  .topbar { display: flex; justify-content: space-between;
            align-items: center; margin-bottom: 20px;
            flex-wrap: wrap; gap: 12px; }
  h1 { color: #f39c12; font-size: 1.6rem; }
  .btn { padding: 10px 18px; border-radius: 10px;
         text-decoration: none; font-weight: 600; font-size: .85rem;
         background: #f39c12; color: #fff; border: none;
         cursor: pointer; font-family: inherit; }
  .info { background: #1e293b; padding: 16px 20px;
          border-radius: 12px; margin-bottom: 20px;
          border-left: 3px solid #3b82f6; color: #94a3b8;
          font-size: .85rem; line-height: 1.6; }
  .info code { background: #0f172a; color: #f39c12;
               padding: 2px 8px; border-radius: 4px;
               font-family: monospace; }
  textarea { width: 100%; padding: 16px; border: 1px solid #334155;
             background: #1e293b; color: #e2e8f0;
             border-radius: 12px; font-family: monospace;
             font-size: .9rem; min-height: 120px;
             resize: vertical; line-height: 1.5; }
  textarea:focus { outline: none; border-color: #f39c12; }
  .actions { margin: 14px 0; display: flex; gap: 10px; flex-wrap: wrap; }
  .btn-primary { padding: 12px 24px; background: #f39c12;
                 color: #fff; border: none; border-radius: 10px;
                 font-weight: 700; cursor: pointer;
                 font-family: inherit; font-size: .95rem; }
  .resultat { background: #1e293b; border-radius: 14px;
              padding: 20px; margin-top: 20px;
              border: 1px solid #334155; }
  .resultat h3 { color: #f39c12; margin-bottom: 14px;
                 font-size: 1rem; }
  .resultat table { width: 100%; border-collapse: collapse;
                    font-size: .82rem; font-family: monospace; }
  .resultat th { text-align: left; color: #94a3b8;
                 font-size: .7rem; text-transform: uppercase;
                 padding: 8px 12px; border-bottom: 1px solid #334155;
                 background: #0f172a; }
  .resultat td { padding: 8px 12px;
                 border-bottom: 1px solid #334155; }
  .erreur { background: #7f1d1d; color: #fecaca;
            padding: 16px; border-radius: 12px;
            margin-top: 20px; border-left: 4px solid #ef4444;
            font-family: monospace; font-size: .85rem; }
  .exemples { background: #0f172a; padding: 16px;
              border-radius: 12px; margin-bottom: 16px; }
  .exemples h4 { color: #f39c12; font-size: .85rem;
                 margin-bottom: 10px; }
  .exemples code { display: block; background: #1e293b;
                   color: #94a3b8; padding: 8px 12px;
                   border-radius: 6px; margin-bottom: 6px;
                   font-size: .8rem; cursor: pointer; }
  .exemples code:hover { color: #f39c12; background: #1a2332; }
</style></head><body>
<div class="container">
  <div class="topbar">
    <h1>🔎 Requête SQL</h1>
    <a href="/admin/database" class="btn">← Base de données</a>
  </div>

  <div class="info">
    <b>⚠️ Sécurité :</b> Seules les requêtes <code>SELECT</code> sont autorisées.
    Limite : 100 résultats.
  </div>

  <div class="exemples">
    <h4>💡 Exemples :</h4>
    <code onclick="document.getElementById('req').value=this.textContent;">
      SELECT * FROM users ORDER BY created_at DESC
    </code>
    <code onclick="document.getElementById('req').value=this.textContent;">
      SELECT COUNT(*) as total, premium FROM users GROUP BY premium
    </code>
    <code onclick="document.getElementById('req').value=this.textContent;">
      SELECT u.nom, COUNT(c.id) as nb_cv FROM users u LEFT JOIN cvs c ON c.user_id = u.id GROUP BY u.id
    </code>
  </div>

  <form method="post">
    <textarea id="req" name="requete" placeholder="SELECT * FROM users LIMIT 10">{{ requete }}</textarea>
    <div class="actions">
      <button type="submit" class="btn-primary">▶ Exécuter</button>
      <a href="/admin/database/query" class="btn" style="background:#334155;">Effacer</a>
    </div>
  </form>

  {% if erreur %}<div class="erreur">{{ erreur }}</div>{% endif %}

  {% if resultat %}
    <div class="resultat">
      <h3>📊 Résultat — {{ resultat.count }} ligne(s)</h3>
      <div style="overflow-x:auto;">
        <table>
          <thead><tr>
            {% for col in resultat.colonnes %}<th>{{ col }}</th>{% endfor %}
          </tr></thead>
          <tbody>
            {% for ligne in resultat.lignes %}
              <tr>
                {% for col in resultat.colonnes %}<td>{{ ligne[col] }}</td>{% endfor %}
              </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
  {% endif %}
</div>
</body></html>
'''