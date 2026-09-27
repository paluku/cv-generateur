"""
lister.py — Affiche la structure complète du projet
Utile pour vérifier les fichiers manquants.
"""
import os

# Dossier à analyser (le dossier où se trouve ce script)
RACINE = os.path.dirname(os.path.abspath(__file__))


def afficher_arbre(dossier, prefixe="", niveau=0, max_niveau=4):
    """Affiche l'arborescence des fichiers."""
    if niveau > max_niveau:
        return

    try:
        elements = sorted(os.listdir(dossier))
    except PermissionError:
        return

    # Filtrer les dossiers à ignorer
    IGNORER = {'__pycache__', '.git', 'venv', 'env', '.venv',
               'node_modules', '.idea', '.vscode', 'instance'}

    elements = [e for e in elements if e not in IGNORER]

    # Séparer dossiers et fichiers
    dossiers = [e for e in elements if os.path.isdir(os.path.join(dossier, e))]
    fichiers = [e for e in elements if os.path.isfile(os.path.join(dossier, e))]

    # Afficher dossiers
    for i, d in enumerate(dossiers):
        chemin = os.path.join(dossier, d)
        dernier = (i == len(dossiers) - 1) and not fichiers
        symbole = "└── " if dernier else "├── "
        print(f"{prefixe}{symbole}📁 {d}/")
        extension = "    " if dernier else "│   "
        afficher_arbre(chemin, prefixe + extension, niveau + 1, max_niveau)

    # Afficher fichiers
    for i, f in enumerate(fichiers):
        dernier = (i == len(fichiers) - 1)
        symbole = "└── " if dernier else "├── "
        chemin = os.path.join(dossier, f)
        taille = os.path.getsize(chemin)
        taille_str = f"({taille} octets)" if taille < 1024 else f"({taille // 1024} Ko)"
        print(f"{prefixe}{symbole}📄 {f} {taille_str}")


def verifier_fichiers_importants():
    """Vérifie la présence des fichiers critiques."""
    print("\n" + "=" * 70)
    print("🔍 VÉRIFICATION DES FICHIERS CRITIQUES")
    print("=" * 70)

    importants = [
        # Racine
        ('app.py',              'racine',  'Factory Flask principal'),
        ('config.py',           'racine',  'Configuration'),
        ('extensions.py',       'racine',  'Extensions (db, login)'),
        ('models.py',           'racine',  'Modèles (User)'),
        ('data.py',             'racine',  'Données (MODELES, SAMPLE)'),
        ('stats_utils.py',      'racine',  'Fonctions stats'),
        ('filters.py',          'racine',  'Filtres Jinja'),
        ('requirements.txt',    'racine',  'Dépendances'),
        ('.env',                'racine',  'Variables d\'environnement'),
        ('stats.json',          'racine',  'Compteurs'),

        # Blueprints
        ('blueprints/__init__.py',  'bp',  'Package blueprints'),
        ('blueprints/main.py',      'bp',  'Routes principales'),
        ('blueprints/auth.py',      'bp',  'Auth (register/login)'),
        ('blueprints/premium.py',   'bp',  'Premium + Stripe'),
        ('blueprints/admin.py',     'bp',  'Admin dashboard'),

        # Templates
        ('templates/index.html',        'tpl', 'Page d\'accueil'),
        ('templates/register.html',     'tpl', 'Inscription'),
        ('templates/login.html',        'tpl', 'Connexion'),
        ('templates/mon_compte.html',   'tpl', 'Mon compte'),
        ('templates/succes_paiement.html','tpl','Succès paiement'),
        ('templates/annule_paiement.html','tpl','Annulation'),

        # Static
        ('static/css/style.css',    'static', 'CSS principal'),
        ('static/js/app.js',        'static', 'JS principal'),
    ]

    ok = 0
    manquants = 0

    for chemin, _, description in importants:
        complet = os.path.join(RACINE, chemin)
        if os.path.exists(complet):
            print(f"  ✅ {chemin:42s} {description}")
            ok += 1
        else:
            print(f"  ❌ {chemin:42s} MANQUANT — {description}")
            manquants += 1

    print("\n" + "=" * 70)
    print(f"✅ Fichiers présents : {ok}")
    print(f"❌ Fichiers manquants : {manquants}")
    print("=" * 70)

    return manquants


def verifier_imports():
    """Teste si Python arrive à importer les modules."""
    print("\n" + "=" * 70)
    print("🧪 TEST DES IMPORTS PYTHON")
    print("=" * 70)

    import sys
    sys.path.insert(0, RACINE)

    modules = [
        'config',
        'extensions',
        'models',
        'data',
        'stats_utils',
        'filters',
        'blueprints',
        'blueprints.main',
        'blueprints.auth',
        'blueprints.premium',
        'blueprints.admin',
    ]

    ok = 0
    erreurs = 0

    for module in modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
            ok += 1
        except Exception as e:
            print(f"  ❌ {module} — {type(e).__name__}: {e}")
            erreurs += 1

    print("\n" + "=" * 70)
    print(f"✅ Imports réussis : {ok}")
    print(f"❌ Imports échoués : {erreurs}")
    print("=" * 70)

    return erreurs


def main():
    print("\n" + "=" * 70)
    print(f"📁 STRUCTURE DU PROJET")
    print(f"   {RACINE}")
    print("=" * 70 + "\n")
    print(f"📦 {os.path.basename(RACINE)}/")
    afficher_arbre(RACINE, max_niveau=3)

    manquants = verifier_fichiers_importants()
    erreurs = verifier_imports()

    print("\n" + "=" * 70)
    print("🎯 DIAGNOSTIC")
    print("=" * 70)

    if manquants == 0 and erreurs == 0:
        print("🎉 Tout est OK ! Tu peux lancer : python app.py")
    else:
        print(f"⚠️ {manquants} fichier(s) manquant(s)")
        print(f"⚠️ {erreurs} erreur(s) d'import")
        print("\n➡️ Crée les fichiers manquants, puis relance ce script.")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    main()