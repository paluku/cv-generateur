from flask import Flask, render_template, request
import os
from datetime import datetime
import re

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/")
def home():
    # Données pré-remplies professionnelles
    prefill_data = {
        "civilite": "M.",
        "nom": "Dupont",
        "prenom": "Jean",
        "metier": "Développeur Full Stack Senior",
        "email": "jean.dupont@email.com",
        "telephone": "+33 6 12 34 56 78",
        "ville": "Paris, France",
        "date_naissance": "1990-05-15",
        "nationalite": "Française",
        "permis": "B (Véhicule léger)",

        "experiences": [
            {
                "poste": "Lead Développeur Full Stack",
                "entreprise": "TechCorp Solutions",
                "ville": "Paris",
                "date_debut": "2021-01-15",
                "date_fin": "",
                "description": "Management d'une équipe de 8 développeurs\n"
                               "Mise en place d'une architecture microservices\n"
                               "Optimisation des performances (gain de 40%)\n"
                               "Développement d'une plateforme SaaS avec React et Node.js"
            },
            {
                "poste": "Développeur Full Stack",
                "entreprise": "WebSolutions Agency",
                "ville": "Lyon",
                "date_debut": "2018-06-01",
                "date_fin": "2020-12-31",
                "description": "Conception de sites web e-commerce\n"
                               "Développement d'APIs RESTful\n"
                               "Migration vers des technologies modernes\n"
                               "Formation des nouveaux développeurs"
            }
        ],

        "formations": [
            {
                "diplome": "Master en Informatique",
                "ecole": "Université Paris-Saclay",
                "ville": "Paris",
                "date_debut": "2016-09-01",
                "date_fin": "2018-06-30",
                "mention": "Mention Bien"
            },
            {
                "diplome": "Licence en Mathématiques",
                "ecole": "Université Paris-Diderot",
                "ville": "Paris",
                "date_debut": "2013-09-01",
                "date_fin": "2016-06-30",
                "mention": "Mention Assez Bien"
            }
        ],

        "competences": {
            "techniques": "Python, JavaScript (ES6+), TypeScript\n"
                           "React, Vue.js, Node.js, Express\n"
                           "Docker, Kubernetes, AWS (EC2, S3, RDS)\n"
                           "Git, CI/CD (GitLab CI, Jenkins)\n"
                           "MongoDB, PostgreSQL, Redis",

            "methodologies": "Agile/Scrum, DevOps, TDD, Clean Code",

            "autres": "Architecture Cloud, Microservices, API Design"
        },

        "langues": [
            {
                "langue": "Français",
                "niveau": "Langue maternelle"
            },
            {
                "langue": "Anglais",
                "niveau": "Courant (TOEIC 950)"
            },
            {
                "langue": "Espagnol",
                "niveau": "Intermédiaire (B1)"
            }
        ],

        "atouts": "Leadership d'équipe\n"
                  "Autonomie et proactivité\n"
                  "Rigueur et organisation\n"
                  "Capacité d'adaptation\n"
                  "Esprit d'innovation",

        "loisirs": "Intelligence Artificielle\n"
                   "Développement de projets open-source\n"
                   "Lecture (tech, business, science-fiction)\n"
                   "Sport (course à pied, natation)\n"
                   "Voyages"
    }

    return render_template(
        "index.html",
        prefill=prefill_data
    )


def format_date_range(date_debut, date_fin, current=False):
    """Formate les dates pour l'affichage"""

    if not date_debut:
        return ""

    try:
        debut_obj = datetime.strptime(
            date_debut,
            "%Y-%m-%d"
        )

        debut_str = debut_obj.strftime("%B %Y")

        if current:
            fin_str = "Présent"
        elif date_fin:
            fin_obj = datetime.strptime(
                date_fin,
                "%Y-%m-%d"
            )
            fin_str = fin_obj.strftime("%B %Y")
        else:
            fin_str = "Présent"

        # Calcul de la durée
        if current or not date_fin:
            fin_date = datetime.now()
        else:
            fin_date = datetime.strptime(
                date_fin,
                "%Y-%m-%d"
            )

        duration = fin_date - debut_obj

        years = duration.days // 365
        months = (duration.days % 365) // 30

        if years > 0:
            duration_str = f"{years} an"

            if years > 1:
                duration_str += "s"

            if months > 0:
                duration_str += f" {months} mois"

        elif months > 0:
            duration_str = f"{months} mois"

        else:
            duration_str = "Moins d'un mois"

        return f"{debut_str} - {fin_str} · {duration_str}"

    except ValueError:
        return ""


