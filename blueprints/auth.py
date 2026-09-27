from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'], strict_slashes=False)
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        email = request.form.get('email', '').strip().lower()
        telephone = request.form.get('telephone', '').strip()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')
        next_page = request.form.get('next', '')

        erreurs = []
        if not nom: erreurs.append('Le nom est obligatoire.')
        if not email: erreurs.append("L'email est obligatoire.")
        if len(password) < 6: erreurs.append('Mot de passe : 6 caractères minimum.')
        if password != password2: erreurs.append('Les mots de passe ne correspondent pas.')
        if User.query.filter_by(email=email).first():
            erreurs.append('Cet email est déjà utilisé.')

        if erreurs:
            for e in erreurs: flash(e, 'error')
            return render_template('register.html', nom=nom, email=email,
                                   telephone=telephone, next_page=next_page)

        user = User(nom=nom, email=email, telephone=telephone)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)

        if next_page == 'premium':
            flash(f'Bienvenue {user.nom} ! Vous pouvez maintenant passer Premium.', 'success')
            return redirect(url_for('main.index') + '#premium')

        flash(f'Bienvenue {user.nom} ! Votre compte est créé.', 'success')
        return redirect(url_for('main.index'))

    next_page = request.args.get('next', '')
    return render_template('register.html', next_page=next_page)


@auth_bp.route('/login', methods=['GET', 'POST'], strict_slashes=False)
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f'Content de vous revoir, {user.nom} !', 'success')
            next_page = request.args.get('next') or request.form.get('next')
            return redirect(next_page or url_for('main.index'))

        flash('Email ou mot de passe incorrect.', 'error')

    return render_template('login.html')


@auth_bp.route('/logout', strict_slashes=False)
def logout():
    logout_user()
    flash('Vous êtes déconnecté.', 'success')
    return redirect(url_for('main.index'))


@auth_bp.route('/mon-compte', strict_slashes=False)
@login_required
def mon_compte():
    return render_template('mon_compte.html', user=current_user)