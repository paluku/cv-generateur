# -*- coding: utf-8 -*-
"""
Module « Relevé d'heures » — blueprint Flask autonome.
======================================================
Intégration dans ton app.py existant :

    from releve_heures import releve_bp, init_releve_db
    init_releve_db()
    app.register_blueprint(releve_bp, url_prefix="/releve")

Templates attendus :
    - templates/releve_heures.html      (page principale / standalone)
    - templates/releve_heures_pdf.html  (vue imprimable PDF)

Base de données :
    releve_heures.db (fichier SQLite créé automatiquement,
    totalement indépendant de ta base existante)
"""

import csv
import io
import json
import os
import sqlite3
from datetime import datetime

from flask import (
    Blueprint, Response, g, jsonify, redirect,
    render_template, request,
)

# ============================================================
# CONFIGURATION
# ============================================================
DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "releve_heures.db",
)

VALID_STATUS = {"travail", "modifie", "absence", "conge"}

MOIS_NOMS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]

releve_bp = Blueprint("releve", __name__)


# ============================================================
# BASE DE DONNÉES
# ============================================================
def get_db():
    """Ouvre (ou récupère) la connexion SQLite attachée à la requête."""
    if "db_releve" not in g:
        g.db_releve = sqlite3.connect(DB_PATH)
        g.db_releve.row_factory = sqlite3.Row
    return g.db_releve


