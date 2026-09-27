# ==================== MODÈLES CV ====================
MODELES = [
    # ----- GRATUITS -----
    {"id": "modele1",  "nom": "Classique",     "description": "Sobre et professionnel",              "couleur": "#2c3e50", "premium": False},
    {"id": "modele2",  "nom": "Moderne",       "description": "Bandeau latéral coloré",              "couleur": "#3498db", "premium": False},
    {"id": "modele3",  "nom": "Élégant",       "description": "Typographie raffinée",                "couleur": "#8e44ad", "premium": False},
    {"id": "modele4",  "nom": "Créatif",       "description": "Idéal pour les métiers artistiques",  "couleur": "#e67e22", "premium": False},
    {"id": "modele5",  "nom": "Minimaliste",   "description": "Beaucoup de blanc, très lisible",     "couleur": "#34495e", "premium": False},
    {"id": "modele6",  "nom": "Corporate",     "description": "Pour les grandes entreprises",        "couleur": "#1abc9c", "premium": False},
    {"id": "modele7",  "nom": "Technique",     "description": "Met en avant les compétences",        "couleur": "#e74c3c", "premium": False},
    {"id": "modele8",  "nom": "Académique",    "description": "Pour la recherche et l'enseignement", "couleur": "#2ecc71", "premium": False},
    {"id": "modele9",  "nom": "Commercial",    "description": "Orienté résultats",                   "couleur": "#f39c12", "premium": False},
    {"id": "modele10", "nom": "International", "description": "Format anglais / américain",          "couleur": "#9b59b6", "premium": False},
    # ----- PREMIUM ⭐ -----
    {"id": "modele11", "nom": "Executive",     "description": "Prestige, format haut de gamme",      "couleur": "#0f172a", "premium": True},
    {"id": "modele12", "nom": "Luxe",          "description": "Design raffiné, typographie soignée", "couleur": "#7c3aed", "premium": True},
    {"id": "modele13", "nom": "Signature",     "description": "Unique, entièrement personnalisé",    "couleur": "#059669", "premium": True},
]


# ==================== MODÈLES LETTRES ====================
LETTRES_MODELES = [
    {"id": "modele1", "nom": "Formelle",    "description": "Présentation classique, cadre strict", "couleur": "#2c3e50"},
    {"id": "modele2", "nom": "Moderne",     "description": "Bandeau coloré, structure claire",     "couleur": "#3498db"},
    {"id": "modele3", "nom": "Élégante",    "description": "Typographie soignée, sobriété",        "couleur": "#8e44ad"},
    {"id": "modele4", "nom": "Créative",    "description": "Style original, dynamique",            "couleur": "#e67e22"},
    {"id": "modele5", "nom": "Minimaliste", "description": "Sans fioritures, tout en texte",       "couleur": "#34495e"},
]


# ==================== DONNÉES EXEMPLE ====================
SAMPLE_CV = {
    'civilite': 'Monsieur',
    'prenom': 'Amadou', 'nom': 'Diallo',
    'titre': 'Développeur Web Full-Stack',
    'email': 'amadou.diallo@mail.com',
    'telephone': '+33 6 12 34 56 78',
    'adresse': '12 rue de la Paix',
    'code_postal': '75002', 'ville': 'Paris', 'pays': 'France',
    'date_naissance': '1996-03-15', 'permis': 'B',
    'linkedin': 'linkedin.com/in/amadou-diallo',
    'site': 'amadou-dev.fr',
    'profil': ("Développeur passionné avec 5 ans d'expérience dans la création "
               "d'applications web modernes. Spécialisé en JavaScript, Python et "
               "architectures cloud."),
    'competences': ['JavaScript', 'Python', 'React', 'Node.js', 'SQL', 'Docker'],
    'experiences': [
        {'poste': 'Développeur Full-Stack Senior', 'entreprise': 'TechCorp',
         'lieu': 'Paris', 'debut': '2021-01', 'fin': '2024-12',
         'description': "Conception d'une plateforme SaaS utilisée par 50 000 clients."},
        {'poste': 'Développeur Web', 'entreprise': 'StartupXYZ',
         'lieu': 'Lyon', 'debut': '2019-06', 'fin': '2020-12',
         'description': "Développement d'une API REST et d'une interface React."},
    ],
    'formations': [
        {'diplome': 'Master Informatique', 'etablissement': 'Université Paris-Saclay',
         'lieu': 'Paris', 'debut': '2017-09', 'fin': '2019-06',
         'description': 'Mention Très Bien — Génie Logiciel'},
        {'diplome': 'Licence Informatique', 'etablissement': 'Université Claude Bernard',
         'lieu': 'Lyon', 'debut': '2014-09', 'fin': '2017-06', 'description': ''},
    ],
    'langues': [
        {'langue': 'Français', 'niveau': 'Langue maternelle'},
        {'langue': 'Anglais',  'niveau': 'Courant (C1)'},
        {'langue': 'Espagnol', 'niveau': 'Intermédiaire (B1)'},
    ],
    'certifications': ['AWS Certified Developer — 2023', 'Scrum Master PSM I — 2022'],
    'interets': ['Photographie', 'Course à pied', 'Contribution open-source'],
}


SAMPLE_LETTRE = {
    'prenom': 'Amadou', 'nom': 'Diallo',
    'adresse': '12 rue de la Paix', 'code_postal': '75002', 'ville': 'Paris',
    'email': 'amadou.diallo@mail.com', 'telephone': '+33 6 12 34 56 78',
    'entreprise': 'TechCorp SAS',
    'entreprise_adresse': '5 avenue des Champs-Élysées',
    'entreprise_cp': '75008', 'entreprise_ville': 'Paris',
    'destinataire': 'Monsieur le Directeur des Ressources Humaines',
    'date_lettre': '2025-01-15', 'lieu_lettre': 'Paris',
    'poste': 'Développeur Web Full-Stack', 'reference': 'Réf. DEV-2025-042',
    'appel': 'Madame, Monsieur,',
    'para1': "Actuellement à la recherche d'un nouveau défi professionnel, je me permets de vous adresser ma candidature.",
    'para2': "Fort de 5 années d'expérience en développement web, j'ai acquis une solide expertise.",
    'para3': "Votre entreprise, reconnue pour son innovation technologique, correspond parfaitement à mes aspirations.",
    'para4': "Je me tiens à votre disposition pour un entretien à votre convenance.",
    'politesse': "Veuillez agréer, Madame, Monsieur, l'expression de mes salutations distinguées.",
    'signature': 'Amadou Diallo',
}