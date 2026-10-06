"""
Service d'IA pour la génération de lettres de motivation.
Utilise l'API Groq (gratuit, très rapide).
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Modèles disponibles chez Groq (2026)
# - llama-3.3-70b-versatile (recommandé)
# - llama-3.1-8b-instant (rapide)
# - mixtral-8x7b-32768
# - gemma2-9b-it
MODELE = "llama-3.3-70b-versatile"


def generer_lettre_motivation(cv_donnees, offre):
    """Génère une lettre de motivation personnalisée."""
    if not GROQ_API_KEY:
        return {'success': False, 'erreur': 'Clé Groq manquante dans .env'}

    # Extraire les infos
    prenom = cv_donnees.get('prenom', '')
    nom = cv_donnees.get('nom', '')
    titre = cv_donnees.get('titre', '')
    profil = cv_donnees.get('profil', '')
    competences = cv_donnees.get('competences', [])
    experiences = cv_donnees.get('experiences', [])

    exp_txt = ""
    for e in experiences[:3]:
        exp_txt += f"- {e.get('poste', '')} chez {e.get('entreprise', '')}\n"

    # Compétences en texte
    if isinstance(competences, list):
        comp_txt = ', '.join(competences)
    else:
        comp_txt = str(competences)

    prompt = f"""Tu es un expert en rédaction de lettres de motivation professionnelles.

Rédige une lettre de motivation pour ce candidat qui postule à cette offre.

═══ PROFIL DU CANDIDAT ═══
Prénom/Nom : {prenom} {nom}
Poste : {titre}
Profil : {profil}
Compétences : {comp_txt}
Expériences :
{exp_txt}

═══ OFFRE D'EMPLOI ═══
Poste : {offre.get('titre', '')}
Entreprise : {offre.get('entreprise', '')}
Lieu : {offre.get('lieu', '')}
Description : {(offre.get('description', '') or '')[:800]}

═══ INSTRUCTIONS ═══
- La lettre doit faire 3 paragraphes max
- Premier paragraphe : pourquoi cette offre précisément
- Deuxième paragraphe : apporter ses compétences et expériences
- Troisième paragraphe : motivation et demande d'entretien
- Ton professionnel, direct, sans clichés
- En français
- Commence directement par "Madame, Monsieur,"
- Termine par "Cordialement,"
- Ne mets PAS de date ni de coordonnées
- Sois concis et percutant
"""

    headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}',
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
        response = requests.post(GROQ_URL, headers=headers, json=data, timeout=30)

        # Afficher l'erreur détaillée si besoin
        if response.status_code != 200:
            print(f"❌ Groq {response.status_code}")
            print(f"   Réponse : {response.text}")

        # Gérer le rate limit
        if response.status_code == 429:
            import time
            print("⏱️ Rate limit, attente 3 sec...")
            time.sleep(3)
            response = requests.post(GROQ_URL, headers=headers, json=data, timeout=30)

        if response.status_code != 200:
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
        print(f"❌ Erreur : {e}")
        return {'success': False, 'erreur': str(e)}


# ==================== TEST ====================
if __name__ == '__main__':
    print("\n🧪 Test IA Groq...\n")

    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY manquante dans .env")
        print("   Ajoute cette ligne dans .env :")
        print("   GROQ_API_KEY=gsk_ta_clé")
        exit(1)

    print(f"🔑 Clé lue : {GROQ_API_KEY[:15]}...")
    print(f"🤖 Modèle   : {MODELE}")
    print(f"🌐 URL      : {GROQ_URL}\n")

    cv_test = {
        'prenom': 'Kevin',
        'nom': 'KAMBERE',
        'titre': 'Électricien',
        'profil': 'Électricien expérimenté avec 5 ans d\'expérience',
        'competences': ['Câblage', 'Maintenance', 'Sécurité électrique'],
        'experiences': [
            {'poste': 'Électricien', 'entreprise': 'BTP Solutions'},
        ],
    }

    offre_test = {
        'titre': 'Électricien industriel',
        'entreprise': 'EDF',
        'lieu': 'Paris',
        'description': 'Maintenance électrique sur site industriel. Installation et diagnostic.',
    }

    result = generer_lettre_motivation(cv_test, offre_test)

    if result.get('success'):
        print("✅ Lettre générée :\n")
        print("-" * 60)
        print(result['lettre'])
        print("-" * 60)
    else:
        print(f"❌ Erreur : {result.get('erreur')}")