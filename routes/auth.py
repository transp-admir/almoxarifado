from flask import Blueprint, render_template, request, redirect, session, flash
from models import conectar_db, registrar_log
import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nome = request.form['usuario'].strip()
        senha = request.form['senha'].strip()

        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT tipo FROM usuarios WHERE nome = ? AND senha = ?", (nome, senha))
        resultado = cursor.fetchone()
        conn.close()

        if resultado:
            session['usuario'] = nome
            session['tipo'] = resultado[0]
            registrar_log("LOGIN", f"Usuário {nome} logado", nome)
            return redirect('/home')
        else:
            flash("Usuário ou senha inválidos.", "erro")

    return render_template('login.html', ano=datetime.datetime.now().year)

@auth_bp.route('/logout')
def logout():
    usuario = session.get('usuario')
    session.clear()
    if usuario:
        registrar_log("LOGOUT", f"Usuário {usuario} saiu", usuario)
    return redirect('/')
