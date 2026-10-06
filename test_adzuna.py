"""
Test de connexion à l'API Adzuna.
Vérifie que les clés API sont valides et que la connexion fonctionne.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# ==================== CONFIGURATION ====================
APP_ID = os.getenv('ADZUNA_APP_ID')
APP_KEY = os.getenv('ADZUNA_APP_KEY')

BASE_URL = "https://api.adzuna.com/v1/api/jobs/fr/search/1"


def test_connexion():
    print("\n" + "=" * 60)
    print("🧪 TEST DE CONNEXION À L'API ADZUNA")
    print("=" * 60)

    # ---------- ÉTAPE 1 : Vérifier que les clés existent ----------
    print("\n📋 ÉTAPE 1 — Vérification des clés dans .env")
    print("-" * 60)

    if not APP_ID:
        print("❌ ADZUNA_APP_ID manquant dans .env")
        return False
    else:
        print(f"✅ ADZUNA_APP_ID  : {APP_ID[:12]}...")

    if not APP_KEY:
        print("❌ ADZUNA_APP_KEY manquant dans .env")
        return False
    else:
        print(f"✅ ADZUNA_APP_KEY : {APP_KEY[:12]}...")

    # ---------- ÉTAPE 2 : Test de connexion simple ----------
    print("\n📋 ÉTAPE 2 — Test de connexion (recherche basique)")
    print("-" * 60)

    params = {
        'app_id': APP_ID,
        'app_key': APP_KEY,
        'results_per_page': 3,
        'what': 'développeur',
        'content-type': 'application/json',
    }

    try:
        print(f"🌐 URL : {BASE_URL}")
        print(f"🔍 Recherche : 'développeur'")
        print()

        response = requests.get(BASE_URL, params=params, timeout=15)

        print(f"📡 Code HTTP : {response.status_code}")

        # ---------- ÉTAPE 3 : Analyse de la réponse ----------
        if response.status_code == 200:
            print("✅ Connexion réussie !")

            data = response.json()
            offres = data.get('results', [])
            total = data.get('count', 0)

            print(f"\n📊 Résultat :")
            print(f"   Nombre total d'offres : {total}")
            print(f"   Offres reçues         : {len(offres)}")

            if offres:
                print(f"\n📋 Aperçu des 3 premières offres :")
                print("-" * 60)
                for i, o in enumerate(offres, 1):
                    titre = o.get('title', 'Sans titre')
                    entreprise = o.get('company', {}).get('display_name', 'Non précisé')
                    lieu = o.get('location', {}).get('display_name', 'Non précisé')
                    print(f"\n   {i}. {titre}")
                    print(f"      🏢 {entreprise}")
                    print(f"      📍 {lieu}")

            return True

        elif response.status_code == 401:
            print("❌ ERREUR 401 — Authentification échouée")
            print(f"   Réponse : {response.text}")
            print("\n👉 Vérifiez vos clés sur https://developer.adzuna.com/")
            return False

        elif response.status_code == 403:
            print("❌ ERREUR 403 — Accès refusé")
            print(f"   Réponse : {response.text}")
            print("\n👉 Votre compte Adzuna n'est peut-être pas encore activé.")
            return False

        elif response.status_code == 429:
            print("⚠️  ERREUR 429 — Trop de requêtes")
            print("   Vous avez dépassé votre quota mensuel.")
            return False

        else:
            print(f"❌ ERREUR {response.status_code}")
            print(f"   Réponse : {response.text[:200]}")
            return False

    except requests.exceptions.Timeout:
        print("❌ TIMEOUT — Le serveur Adzuna ne répond pas")
        print("   Vérifiez votre connexion Internet.")
        return False

    except requests.exceptions.ConnectionError:
        print("❌ ERREUR RÉSEAU — Impossible de se connecter à Adzuna")
        print("   Vérifiez votre connexion Internet ou un éventuel pare-feu.")
        return False

    except Exception as e:
        print(f"❌ ERREUR INATTENDUE : {e}")
        return False


# ==================== LANCEMENT ====================
if __name__ == '__main__':
    resultat = test_connexion()

    print("\n" + "=" * 60)
    if resultat:
        print("🎉 RÉSULTAT : CONNEXION OK — Vous pouvez intégrer Adzuna !")
    else:
        print("⚠️  RÉSULTAT : ÉCHEC — Corrigez le problème avant de continuer")
    print("=" * 60 + "\n")