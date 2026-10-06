"""
Service d'accès à l'API Adzuna pour les offres d'emploi.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# ==================== CONFIGURATION ====================
APP_ID = os.getenv('ADZUNA_APP_ID')
APP_KEY = os.getenv('ADZUNA_APP_KEY')

# URL par pays (fr, gb, us, de, es, it, nl, at, au, br, ca, ch, in, mx, nz, pl, sg, za)
BASE_URL_TEMPLATE = "https://api.adzuna.com/v1/api/jobs/{pays}/search/{page}"


# ==================== RECHERCHE ====================
def rechercher_offres_adzuna(mots_cles='', ville='', nb_resultats=20, page=1, pays='fr'):
    """
    Recherche des offres sur Adzuna.
    :param mots_cles: Termes (ex: 'développeur')
    :param ville: Ville (ex: 'Paris')
    :param nb_resultats: Nombre par page (max 50)
    :param page: Numéro de page
    :param pays: Code pays (fr, gb, us, de...)
    """
    if not APP_ID or not APP_KEY:
        return {'success': False, 'erreur': 'Clés API Adzuna manquantes dans .env'}

    url = BASE_URL_TEMPLATE.format(pays=pays, page=page)

    params = {
        'app_id': APP_ID,
        'app_key': APP_KEY,
        'results_per_page': min(nb_resultats, 50),
        'content-type': 'application/json',
    }

    if mots_cles:
        params['what'] = mots_cles
    if ville:
        params['where'] = ville

    try:
        response = requests.get(url, params=params, timeout=15)

        if response.status_code == 200:
            data = response.json()
            offres = data.get('results', [])
            return {
                'success': True,
                'offres': [formater_offre_adzuna(o) for o in offres],
                'total': data.get('count', 0),
            }
        elif response.status_code == 204:
            return {'success': True, 'offres': [], 'total': 0}
        elif response.status_code == 429:
            return {
                'success': False,
                'erreur': 'Limite de requêtes Adzuna atteinte. Réessayez plus tard.',
            }
        else:
            print(f"❌ Erreur Adzuna {response.status_code} : {response.text}")
            return {'success': False, 'erreur': f'Erreur {response.status_code}'}

    except requests.exceptions.Timeout:
        return {'success': False, 'erreur': 'Timeout Adzuna'}
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur réseau Adzuna : {e}")
        return {'success': False, 'erreur': str(e)}


# ==================== FORMATAGE ====================
def formater_offre_adzuna(offre):
    """Formate une offre Adzuna pour l'affichage."""
    # ----- Salaire -----
    salaire_min = offre.get('salary_min')
    salaire_max = offre.get('salary_max')
    if salaire_min and salaire_max:
        salaire = f"{int(salaire_min)} - {int(salaire_max)} €"
    elif salaire_min:
        salaire = f"À partir de {int(salaire_min)} €"
    elif salaire_max:
        salaire = f"Jusqu'à {int(salaire_max)} €"
    else:
        salaire = "Non précisé"

    # ----- Description COMPLÈTE -----
    description_complete = offre.get('description', '') or 'Pas de description disponible.'

    # Description courte pour la carte (300 caractères)
    description_courte = description_complete
    if len(description_courte) > 300:
        description_courte = description_courte[:300] + '...'

    # ----- Type de contrat -----
    contract_time = offre.get('contract_time', '')
    contract_type = offre.get('contract_type', '')
    type_contrat = 'Non précisé'
    if contract_time == 'full_time':
        type_contrat = 'Temps plein'
    elif contract_time == 'part_time':
        type_contrat = 'Temps partiel'
    if contract_type == 'permanent':
        type_contrat += ' · CDI'
    elif contract_type == 'contract':
        type_contrat += ' · CDD'

    # ----- Catégorie -----
    categorie = offre.get('category', {}).get('label', '')

    # ----- URL -----
    url_offre = offre.get('redirect_url', '')
    if not url_offre:
        url_offre = f"https://www.adzuna.fr/details/{offre.get('id', '')}"

    return {
        'id': offre.get('id', ''),
        'titre': offre.get('title', 'Sans titre'),
        'entreprise': offre.get('company', {}).get('display_name', 'Non précisé'),
        'lieu': offre.get('location', {}).get('display_name', 'Non précisé'),
        'type_contrat': type_contrat,
        'salaire': salaire,
        'date_creation': offre.get('created', '')[:10] if offre.get('created') else '',
        'description': description_courte,
        'description_complete': description_complete,
        'url': url_offre,
        'competences': [],
        'experience': 'Non précisé',
        'categorie': categorie,
    }


# ==================== TEST ====================
if __name__ == '__main__':
    print("\n🧪 Test Adzuna...\n")

    if not APP_ID or not APP_KEY:
        print("❌ ADZUNA_APP_ID ou ADZUNA_APP_KEY manquant dans .env")
        exit(1)

    print(f"🔑 APP_ID  : {APP_ID[:10]}...")
    print(f"🔑 APP_KEY : {APP_KEY[:10]}...\n")

    resultat = rechercher_offres_adzuna(
        mots_cles='développeur',
        ville='Paris',
        nb_resultats=3
    )

    if resultat.get('success'):
        print(f"✅ {resultat['total']} offres disponibles\n")
        for i, o in enumerate(resultat['offres'], 1):
            print(f"--- Offre {i} ---")
            print(f"   Titre       : {o['titre']}")
            print(f"   Entreprise  : {o['entreprise']}")
            print(f"   Lieu        : {o['lieu']}")
            print(f"   Salaire     : {o['salaire']}")
            print(f"   Contrat     : {o['type_contrat']}")
            print(f"   Catégorie   : {o['categorie']}")
            print(f"   URL         : {o['url']}")
            print(f"   Description (courte)     : {o['description'][:80]}...")
            print(f"   Description (complète)   : {len(o['description_complete'])} caractères")
            print()
    else:
        print(f"❌ Erreur : {resultat.get('erreur')}")