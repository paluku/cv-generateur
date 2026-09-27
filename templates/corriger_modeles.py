"""
Corrige automatiquement tous les templates CV :
1. Remplace `%|` par `%} |` (bug Jinja)
2. Supprime la date brute dupliquée dans .ligne
3. Utilise format_date dans le .date
"""
import os
import re
import glob

DOSSIER_CV = 'templates/cv'

def corriger_fichier(chemin):
    with open(chemin, 'r', encoding='utf-8') as f:
        contenu = f.read()

    original = contenu
    modifs = []

    # ---------- 1. Corriger le bug %| → %} | ----------
    if '%|' in contenu:
        contenu = contenu.replace('%|', '%} |')
        modifs.append('bug %| corrigé')

    # ---------- 2. Supprimer la date brute dans .ligne et la remplacer par format_date ----------
    # Cherche : <span class="date">{{ exp.debut }} - {{ exp.fin }}</span>
    pattern_exp = (
        r'<span class="date">\{\{ exp\.debut \}\} - \{\{ exp\.fin \}\}</span>'
    )
    remplacement_exp = (
        '<span class="date">{{ exp.debut|format_date }} - {{ exp.fin|format_date }}</span>'
    )
    if re.search(pattern_exp, contenu):
        contenu = re.sub(pattern_exp, remplacement_exp, contenu)
        modifs.append('date expérience formatée')

    # Idem pour les formations
    pattern_form = (
        r'<span class="date">\{\{ form\.debut \}\} - \{\{ form\.fin \}\}</span>'
    )
    remplacement_form = (
        '<span class="date">{{ form.debut|format_date }} - {{ form.fin|format_date }}</span>'
    )
    if re.search(pattern_form, contenu):
        contenu = re.sub(pattern_form, remplacement_form, contenu)
        modifs.append('date formation formatée')

    # ---------- 3. Supprimer la date dupliquée dans .sous-titre ----------
    # Cherche : ... | {{ exp.debut|format_date }} - {{ exp.fin|format_date }}
    pattern_sous_titre_exp = (
        r'(\| )\{\{ exp\.debut\|format_date \}\} - \{\{ exp\.fin\|format_date \}\}'
    )
    if re.search(pattern_sous_titre_exp, contenu):
        # On supprime la date et le séparateur " | "
        contenu = re.sub(r' \| \{\{ exp\.debut\|format_date \}\} - \{\{ exp\.fin\|format_date \}\}', '', contenu)
        modifs.append('doublon expérience supprimé')

    # Idem pour les formations dans le sous-titre
    if re.search(r' \| \{\{ form\.debut\|format_date \}\} - \{\{ form\.fin\|format_date \}\}', contenu):
        contenu = re.sub(r' \| \{\{ form\.debut\|format_date \}\} - \{\{ form\.fin\|format_date \}\}', '', contenu)
        modifs.append('doublon formation supprimé')

    # ---------- Écriture si modifié ----------
    if contenu != original:
        with open(chemin, 'w', encoding='utf-8') as f:
            f.write(contenu)
        print(f"✅ {os.path.basename(chemin)} : {', '.join(modifs)}")
    else:
        print(f"⏭️  {os.path.basename(chemin)} : rien à corriger")


def main():
    fichiers = sorted(glob.glob(os.path.join(DOSSIER_CV, '*.html')))
    if not fichiers:
        print(f"❌ Aucun fichier trouvé dans {DOSSIER_CV}")
        return

    print(f"🔧 Correction de {len(fichiers)} fichiers...\n")
    for f in fichiers:
        corriger_fichier(f)
    print(f"\n✅ Terminé. Vérifiez vos fichiers puis redémarrez le serveur.")


if __name__ == '__main__':
    main()