"""
Admin — Dashboard, statistiques, maintenance.
"""
import os
import csv
import json
import subprocess
import sys
from io import StringIO
from datetime import datetime
from functools import wraps

from flask import (Blueprint, render_template_string, request, redirect,
                   url_for, flash, session, jsonify, send_file, Response)
from flask_login import current_user

from config import Config
from extensions import db
from models import User, CV
from stats_utils import (lire_stats, ecrire_stats, stats_periode,
                         stats_resume, get_stats_temps_reel)

admin_bp = Blueprint('admin', __name__)


# ==================== DÉCORATEUR ====================
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_connecte'):
            return redirect(url_for('admin.admin_login'))
        return f(*args, **kwargs)
    return decorated


# ==================== LOGIN / LOGOUT ====================
@admin_bp.route('/admin', methods=['GET', 'POST'], strict_slashes=False)
@admin_bp.route('/admin/login', methods=['GET', 'POST'], strict_slashes=False)
def admin_login():
    if session.get('admin_connecte'):
        return redirect(url_for('admin.admin_stats'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == Config.ADMIN_PASSWORD:
            session['admin_connecte'] = True
            flash('Connexion admin réussie.', 'success')
            return redirect(url_for('admin.admin_stats'))
        flash('Mot de passe incorrect.', 'error')

    return render_template_string(LOGIN_HTML)


@admin_bp.route('/admin/logout', strict_slashes=False)
def admin_logout():
    session.pop('admin_connecte', None)
    flash('Déconnecté de l\'admin.', 'success')
    return redirect(url_for('admin.admin_login'))


# ==================== DASHBOARD ====================
@admin_bp.route('/admin/stats', strict_slashes=False)
@admin_required
def admin_stats():
    stats = lire_stats()
    nb_users = User.query.count()
    nb_premium = User.query.filter_by(premium=True).count()
    nb_gratuits = nb_users - nb_premium
    nb_cv_sauvegardes = CV.query.count()

    revenus = stats.get('revenus_total', 0)

    aujourdhui = datetime.utcnow().date()
    users_aujourd_hui = User.query.filter(
        db.func.date(User.created_at) == aujourdhui
    ).count()

    debut_mois = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
    users_ce_mois = User.query.filter(User.created_at >= debut_mois).count()

    resume = stats_resume()
    historique = stats_periode(30)
    max_visites = max((h['visites'] for h in historique), default=1) or 1

    modeles_top = sorted(
        stats.get('modeles_utilises', {}).items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    derniers_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    derniers_premium = (User.query
                        .filter_by(premium=True)
                        .order_by(User.premium_date.desc())
                        .limit(5).all())

    def fmt_date(d):
        return d.strftime('%d/%m/%Y %H:%M') if d else '—'

    lignes_users = ''
    for u in derniers_users:
        badge = '👑' if u.premium else '👤'
        couleur = '#f59e0b' if u.premium else '#64748b'
        lignes_users += f'''
        <tr>
          <td>{badge}</td>
          <td><b>{u.nom}</b></td>
          <td>{u.email}</td>
          <td>{fmt_date(u.created_at)}</td>
          <td style="color:{couleur};font-weight:600;">{'Premium' if u.premium else 'Gratuit'}</td>
        </tr>'''

    lignes_premium = ''
    for u in derniers_premium:
        lignes_premium += f'''
        <tr>
          <td>👑</td>
          <td><b>{u.nom}</b></td>
          <td>{u.email}</td>
          <td>{fmt_date(u.premium_date)}</td>
        </tr>'''

    barres = ''
    for h in historique:
        hauteur = int((h['visites'] / max_visites) * 100) if max_visites > 0 else 0
        if hauteur == 0 and h['visites'] > 0:
            hauteur = 4
        tooltip = f"{h['jour']} : {h['visites']} visites, {h['inscriptions']} inscrits"
        barres += f'''
          <div class="barre-jour" title="{tooltip}">
            <div class="barre-visites" style="height: {hauteur}%;"></div>
          </div>'''

    lignes_modeles = ''
    for modele_id, count in modeles_top:
        lignes_modeles += f'''
        <tr>
          <td><b>{modele_id}</b></td>
          <td style="text-align:right; color:#f39c12; font-weight:700;">{count}</td>
        </tr>'''

    return render_template_string(
        DASHBOARD_HTML,
        stats=stats,
        nb_users=nb_users,
        nb_premium=nb_premium,
        nb_gratuits=nb_gratuits,
        nb_cv_sauvegardes=nb_cv_sauvegardes,
        revenus=revenus,
        users_aujourd_hui=users_aujourd_hui,
        users_ce_mois=users_ce_mois,
        resume=resume,
        historique=historique,
        barres=barres,
        lignes_users=lignes_users,
        lignes_premium=lignes_premium,
        lignes_modeles=lignes_modeles,
        maintenant=datetime.now(),
    )


# ==================== API STATS LIVE ====================
@admin_bp.route('/admin/api/stats-live', strict_slashes=False)
@admin_required
def admin_api_stats_live():
    stats = get_stats_temps_reel()
    stats['nb_users'] = User.query.count()
    stats['nb_premium'] = User.query.filter_by(premium=True).count()
    stats['nb_cv_sauvegardes'] = CV.query.count()
    return jsonify(stats)


# ==================== RESET ====================
@admin_bp.route('/admin/stats/reset', strict_slashes=False)
@admin_required
def admin_stats_reset():
    ecrire_stats({
        "visites": 0,
        "telechargements": 0,
        "telechargements_lettres": 0,
        "inscriptions": 0,
        "premium_achats": 0,
        "revenus_total": 0.0,
        "historique": {},
        "modeles_utilises": {},
    })
    flash('Compteurs réinitialisés.', 'success')
    return redirect(url_for('admin.admin_stats'))


# ==================== UTILISATEURS ====================
@admin_bp.route('/admin/users', strict_slashes=False)
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()

    lignes = ''
    for u in users:
        badge = '👑' if u.premium else '👤'
        couleur = '#f59e0b' if u.premium else '#64748b'
        date_insc = u.created_at.strftime('%d/%m/%Y') if u.created_at else '—'
        date_prem = u.premium_date.strftime('%d/%m/%Y') if u.premium_date else '—'
        nb_cvs = CV.query.filter_by(user_id=u.id).count()
        lignes += f'''
        <tr>
          <td>{badge}</td>
          <td><b>{u.nom}</b></td>
          <td>{u.email}</td>
          <td>{u.telephone or '—'}</td>
          <td>{date_insc}</td>
          <td style="color:{couleur};font-weight:600;">{'Premium' if u.premium else 'Gratuit'}</td>
          <td>{date_prem}</td>
          <td style="text-align:center;">{nb_cvs}</td>
        </tr>'''

    return render_template_string(USERS_HTML, lignes=lignes, total=len(users))


# ==================== EXPORT CSV ====================
@admin_bp.route('/admin/export', strict_slashes=False)
@admin_required
def admin_export():
    users = User.query.order_by(User.created_at.desc()).all()

    def gen():
        data = StringIO()
        writer = csv.writer(data, delimiter=';')
        writer.writerow(['ID', 'Nom', 'Email', 'Telephone', 'Premium',
                         'Premium_date', 'Inscription', 'Nb_CV'])
        yield data.getvalue()
        data.seek(0); data.truncate(0)

        for u in users:
            nb_cvs = CV.query.filter_by(user_id=u.id).count()
            writer.writerow([
                u.id, u.nom, u.email, u.telephone or '',
                'Oui' if u.premium else 'Non',
                u.premium_date.strftime('%Y-%m-%d') if u.premium_date else '',
                u.created_at.strftime('%Y-%m-%d') if u.created_at else '',
                nb_cvs,
            ])
            yield data.getvalue()
            data.seek(0); data.truncate(0)

    fichier = f'cvpro_utilisateurs_{datetime.now().strftime("%Y-%m-%d")}.csv'
    return Response(gen(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename={fichier}'})


# ==================== EXPORT STATS JSON ====================
@admin_bp.route('/admin/export-stats', strict_slashes=False)
@admin_required
def admin_export_stats():
    stats = lire_stats()
    return Response(
        json.dumps(stats, ensure_ascii=False, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename=cvpro_stats_{datetime.now().strftime("%Y-%m-%d")}.json'}
    )


# ==================== BACKUP DB ====================
@admin_bp.route('/admin/backup', strict_slashes=False)
@admin_required
def admin_backup():
    possible = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'cvpro.db'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cvpro.db'),
    ]
    db_path = next((p for p in possible if os.path.exists(p)), None)
    if not db_path:
        return "❌ Base de données introuvable", 404

    nom_backup = f'cvpro_backup_{datetime.now().strftime("%Y-%m-%d_%H-%M")}.db'
    return send_file(db_path, as_attachment=True, download_name=nom_backup)


# ==================== CORRIGER TEMPLATES ====================
@admin_bp.route('/admin/corriger', methods=['GET', 'POST'], strict_slashes=False)
@admin_required
def admin_corriger():
    racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script_path = os.path.join(racine, 'corriger_modeles.py')

    if not os.path.exists(script_path):
        return f"❌ Script introuvable : {script_path}", 404

    try:
        result = subprocess.run([sys.executable, script_path],
                                capture_output=True, text=True,
                                encoding='utf-8', timeout=30, cwd=racine)
        stdout = result.stdout or "(aucune sortie)"

        def esc(s):
            return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        return render_template_string(CORRIGER_HTML, output=esc(stdout))
    except subprocess.TimeoutExpired:
        return "⏱ Timeout", 504
    except Exception as e:
        return f"❌ Erreur : {e}", 500


# ================================================================
# TEMPLATES HTML
# ================================================================

LOGIN_HTML = '''
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<title>Admin — CVPro</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: 'Segoe UI', Arial, sans-serif;
         background: linear-gradient(135deg, #1e2a3a, #0f172a);
         color: #fff; display: grid; place-items: center;
         min-height: 100vh; padding: 20px; }
  .box { background: #fff; color: #2c3e50;
         border-radius: 20px; padding: 45px 40px;
         max-width: 420px; width: 100%; text-align: center;
         box-shadow: 0 30px 80px rgba(0,0,0,.4); }
  .ico { font-size: 3rem; margin-bottom: 12px; }
  h1 { color: #2c3e50; margin-bottom: 8px; }
  p { color: #64748b; margin-bottom: 24px; font-size: .9rem; }
  input { width: 100%; padding: 14px; border: 1px solid #cbd5e1;
          border-radius: 10px; font-family: inherit; font-size: 1rem;
          margin-bottom: 14px; text-align: center; letter-spacing: 2px; }
  input:focus { outline: none; border-color: #f39c12;
                box-shadow: 0 0 0 3px rgba(243,156,18,.15); }
  button { width: 100%; padding: 14px; background: #f39c12;
           color: #fff; border: none; border-radius: 10px;
           font-size: 1rem; font-weight: 700; cursor: pointer;
           font-family: inherit; transition: all .2s; }
  button:hover { background: #e67e22; transform: translateY(-2px); }
  .flash { padding: 10px; background: #fee2e2; color: #991b1b;
           border-radius: 8px; margin-bottom: 14px; font-size: .85rem; }
  a { color: #f39c12; text-decoration: none; font-size: .85rem;
      display: inline-block; margin-top: 12px; }
</style></head><body>
  <div class="box">
    <div class="ico">🔐</div>
    <h1>Administration</h1>
    <p>Accès réservé à l'administrateur</p>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for m in messages %}<div class="flash">{{ m }}</div>{% endfor %}
      {% endif %}
    {% endwith %}
    <form method="post">
      <input type="password" name="password" placeholder="Mot de passe"
             required autofocus/>
      <button type="submit">Se connecter</button>
    </form>
    <a href="/">← Retour au site</a>
  </div>
</body></html>
'''


DASHBOARD_HTML = '''
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Admin — CVPro</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: 'Segoe UI', Arial, sans-serif;
         background: #0f172a; color: #e2e8f0;
         min-height: 100vh; padding: 30px 20px; }
  .container { max-width: 1400px; margin: 0 auto; }

  /* TOPBAR */
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
  .btn-or:hover { background: #e67e22; }
  .btn-ghost { background: transparent; color: #94a3b8;
               border: 1px solid #334155; }
  .btn-ghost:hover { border-color: #f39c12; color: #f39c12; }
  .btn-danger { background: #ef4444; color: #fff; }
  .btn-danger:hover { background: #dc2626; }

  /* WIDGET LIVE */
  .widget-live { background: linear-gradient(135deg, #0f172a, #1e293b);
                 border: 1px solid #334155; border-radius: 16px;
                 padding: 20px; margin-bottom: 24px;
                 position: relative; overflow: hidden; }
  .widget-live::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #22c55e, #16a34a, #22c55e);
    background-size: 200% 100%;
    animation: slide 2s linear infinite;
  }
  @keyframes slide {
    0% { background-position: 0% 0; }
    100% { background-position: 200% 0; }
  }
  .widget-header {
    display: flex; align-items: center; gap: 10px;
    margin-bottom: 16px; font-size: .9rem;
    color: #94a3b8;
  }
  .widget-header b { color: #e2e8f0; }
  .widget-dot {
    width: 10px; height: 10px; border-radius: 50%;
    background: #22c55e;
    box-shadow: 0 0 0 0 rgba(34,197,94,.7);
    animation: pulse-dot 1.5s infinite;
  }
  @keyframes pulse-dot {
    0% { box-shadow: 0 0 0 0 rgba(34,197,94,.7); }
    70% { box-shadow: 0 0 0 10px rgba(34,197,94,0); }
    100% { box-shadow: 0 0 0 0 rgba(34,197,94,0); }
  }
  .widget-grille {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 14px;
  }
  .widget-item {
    display: flex; flex-direction: column;
    align-items: center; text-align: center;
    padding: 12px;
    background: rgba(15,23,42,.6);
    border-radius: 12px;
    border: 1px solid #1e293b;
    transition: all .2s;
  }
  .widget-item:hover {
    border-color: #f39c12;
    transform: translateY(-2px);
  }
  .w-ico { font-size: 1.4rem; margin-bottom: 4px; }
  .w-val {
    font-size: 1.5rem; font-weight: 800;
    color: #f39c12; line-height: 1;
    font-variant-numeric: tabular-nums;
    transition: color .3s;
  }
  .w-val.updated { color: #22c55e; }
  .w-lbl {
    font-size: .7rem; color: #94a3b8;
    text-transform: uppercase; letter-spacing: 1px;
    margin-top: 4px; font-weight: 600;
  }

  /* GRILLE STATS */
  .grille { display: grid;
            grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
            gap: 16px; margin-bottom: 26px; }
  .stat { background: #1e293b; border: 1px solid #334155;
          border-radius: 16px; padding: 20px; position: relative;
          overflow: hidden; transition: all .3s; }
  .stat:hover { transform: translateY(-3px); border-color: #f39c12;
                box-shadow: 0 15px 40px rgba(243,156,18,.15); }
  .stat::before { content: ''; position: absolute;
                  top: 0; left: 0; right: 0; height: 3px;
                  background: linear-gradient(90deg, #f39c12, #e67e22); }
  .stat .ico { font-size: 1.6rem; margin-bottom: 8px; display: block; }
  .stat .val { font-size: 1.9rem; font-weight: 800; color: #f39c12;
               line-height: 1; margin-bottom: 6px;
               font-variant-numeric: tabular-nums; }
  .stat .lbl { font-size: .7rem; color: #94a3b8;
               text-transform: uppercase; letter-spacing: 1px;
               font-weight: 600; }
  .stat .sub { font-size: .72rem; color: #64748b; margin-top: 5px; }

  /* SECTION */
  .section { background: #1e293b; border: 1px solid #334155;
             border-radius: 16px; padding: 22px; margin-bottom: 22px; }
  .section h2 { color: #f39c12; font-size: 1.1rem;
                margin-bottom: 16px; display: flex;
                align-items: center; gap: 10px; }
  .section h2 .count { background: #0f172a; color: #f39c12;
                       padding: 3px 12px; border-radius: 12px;
                       font-size: .75rem; }

  /* TABLEAU */
  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; color: #94a3b8; font-size: .7rem;
       text-transform: uppercase; letter-spacing: 1px;
       padding: 10px 12px; border-bottom: 1px solid #334155;
       font-weight: 600; }
  td { padding: 11px 12px; border-bottom: 1px solid #1e293b;
       font-size: .86rem; color: #e2e8f0; }
  tr:hover td { background: #0f172a; }
  .vide { text-align: center; color: #64748b;
          padding: 25px; font-style: italic; font-size: .85rem; }

  /* GRAPHIQUE */
  .graphique { display: flex; align-items: flex-end;
               justify-content: space-between;
               height: 180px; gap: 3px;
               padding: 15px 0; overflow-x: auto; }
  .barre-jour { flex: 1; min-width: 10px;
                display: flex; flex-direction: column;
                justify-content: flex-end;
                height: 100%; cursor: pointer;
                position: relative; }
  .barre-visites { background: linear-gradient(180deg, #f39c12, #e67e22);
                   border-radius: 3px 3px 0 0;
                   transition: all .2s;
                   min-height: 2px; }
  .barre-jour:hover .barre-visites {
    background: linear-gradient(180deg, #fbbf24, #f39c12);
    transform: scaleY(1.05);
  }
  .legende { display: flex; justify-content: space-between;
             color: #64748b; font-size: .7rem;
             margin-top: 8px; }

  /* RÉSUMÉ PÉRIODES */
  .grille-periodes { display: grid;
                     grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                     gap: 14px; }
  .periode { background: #0f172a; border-radius: 12px;
             padding: 16px; border-left: 3px solid #f39c12; }
  .periode h4 { color: #94a3b8; font-size: .72rem;
                text-transform: uppercase; letter-spacing: 1px;
                margin-bottom: 10px; font-weight: 600; }
  .periode-ligne { display: flex; justify-content: space-between;
                   font-size: .82rem; padding: 4px 0;
                   color: #cbd5e1; }
  .periode-ligne b { color: #f39c12; }

  /* ACTIONS MAINTENANCE */
  .actions-grille { display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                    gap: 12px; }
  .action-btn { background: #0f172a; border: 1px solid #334155;
                border-radius: 12px; padding: 16px;
                text-decoration: none; color: #e2e8f0;
                font-weight: 600; font-size: .85rem;
                text-align: center; transition: all .2s;
                display: block; }
  .action-btn:hover { border-color: #f39c12;
                      background: #1e293b;
                      transform: translateY(-2px); }
  .action-btn .ico { font-size: 1.5rem; display: block;
                     margin-bottom: 6px; }

  @media (max-width: 700px) {
    h1 { font-size: 1.5rem; }
    .grille { grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }
    .stat .val { font-size: 1.5rem; }
    table { font-size: .78rem; }
    th, td { padding: 8px 6px; }
  }
</style></head><body>
<div class="container">
  <div class="topbar">
    <div>
      <h1>📊 Tableau de bord CVPro</h1>
      <p class="date">🕐 {{ maintenant.strftime('%d/%m/%Y à %H:%M') }}</p>
    </div>
    <div class="actions-top">
      <a href="/" class="btn btn-or">← Site</a>
      <a href="/admin/users" class="btn btn-ghost">👥 Utilisateurs</a>
      <a href="/admin/export" class="btn btn-ghost">📥 CSV</a>
      <a href="/admin/backup" class="btn btn-ghost">💾 Backup</a>
      <a href="/admin/logout" class="btn btn-danger">🚪</a>
    </div>
  </div>

  <!-- WIDGET LIVE -->
  <div class="widget-live">
    <div class="widget-header">
      <span class="widget-dot"></span>
      <b>En direct</b>
      <span id="widget-time" style="margin-left:auto;color:#64748b;font-size:.8rem;"></span>
    </div>
    <div class="widget-grille">
      <div class="widget-item">
        <span class="w-ico">🟢</span>
        <span class="w-val" id="live-visiteurs">—</span>
        <span class="w-lbl">en ligne</span>
      </div>
      <div class="widget-item">
        <span class="w-ico">👥</span>
        <span class="w-val" id="live-visites">—</span>
        <span class="w-lbl">visites</span>
      </div>
      <div class="widget-item">
        <span class="w-ico">⬇️</span>
        <span class="w-val" id="live-cv">—</span>
        <span class="w-lbl">CV</span>
      </div>
      <div class="widget-item">
        <span class="w-ico">✉️</span>
        <span class="w-val" id="live-lettres">—</span>
        <span class="w-lbl">lettres</span>
      </div>
      <div class="widget-item">
        <span class="w-ico">👤</span>
        <span class="w-val" id="live-users">—</span>
        <span class="w-lbl">comptes</span>
      </div>
      <div class="widget-item">
        <span class="w-ico">👑</span>
        <span class="w-val" id="live-premium">—</span>
        <span class="w-lbl">premium</span>
      </div>
      <div class="widget-item">
        <span class="w-ico">💰</span>
        <span class="w-val" id="live-revenus">—</span>
        <span class="w-lbl">€</span>
      </div>
      <div class="widget-item">
        <span class="w-ico">📂</span>
        <span class="w-val" id="live-cv-base">—</span>
        <span class="w-lbl">CV base</span>
      </div>
    </div>
  </div>

  <!-- COMPTEURS GLOBAUX -->
  <div class="grille">
    <div class="stat">
      <span class="ico">👥</span>
      <div class="val">{{ stats.visites }}</div>
      <div class="lbl">Visiteurs</div>
      <div class="sub">Total cumulé</div>
    </div>
    <div class="stat">
      <span class="ico">⬇️</span>
      <div class="val">{{ stats.telechargements }}</div>
      <div class="lbl">CV téléchargés</div>
    </div>
    <div class="stat">
      <span class="ico">✉️</span>
      <div class="val">{{ stats.telechargements_lettres }}</div>
      <div class="lbl">Lettres téléchargées</div>
    </div>
    <div class="stat">
      <span class="ico">👤</span>
      <div class="val">{{ nb_users }}</div>
      <div class="lbl">Comptes</div>
      <div class="sub">{{ nb_gratuits }} gratuits · {{ nb_premium }} premium</div>
    </div>
    <div class="stat">
      <span class="ico">👑</span>
      <div class="val">{{ nb_premium }}</div>
      <div class="lbl">Clients Premium</div>
    </div>
    <div class="stat">
      <span class="ico">💰</span>
      <div class="val">{{ '%.2f'|format(revenus) }} €</div>
      <div class="lbl">Revenus totaux</div>
    </div>
    <div class="stat">
      <span class="ico">📂</span>
      <div class="val">{{ nb_cv_sauvegardes }}</div>
      <div class="lbl">CV en base</div>
    </div>
    <div class="stat">
      <span class="ico">📅</span>
      <div class="val">{{ users_aujourd_hui }}</div>
      <div class="lbl">Inscrits aujourd'hui</div>
    </div>
    <div class="stat">
      <span class="ico">📆</span>
      <div class="val">{{ users_ce_mois }}</div>
      <div class="lbl">Inscrits ce mois</div>
    </div>
  </div>

  <!-- RÉSUMÉ PAR PÉRIODE -->
  <div class="section">
    <h2>📈 Statistiques par période</h2>
    <div class="grille-periodes">
      <div class="periode">
        <h4>Aujourd'hui</h4>
        <div class="periode-ligne"><span>Visites</span><b>{{ resume.aujourd_hui.visites }}</b></div>
        <div class="periode-ligne"><span>CV</span><b>{{ resume.aujourd_hui.cv }}</b></div>
        <div class="periode-ligne"><span>Lettres</span><b>{{ resume.aujourd_hui.lettres }}</b></div>
        <div class="periode-ligne"><span>Inscrits</span><b>{{ resume.aujourd_hui.inscriptions }}</b></div>
      </div>
      <div class="periode">
        <h4>Hier</h4>
        <div class="periode-ligne"><span>Visites</span><b>{{ resume.hier.visites }}</b></div>
        <div class="periode-ligne"><span>CV</span><b>{{ resume.hier.cv }}</b></div>
        <div class="periode-ligne"><span>Lettres</span><b>{{ resume.hier.lettres }}</b></div>
        <div class="periode-ligne"><span>Inscrits</span><b>{{ resume.hier.inscriptions }}</b></div>
      </div>
      <div class="periode">
        <h4>7 derniers jours</h4>
        <div class="periode-ligne"><span>Visites</span><b>{{ resume.semaine.visites }}</b></div>
        <div class="periode-ligne"><span>CV</span><b>{{ resume.semaine.cv }}</b></div>
        <div class="periode-ligne"><span>Lettres</span><b>{{ resume.semaine.lettres }}</b></div>
        <div class="periode-ligne"><span>Inscrits</span><b>{{ resume.semaine.inscriptions }}</b></div>
      </div>
      <div class="periode">
        <h4>30 derniers jours</h4>
        <div class="periode-ligne"><span>Visites</span><b>{{ resume.mois.visites }}</b></div>
        <div class="periode-ligne"><span>CV</span><b>{{ resume.mois.cv }}</b></div>
        <div class="periode-ligne"><span>Lettres</span><b>{{ resume.mois.lettres }}</b></div>
        <div class="periode-ligne"><span>Inscrits</span><b>{{ resume.mois.inscriptions }}</b></div>
      </div>
    </div>
  </div>

  <!-- GRAPHIQUE 30 JOURS -->
  <div class="section">
    <h2>📊 Visites des 30 derniers jours</h2>
    <div class="graphique">
      {{ barres|safe }}
    </div>
    <div class="legende">
      <span>Il y a 30 jours</span>
      <span>Aujourd'hui</span>
    </div>
  </div>

  <!-- TOP MODÈLES -->
  <div class="section">
    <h2>🎨 Modèles les plus utilisés</h2>
    {% if lignes_modeles %}
      <table>
        <thead><tr><th>Modèle</th><th style="text-align:right;">Utilisations</th></tr></thead>
        <tbody>{{ lignes_modeles|safe }}</tbody>
      </table>
    {% else %}
      <p class="vide">Aucune utilisation enregistrée</p>
    {% endif %}
  </div>

  <!-- DERNIERS UTILISATEURS -->
  <div class="section">
    <h2>🆕 Derniers inscrits <span class="count">10</span></h2>
    <table>
      <thead><tr>
        <th></th><th>Nom</th><th>Email</th>
        <th>Inscription</th><th>Statut</th>
      </tr></thead>
      <tbody>
        {{ lignes_users|safe if lignes_users else '<tr><td colspan="5" class="vide">Aucun utilisateur</td></tr>'|safe }}
      </tbody>
    </table>
  </div>

  <!-- DERNIERS PREMIUM -->
  <div class="section">
    <h2>👑 Derniers clients Premium</h2>
    <table>
      <thead><tr><th></th><th>Nom</th><th>Email</th><th>Premium depuis</th></tr></thead>
      <tbody>
        {{ lignes_premium|safe if lignes_premium else '<tr><td colspan="4" class="vide">Aucun client Premium</td></tr>'|safe }}
      </tbody>
    </table>
  </div>

  <!-- MAINTENANCE -->
  <div class="section">
    <h2>🔧 Maintenance</h2>
    <div class="actions-grille">
      <a href="/admin/database" class="action-btn">
        <span class="ico">🗄️</span>Base de données
      </a>
      <a href="/admin/corriger" class="action-btn">
        <span class="ico">🔧</span>Corriger les templates
      </a>
      <a href="/admin/export" class="action-btn">
        <span class="ico">📥</span>Export utilisateurs CSV
      </a>
      <a href="/admin/export-stats" class="action-btn">
        <span class="ico">📊</span>Export statistiques JSON
      </a>
      <a href="/admin/backup" class="action-btn">
        <span class="ico">💾</span>Télécharger la base
      </a>
      <a href="/admin/stats/reset" class="action-btn"
         onclick="return confirm('⚠️ Remettre TOUS les compteurs à zéro ?\\n\\nCette action est IRRÉVERSIBLE.')">
        <span class="ico">🗑</span>Réinitialiser les compteurs
      </a>
    </div>
  </div>

  <p style="text-align:center;color:#475569;font-size:.78rem;margin-top:30px;">
    🔒 Espace administrateur · CVPro · {{ maintenant.year }}
  </p>
</div>

<script>
// ==================== WIDGET LIVE ====================
let dernieresValeurs = {};

function majValeur(id, nouvelleValeur) {
  const el = document.getElementById(id);
  if (!el) return;

  const ancienne = dernieresValeurs[id];

  if (ancienne !== undefined && ancienne !== nouvelleValeur) {
    el.classList.add('updated');
    setTimeout(() => el.classList.remove('updated'), 1000);
  }

  el.textContent = nouvelleValeur;
  dernieresValeurs[id] = nouvelleValeur;
}

async function refreshStatsLive() {
  try {
    const res = await fetch('/admin/api/stats-live');
    const json = await res.json();

    majValeur('live-visiteurs', json.visiteurs_en_ligne);
    majValeur('live-visites', json.visites);
    majValeur('live-cv', json.telechargements);
    majValeur('live-lettres', json.telechargements_lettres);
    majValeur('live-users', json.nb_users);
    majValeur('live-premium', json.nb_premium);
    majValeur('live-revenus', json.revenus_total.toFixed(2));
    majValeur('live-cv-base', json.nb_cv_sauvegardes);

    const d = new Date(json.timestamp);
    document.getElementById('widget-time').textContent =
      'Mis à jour ' + d.toLocaleTimeString('fr-FR');
  } catch (e) {
    console.error('Erreur live stats', e);
  }
}

refreshStatsLive();
setInterval(refreshStatsLive, 5000);
</script>
</body></html>
'''


USERS_HTML = '''
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<title>Tous les utilisateurs — CVPro</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: 'Segoe UI', Arial, sans-serif;
         background: #0f172a; color: #e2e8f0; padding: 30px 20px; }
  .container { max-width: 1400px; margin: 0 auto; }
  h1 { color: #f39c12; margin-bottom: 10px; }
  .sub { color: #94a3b8; margin-bottom: 24px; font-size: .9rem; }
  .topbar { display: flex; justify-content: space-between;
            align-items: center; margin-bottom: 20px;
            flex-wrap: wrap; gap: 12px; }
  .btn { padding: 10px 18px; border-radius: 10px;
         text-decoration: none; font-weight: 600; font-size: .85rem;
         background: #f39c12; color: #fff; }
  table { width: 100%; background: #1e293b; border-radius: 14px;
          overflow: hidden; border-collapse: collapse; }
  th { text-align: left; color: #94a3b8; font-size: .7rem;
       text-transform: uppercase; letter-spacing: 1px;
       padding: 14px 16px; background: #0f172a; font-weight: 600; }
  td { padding: 12px 16px; border-top: 1px solid #334155; font-size: .85rem; }
  tr:hover td { background: #0f172a; }
</style></head><body>
<div class="container">
  <div class="topbar">
    <div>
      <h1>👥 Tous les utilisateurs</h1>
      <p class="sub">{{ total }} comptes au total</p>
    </div>
    <a href="/admin/stats" class="btn">← Tableau de bord</a>
  </div>
  <table><thead><tr>
    <th></th><th>Nom</th><th>Email</th><th>Téléphone</th>
    <th>Inscription</th><th>Statut</th><th>Premium depuis</th><th>CV</th>
  </tr></thead><tbody>
    {{ lignes|safe if lignes else '<tr><td colspan="8" style="text-align:center;padding:30px;color:#64748b;">Aucun utilisateur</td></tr>'|safe }}
  </tbody></table>
</div></body></html>
'''


CORRIGER_HTML = '''
<!DOCTYPE html><html><head><meta charset="utf-8"><title>Correction</title>
<style>body{font-family:monospace;background:#0f172a;color:#e2e8f0;padding:30px}
.box{max-width:900px;margin:0 auto;background:#1e293b;padding:30px;border-radius:16px}
h1{color:#f39c12;font-family:sans-serif} pre{background:#0f172a;padding:20px;
border-radius:10px;overflow:auto;white-space:pre-wrap}
a{color:#f39c12;display:inline-block;margin-top:15px;text-decoration:none}</style>
</head><body>
<div class="box"><h1>🔧 Correction des templates</h1>
<pre>{{ output }}</pre>
<a href="/admin/stats">← Tableau de bord</a></div></body></html>
'''