def init_releve_db():
    """Crée les tables si elles n'existent pas. À appeler au démarrage."""
    con = sqlite3.connect(DB_PATH)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            id                    INTEGER PRIMARY KEY CHECK (id = 1),
            duree_defaut_minutes  INTEGER NOT NULL DEFAULT 480,
            pause_defaut_minutes  INTEGER NOT NULL DEFAULT 60,
            heure_debut_defaut    TEXT    NOT NULL DEFAULT '08:00'
        );
        INSERT OR IGNORE INTO settings VALUES (1, 480, 60, '08:00');

        CREATE TABLE IF NOT EXISTS pointages (
            date          TEXT PRIMARY KEY,
            total_minutes INTEGER NOT NULL DEFAULT 0,
            heure_debut   TEXT    NOT NULL DEFAULT '08:00',
            heure_fin     TEXT    NOT NULL DEFAULT '17:00',
            pause_minutes INTEGER NOT NULL DEFAULT 60,
            statut        TEXT    NOT NULL DEFAULT 'travail',
            commentaire   TEXT    NOT NULL DEFAULT '',
            updated_at    TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_pointages_date
            ON pointages(date);
    """)
    con.commit()
    con.close()


# ============================================================
# HELPERS
# ============================================================
def _row(r):
    """Convertit une sqlite3.Row en dict JSON-friendly."""
    return {k: r[k] for k in r.keys()}


def _fmt_minutes(m):
    """480 -> '8h' ; 485 -> '8h05'."""
    h, mm = divmod(int(m), 60)
    return f"{h}h{mm:02d}" if mm else f"{h}h"


def _int_safe(value, default=0):
    """Cast int tolérant."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ============================================================
# VUES
# ============================================================
@releve_bp.route("/")
def index():
    """
    Si ta page principale (index.html) intègre déjà la section #releve,
    on redirige vers /#releve pour rester sur le site principal.
    """
    return redirect("/#releve")


@releve_bp.route("/standalone")
def standalone():
    """Page complète autonome (debug ou usage isolé)."""
    now = datetime.now()
    return render_template(
        "releve_heures.html",
        annee=now.year,
        mois=now.month,
    )


# ============================================================
# API — RÉGLAGES
# ============================================================
@releve_bp.get("/api/settings")
def api_get_settings():
    r = get_db().execute("SELECT * FROM settings WHERE id=1").fetchone()
    return jsonify({
        "duree_defaut_minutes": r["duree_defaut_minutes"],
        "pause_defaut_minutes": r["pause_defaut_minutes"],
        "heure_debut_defaut":   r["heure_debut_defaut"],
    })


@releve_bp.put("/api/settings")
def api_put_settings():
    data = request.get_json(silent=True) or {}
    db   = get_db()
    cur  = db.execute("SELECT * FROM settings WHERE id=1").fetchone()

    duree = _int_safe(data.get("duree_defaut_minutes"),
                      cur["duree_defaut_minutes"])
    pause = _int_safe(data.get("pause_defaut_minutes"),
                      cur["pause_defaut_minutes"])
    debut = str(data.get("heure_debut_defaut") or cur["heure_debut_defaut"])

    # Bornes de sécurité
    duree = max(0, min(duree, 24 * 60))
    pause = max(0, min(pause, 12 * 60))

    db.execute(
        "UPDATE settings SET duree_defaut_minutes=?, "
        "pause_defaut_minutes=?, heure_debut_defaut=? WHERE id=1",
        (duree, pause, debut),
    )
    db.commit()
    return jsonify({
        "duree_defaut_minutes": duree,
        "pause_defaut_minutes": pause,
        "heure_debut_defaut":   debut,
    })


# ============================================================
# API — JOURS (pointages)
# ============================================================
@releve_bp.get("/api/days")
def api_list_days():
    month = request.args.get("month")  # format "YYYY-MM"
    db    = get_db()

    if month and len(month) == 7:
        rows = db.execute(
            "SELECT * FROM pointages WHERE date LIKE ? ORDER BY date",
            (month + "-%",),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM pointages ORDER BY date"
        ).fetchall()

    return jsonify([_row(r) for r in rows])


@releve_bp.post("/api/days")
def api_upsert_day():
    data = request.get_json(silent=True) or {}
    day  = str(data.get("date", "")).strip()

    if len(day) != 10:
        return jsonify({"error": "date invalide (attendu YYYY-MM-DD)"}), 400

    statut = data.get("statut", "travail")
    if statut not in VALID_STATUS:
        statut = "travail"

    total = max(0, _int_safe(data.get("total_minutes"), 0))
    pause = max(0, _int_safe(data.get("pause_minutes"), 0))

    db = get_db()
    db.execute("""
        INSERT INTO pointages
            (date, total_minutes, heure_debut, heure_fin,
             pause_minutes, statut, commentaire, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            total_minutes = excluded.total_minutes,
            heure_debut   = excluded.heure_debut,
            heure_fin     = excluded.heure_fin,
            pause_minutes = excluded.pause_minutes,
            statut        = excluded.statut,
            commentaire   = excluded.commentaire,
            updated_at    = excluded.updated_at
    """, (
        day,
        total,
        str(data.get("heure_debut") or "08:00"),
        str(data.get("heure_fin")   or "17:00"),
        pause,
        statut,
        str(data.get("commentaire") or "").strip()[:500],
        datetime.now().isoformat(timespec="seconds"),
    ))
    db.commit()

    r = db.execute(
        "SELECT * FROM pointages WHERE date=?", (day,)
    ).fetchone()
    return jsonify(_row(r)), 201


@releve_bp.delete("/api/days/<date>")
def api_delete_day(date):
    db = get_db()
    db.execute("DELETE FROM pointages WHERE date=?", (date,))
    db.commit()
    return jsonify({"deleted": date})


# ============================================================
# EXPORT PDF — page imprimable (Ctrl+P → Enregistrer en PDF)
# ============================================================
@releve_bp.route("/export/pdf/<int:annee>/<int:mois>")
def export_pdf(annee, mois):
    if not (1 <= mois <= 12):
        return "Mois invalide", 400

    db     = get_db()
    prefix = f"{annee}-{mois:02d}"
    rows   = db.execute(
        "SELECT * FROM pointages WHERE date LIKE ? ORDER BY date",
        (prefix + "-%",),
    ).fetchall()

    total_min = 0
    jours_travailles = absences = conges = 0

    for r in rows:
        if r["statut"] == "absence":
            absences += 1
        elif r["statut"] == "conge":
            conges += 1
        else:
            jours_travailles += 1
            total_min += r["total_minutes"]

    return render_template(
        "releve_heures_pdf.html",
        annee=annee,
        mois=mois,
        mois_nom=MOIS_NOMS[mois - 1],
        rows=rows,
        total_heures=_fmt_minutes(total_min),
        jours_travailles=jours_travailles,
        absences=absences,
        conges=conges,
        generated_at=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )


# ============================================================
# EXPORT CSV — pour Excel (séparateur ';' pour locale FR)
# ============================================================
@releve_bp.route("/export/csv/<int:annee>/<int:mois>")
def export_csv(annee, mois):
    if not (1 <= mois <= 12):
        return "Mois invalide", 400

    db     = get_db()
    prefix = f"{annee}-{mois:02d}"
    rows   = db.execute(
        "SELECT * FROM pointages WHERE date LIKE ? ORDER BY date",
        (prefix + "-%",),
    ).fetchall()

    buf = io.StringIO()
    buf.write("\ufeff")  # BOM UTF-8 pour Excel FR
    w = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    w.writerow([
        "Date", "Statut", "Début", "Fin",
        "Pause (min)", "Total (min)", "Total", "Commentaire",
    ])

    for r in rows:
        w.writerow([
            r["date"],
            r["statut"],
            r["heure_debut"],
            r["heure_fin"],
            r["pause_minutes"],
            r["total_minutes"],
            _fmt_minutes(r["total_minutes"]),
            r["commentaire"],
        ])

    return Response(
        buf.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition":
                f"attachment; filename=releve_{annee}_{mois:02d}.csv"
        },
    )


