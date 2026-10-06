"""
Service d'IA pour la génération de lettres de motivation.
Utilise l'API Mistral (gratuit).
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MODELE = "mistral-small-latest"


def generer_lettre_motivation(cv_donnees, offre):
    """
    Génère une lettre de motivation personnalisée.
    :param cv_donnees: dict avec prénom, nom, titre, compétences, expériences
    :param offre: dict avec titre, entreprise, lieu, description
    :return: texte de la lettre
    """
    if not MISTRAL_API_KEY:
        return {'success': False, 'erreur': 'Clé Mistral manquante'}

    # Extraire les infos du CV
    prenom = cv_donnees.get('prenom', '')
    nom = cv_donnees.get('nom', '')
    titre = cv_donnees.get('titre', '')
    profil = cv_donnees.get('profil', '')
    competences = cv_donnees.get('competences', [])
    experiences = cv_donnees.get('experiences', [])

    # Résumé des expériences
    exp_txt = ""
    for e in experiences[:3]:
        exp_txt += f"- {e.get('poste', '')} chez {e.get('entreprise', '')}\n"

    # Infos de l'offre
    offre_titre = offre.get('titre', '')
    entreprise = offre.get('entreprise', '')
    lieu = offre.get('lieu', '')
    description = offre.get('description', '')[:800]

    prompt = f"""Tu es un expert en rédaction de lettres de motivation professionnelles.

Rédige une lettre de motivation pour ce candidat qui postule à cette offre.

═══ PROFIL DU CANDIDAT ═══
Prénom/Nom : {prenom} {nom}
Poste actuel/recherché : {titre}
Profil : {profil}
Compétences : {', '.join(competences) if isinstance(competences, list) else competences}
Expériences :
{exp_txt}

═══ OFFRE D'EMPLOI ═══
Titre : {offre_titre}
Entreprise : {entreprise}
Lieu : {lieu}
Description : {description}

═══ INSTRUCTIONS ═══
- La lettre doit faire 3 paragraphes max
- Premier paragraphe : pourquoi cette offre précisément
- Deuxième paragraphe : apporter ses compétences et expériences
- Troisième paragraphe : motivation et demande d'entretien
- Ton professionnel, direct, sans clichés
- En français
- Commence directement par "Madame, Monsieur," (pas d'en-tête)
- Termine par "Cordialement,"
- Ne mets PAS de date ni de coordonnées
- Sois concis et percutant
"""

    headers = {
        'Authorization': f'Bearer {MISTRAL_API_KEY}',
        'Content-Type': 'application/json',
    }

    data = {
        'model': MODELE,
        'messages': [
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.7,
        'max_tokens': 800,
    }

    try:
        response = requests.post(MISTRAL_URL, headers=headers, json=data, timeout=30)

        if response.status_code != 200:
            print(f"❌ Mistral {response.status_code} : {response.text}")
            return {
                'success': False,
                'erreur': f'Erreur API ({response.status_code})'
            }

        result = response.json()
        lettre = result['choices'][0]['message']['content'].strip()

        return {
            'success': True,
            'lettre': lettre,
        }

    except requests.exceptions.Timeout:
        return {'success': False, 'erreur': 'Timeout IA'}
    except Exception as e:
        print(f"❌ Erreur IA : {e}")
        return {'success': False, 'erreur': str(e)}


# ==================== TEST ====================
if __name__ == '__main__':
    print("\n🧪 Test IA Mistral...\n")

    cv_test = {
        'prenom': 'Amadou',
        'nom': 'Diallo',
        'titre': 'Développeur Web Full-Stack',
        'profil': "Développeur passionné avec 5 ans d'expérience",
        'competences': ['Python', 'React', 'Node.js'],
        'experiences': [
            {'poste': 'Développeur Senior', 'entreprise': 'TechCorp'},
            {'poste': 'Développeur Web', 'entreprise': 'StartupXYZ'},
        ],
    }

    offre_test = {
        'titre': 'Développeur Python Senior',
        'entreprise': 'Capgemini',
        'lieu': 'Paris',
        'description': "Nous recherchons un développeur Python pour rejoindre notre équipe innovation. Missions : développement d'API, microservices, CI/CD.",
    }

    result = generer_lettre_motivation(cv_test, offre_test)

    if result.get('success'):
        print("✅ Lettre générée :\n")
        print("-" * 60)
        print(result['lettre'])
        print("-" * 60)
    else:
        print(f"❌ Erreur : {result.get('erreur')}")