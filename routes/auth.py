from flask import Flask, Blueprint, render_template, request, redirect, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from models import conectar_db, registrar_log
import datetime

app = Flask(__name__)
app.secret_key = 'chave_super_secreta'

# --- Blueprint de Auth (login/logout) ---
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nome = request.form['usuario'].strip()
        senha = request.form['senha'].strip()

        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT senha, tipo FROM usuarios WHERE nome = ?", (nome,))
        resultado = cursor.fetchone()
        conn.close()

        if resultado and resultado[0] == senha:
            session.permanent = True
            session['usuario'] = nome
            session['sessao_iniciada'] = True
            session['tipo'] = resultado[1].strip().upper()
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

# --- Blueprint de Usuários (cadastro) ---
usuarios_bp = Blueprint('usuarios', __name__, url_prefix='/usuarios')

@usuarios_bp.route('/cadastro', methods=['GET', 'POST'])
def cadastro_usuario():
    if request.method == 'POST':
        nome = request.form['nome'].strip()
        senha = request.form['senha'].strip()
        tipo = request.form['tipo'].strip().upper()

        if not nome or not senha or not tipo:
            flash("Todos os campos são obrigatórios.", "erro")
            return redirect('/usuarios/cadastro')

        senha_hash = generate_password_hash(senha)

        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE nome = ?", (nome,))
        if cursor.fetchone():
            flash("Usuário já existe.", "erro")
            conn.close()
            return redirect('/usuarios/cadastro')

        cursor.execute("INSERT INTO usuarios (nome, senha, tipo) VALUES (?, ?, ?)", (nome, senha_hash, tipo))
        conn.commit()
        conn.close()

        registrar_log("CADASTRO", f"Usuário {nome} cadastrado com tipo {tipo}")
        flash("Usuário cadastrado com sucesso!", "sucesso")
        return redirect('/usuarios/cadastro')

    return render_template('cadastro_usuario.html', ano=datetime.datetime.now().year)

# --- Middleware para proteger rotas privadas ---
@app.before_request
def proteger_rotas():
    rotas_livres = ['auth.login', 'auth.logout', 'static']
    if not session.get('usuario'):
        if request.endpoint not in rotas_livres and not request.path.startswith('/usuarios/cadastro'):
            print(f"⚠️ Acesso negado a {request.path}, sem sessão")
            return redirect('/')

# --- Página Home ---
@app.route('/home')
def home():
    if 'usuario' not in session:
        return redirect('/')
    return render_template('home.html', ano=datetime.datetime.now().year)

# --- Registro dos blueprints ---
app.register_blueprint(auth_bp)
app.register_blueprint(usuarios_bp)

if __name__ == '__main__':
    app.run(debug=True)
