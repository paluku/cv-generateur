"""
Service d'accès à l'API France Travail pour les offres d'emploi.
"""
import os
import time
import requests
from dotenv import load_dotenv

# Charge le .env
load_dotenv()

# ==================== CONFIGURATION ====================
CLIENT_ID = os.getenv('FT_CLIENT_ID')
CLIENT_SECRET = os.getenv('FT_CLIENT_SECRET')

# URLs (⚠️ %2F obligatoire dans le realm)
TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
API_BASE = "https://api.francetravail.io/partenaire/offresdemploi/v2"

# Cache du token (valable ~25 minutes)
_token_cache = {
    'access_token': None,
    'expires_at': 0,
}


# ==================== AUTHENTIFICATION ====================
def get_access_token():
    """Récupère un token d'accès (avec cache)."""
    maintenant = time.time()

    # Utiliser le token en cache s'il est encore valide
    if _token_cache['access_token'] and maintenant < _token_cache['expires_at']:
        return _token_cache['access_token']

    if not CLIENT_ID or not CLIENT_SECRET:
        print("❌ FT_CLIENT_ID ou FT_CLIENT_SECRET manquant dans .env")
        return None

    data = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scope': 'api_offresdemploiv2 o2dsoffre',
    }

    try:
        response = requests.post(TOKEN_URL, data=data, timeout=10)

        if response.status_code != 200:
            print(f"❌ Erreur {response.status_code}")
            print(f"   Réponse : {response.text}")

        response.raise_for_status()
        json_data = response.json()

        token = json_data.get('access_token')
        expires_in = json_data.get('expires_in', 1499)

        _token_cache['access_token'] = token
        _token_cache['expires_at'] = maintenant + expires_in - 30

        print(f"✅ Token France Travail obtenu (valide {expires_in}s)")
        return token

    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur récupération token : {e}")
        return None


# ==================== RECHERCHE D'OFFRES ====================
def rechercher_offres(mots_cles='', departement='', type_contrat='', nb_resultats=20):
    """Recherche des offres d'emploi sur France Travail."""
    token = get_access_token()
    if not token:
        return {'success': False, 'erreur': 'Impossible d\'obtenir un token'}

    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
    }

    params = {
        'range': f'0-{nb_resultats - 1}',
    }

    if mots_cles:
        params['motsCles'] = mots_cles
    if departement:
        params['departement'] = departement
    if type_contrat:
        params['typeContrat'] = type_contrat

    try:
        response = requests.get(
            f"{API_BASE}/offres/search",
            headers=headers,
            params=params,
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            offres = data.get('resultats', [])
            return {
                'success': True,
                'offres': offres,
                'total': len(offres),
            }

        elif response.status_code == 204:
            return {'success': True, 'offres': [], 'total': 0}

        elif response.status_code == 400:
            print(f"❌ Recherche 400 : {response.text}")
            return {
                'success': False,
                'erreur': 'Paramètres de recherche invalides',
            }

        elif response.status_code == 401:
            _token_cache['access_token'] = None
            _token_cache['expires_at'] = 0
            return {
                'success': False,
                'erreur': 'Token expiré, réessayez',
            }

        else:
            print(f"❌ Recherche {response.status_code} : {response.text}")
            return {
                'success': False,
                'erreur': f'Code HTTP {response.status_code}',
            }

    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur recherche : {e}")
        return {'success': False, 'erreur': str(e)}


# ==================== UTILITAIRES ====================
def extraire_mots_cles_cv(donnees_cv):
    """Extrait les mots-clés d'un CV pour la recherche."""
    mots = []

    if donnees_cv.get('titre'):
        mots.append(donnees_cv['titre'])

    competences = donnees_cv.get('competences', [])
    if isinstance(competences, list):
        mots.extend(competences[:3])

    return ' '.join(mots) if mots else 'développeur'


def formater_offre(offre):
    """Formate une offre France Travail pour l'affichage."""
    # ----- Description COMPLÈTE -----
    description_complete = offre.get('description', '') or 'Pas de description disponible.'

    # Description courte (300 caractères) pour la carte
    description_courte = description_complete
    if len(description_courte) > 300:
        description_courte = description_courte[:300] + '...'

    # ----- Salaire -----
    salaire = offre.get('salaire', {}).get('libelle', 'Non précisé')
    if not salaire:
        salaire = 'Non précisé'

    # ----- Catégorie / Secteur -----
    categorie = ''
    if offre.get('secteurActiviteLibelle'):
        categorie = offre['secteurActiviteLibelle']
    elif offre.get('romeLibelle'):
        categorie = offre['romeLibelle']

    # ----- URL -----
    offre_id = offre.get('id', '')
    url_offre = f"https://candidat.francetravail.fr/offres/recherche/detail/{offre_id}"

    return {
        'id': offre_id,
        'titre': offre.get('intitule', 'Sans titre'),
        'entreprise': offre.get('entreprise', {}).get('nom', 'Non précisé'),
        'lieu': offre.get('lieuTravail', {}).get('libelle', 'Non précisé'),
        'type_contrat': offre.get('typeContratLibelle', 'Non précisé'),
        'salaire': salaire,
        'date_creation': offre.get('dateCreation', '')[:10] if offre.get('dateCreation') else '',
        'description': description_courte,
        'description_complete': description_complete,
        'url': url_offre,
        'competences': [c.get('libelle', '') for c in offre.get('competences', [])[:5]],
        'experience': offre.get('experienceLibelle', 'Non précisé'),
        'categorie': categorie,
    }


# ==================== TEST DIRECT ====================
if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🧪 TEST DE L'API FRANCE TRAVAIL")
    print("=" * 60)

    print(f"\n📋 CLIENT_ID     : {CLIENT_ID[:15] + '...' if CLIENT_ID else '❌ MANQUANT'}")
    print(f"📋 CLIENT_SECRET : {CLIENT_SECRET[:15] + '...' if CLIENT_SECRET else '❌ MANQUANT'}")

    print("\n🔑 Test du token...")
    token = get_access_token()

    if token:
        print(f"✅ Token OK : {token[:30]}...")

        print("\n🔍 Test de recherche (développeur)...")
        resultat = rechercher_offres(mots_cles='développeur', nb_resultats=3)

        if resultat.get('success'):
            print(f"✅ {resultat['total']} offre(s) trouvée(s)\n")
            for i, o in enumerate(resultat.get('offres', []), 1):
                off = formater_offre(o)
                print(f"--- Offre {i} ---")
                print(f"   Titre       : {off['titre']}")
                print(f"   Entreprise  : {off['entreprise']}")
                print(f"   Lieu        : {off['lieu']}")
                print(f"   Salaire     : {off['salaire']}")
                print(f"   Contrat     : {off['type_contrat']}")
                print(f"   Catégorie   : {off['categorie']}")
                print(f"   URL         : {off['url']}")
                print(f"   Description (courte)   : {off['description'][:80]}...")
                print(f"   Description (complète) : {len(off['description_complete'])} caractères")
                print()
        else:
            print(f"❌ Erreur : {resultat.get('erreur')}")
    else:
        print("❌ Impossible d'obtenir un token")

    print("=" * 60 + "\n")