# ============================================================
# EXPORT JSON — sauvegarde complète (backup)
# ============================================================
@releve_bp.route("/export/json")
def export_json():
    db       = get_db()
    rows     = db.execute(
        "SELECT * FROM pointages ORDER BY date"
    ).fetchall()
    settings = db.execute(
        "SELECT * FROM settings WHERE id=1"
    ).fetchone()

    data = {
        "format":      "releve-heures-backup-v1",
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "settings":    dict(settings) if settings else {},
        "pointages":   [dict(r) for r in rows],
    }

    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={
            "Content-Disposition":
                "attachment; filename=releve_backup.json"
        },
    )


# ============================================================
# IMPORT JSON — restauration depuis une sauvegarde
# ============================================================
@releve_bp.post("/import/json")
def import_json():
    data = request.get_json(silent=True)
    if not data or "pointages" not in data:
        return jsonify({
            "error": "fichier invalide : clé 'pointages' manquante"
        }), 400

    db = get_db()
    nb = 0

    # Réglages (optionnels)
    if "settings" in data and isinstance(data["settings"], dict):
        s = data["settings"]
        db.execute(
            "UPDATE settings SET duree_defaut_minutes=?, "
            "pause_defaut_minutes=?, heure_debut_defaut=? WHERE id=1",
            (
                _int_safe(s.get("duree_defaut_minutes"), 480),
                _int_safe(s.get("pause_defaut_minutes"), 60),
                str(s.get("heure_debut_defaut") or "08:00"),
            ),
        )

    for p in data["pointages"]:
        if not isinstance(p, dict) or len(str(p.get("date", ""))) != 10:
            continue

        statut = p.get("statut", "travail")
        if statut not in VALID_STATUS:
            statut = "travail"

        db.execute("""
            INSERT INTO pointages
                (date, total_minutes, heure_debut, heure_fin,
                 pause_minutes, statut, commentaire, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                total_minutes = excluded.total_minutes,
                heure_debut   = excluded.heure_debut,
                heure_fin     = excluded.heure_fin,
                pause_minutes = excluded.pause_minutes,
                statut        = excluded.statut,
                commentaire   = excluded.commentaire,
                updated_at    = excluded.updated_at
        """, (
            p["date"],
            max(0, _int_safe(p.get("total_minutes"), 0)),
            str(p.get("heure_debut") or "08:00"),
            str(p.get("heure_fin")   or "17:00"),
            max(0, _int_safe(p.get("pause_minutes"), 0)),
            statut,
            str(p.get("commentaire") or "").strip()[:500],
            str(p.get("updated_at")
                or datetime.now().isoformat(timespec="seconds")),
        ))
        nb += 1

    db.commit()
    return jsonify({"imported": nb})


# ============================================================
# STATISTIQUES (bonus — API JSON pour tableau de bord)
# ============================================================
@releve_bp.get("/api/stats/<int:annee>/<int:mois>")
def api_stats(annee, mois):
    if not (1 <= mois <= 12):
        return jsonify({"error": "mois invalide"}), 400

    db     = get_db()
    prefix = f"{annee}-{mois:02d}"
    rows   = db.execute(
        "SELECT * FROM pointages WHERE date LIKE ? ORDER BY date",
        (prefix + "-%",),
    ).fetchall()

    total = 0
    jours = absences = conges = modifie = 0

    for r in rows:
        if r["statut"] == "absence":
            absences += 1
        elif r["statut"] == "conge":
            conges += 1
        elif r["statut"] == "modifie":
            modifie += 1
            jours += 1
            total += r["total_minutes"]
        else:
            jours += 1
            total += r["total_minutes"]

    return jsonify({
        "annee": annee,
        "mois": mois,
        "total_minutes": total,
        "total_heures": _fmt_minutes(total),
        "jours_travailles": jours,
        "jours_modifies": modifie,
        "absences": absences,
        "conges": conges,
    })


# ============================================================
# POINT D'ENTRÉE (exécution directe pour test)
# ============================================================
if __name__ == "__main__":
    from flask import Flask

    app = Flask(__name__)
    init_releve_db()
    app.register_blueprint(releve_bp, url_prefix="/releve")
    app.run(host="127.0.0.1", port=5000, debug=True)