@app.route("/generate", methods=["POST"])
def generate():

    try:

        # ==================================================
        # CHOIX DU STYLE DE CV
        # ==================================================

        cv_style = request.form.get(
            "cv_style",
            "modern"
        )

        # ==================================================
        # INFORMATIONS PERSONNELLES
        # ==================================================

        civilite = request.form.get(
            "civilite",
            ""
        )

        nom = request.form.get(
            "nom",
            ""
        )

        prenom = request.form.get(
            "prenom",
            ""
        )

        metier = request.form.get(
            "metier",
            ""
        )

        email = request.form.get(
            "email",
            ""
        )

        telephone = request.form.get(
            "telephone",
            ""
        )

        ville = request.form.get(
            "ville",
            ""
        )

        date_naissance = request.form.get(
            "date_naissance",
            ""
        )

        nationalite = request.form.get(
            "nationalite",
            ""
        )

        permis = request.form.get(
            "permis",
            ""
        )

        # ==================================================
        # EXPERIENCES
        # ==================================================

        experiences = []

        exp_count = int(
            request.form.get(
                "experience_count",
                0
            )
        )

        for i in range(exp_count):

            poste = request.form.get(
                f"exp_{i}_poste",
                ""
            )

            entreprise = request.form.get(
                f"exp_{i}_entreprise",
                ""
            )

            exp_ville = request.form.get(
                f"exp_{i}_ville",
                ""
            )

            date_debut = request.form.get(
                f"exp_{i}_date_debut",
                ""
            )

            date_fin = request.form.get(
                f"exp_{i}_date_fin",
                ""
            )

            current = (
                request.form.get(
                    f"exp_{i}_current"
                ) == "on"
            )

            description = request.form.get(
                f"exp_{i}_description",
                ""
            )

            if poste and entreprise:

                date_range = format_date_range(
                    date_debut,
                    date_fin,
                    current
                )

                experiences.append({
                    "poste": poste,
                    "entreprise": entreprise,
                    "ville": exp_ville,
                    "date_range": date_range,
                    "description": description.replace(
                        "\n",
                        "<br>"
                    ),
                    "current": current
                })

        # ==================================================
        # FORMATIONS
        # ==================================================

        formations = []

        formation_count = int(
            request.form.get(
                "formation_count",
                0
            )
        )

        for i in range(formation_count):

            diplome = request.form.get(
                f"formation_{i}_diplome",
                ""
            )

            ecole = request.form.get(
                f"formation_{i}_ecole",
                ""
            )

            form_ville = request.form.get(
                f"formation_{i}_ville",
                ""
            )

            date_debut = request.form.get(
                f"formation_{i}_date_debut",
                ""
            )

            date_fin = request.form.get(
                f"formation_{i}_date_fin",
                ""
            )

            mention = request.form.get(
                f"formation_{i}_mention",
                ""
            )

            if diplome and ecole:

                date_range = format_date_range(
                    date_debut,
                    date_fin
                )

                formations.append({
                    "diplome": diplome,
                    "ecole": ecole,
                    "ville": form_ville,
                    "date_range": date_range,
                    "mention": mention
                })

        # ==================================================
        # COMPETENCES
        # ==================================================

        competences = {
            "techniques": request.form.get(
                "competences_techniques",
                ""
            ).replace(
                "\n",
                ", "
            ),

            "methodologies": request.form.get(
                "competences_methodologies",
                ""
            ).replace(
                "\n",
                ", "
            ),

            "autres": request.form.get(
                "competences_autres",
                ""
            ).replace(
                "\n",
                ", "
            )
        }

        # ==================================================
        # LANGUES
        # ==================================================

        langues = []

        lang_count = int(
            request.form.get(
                "langue_count",
                0
            )
        )

        for i in range(lang_count):

            langue = request.form.get(
                f"langue_{i}_nom",
                ""
            )

            niveau = request.form.get(
                f"langue_{i}_niveau",
                ""
            )

            if langue and niveau:

                langues.append(
                    f"{langue} : {niveau}"
                )

        # ==================================================
        # ATOUTS
        # ==================================================

        atouts = request.form.get(
            "atouts",
            ""
        ).split("\n")

        # ==================================================
        # LOISIRS
        # ==================================================

        loisirs = request.form.get(
            "loisirs",
            ""
        ).split("\n")

        # ==================================================
        # PHOTO
        # ==================================================

        photo = request.files.get(
            "photo"
        )

        photo_path = ""

        if photo and photo.filename:

            timestamp = datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )

            filename = (
                f"{timestamp}_{photo.filename}"
            )

            photo_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )

            photo.save(photo_path)

            photo_path = "/" + photo_path.replace(
                "\\",
                "/"
            )

        # ==================================================
        # PROFIL SANS IA
        # ==================================================

        profil = ""

        # ==================================================
        # SELECTION DU TEMPLATE
        # ==================================================

        template_mapping = {
            "modern": "modern.html",
            "classic": "classic.html",
            "creative": "creative.html",
            "minimal": "minimal.html",
            "compact": "compact.html"
        }

        template_name = template_mapping.get(
            cv_style,
            "modern.html"
        )

        # ==================================================
        # RENDU FINAL
        # ==================================================

        return render_template(

            template_name,

            civilite=civilite,
            nom=nom,
            prenom=prenom,
            metier=metier,
            email=email,
            telephone=telephone,
            ville=ville,
            date_naissance=date_naissance,
            nationalite=nationalite,
            permis=permis,

            profil=profil,

            experiences=experiences,
            formations=formations,

            competences=competences,

            langues=langues,

            atouts=atouts,
            loisirs=loisirs,

            photo=photo_path,

            cv_style=cv_style
        )

    except Exception as e:

        return f"Erreur : {str(e)}", 500


# ======================================================
# LANCEMENT
# ======================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )