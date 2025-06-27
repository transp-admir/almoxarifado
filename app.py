from flask import Flask, session, request, redirect, render_template, flash
import datetime
from datetime import timedelta

# Blueprints
from routes.auth import auth_bp
from routes.itens import itens_bp
from routes.saidas import saidas_bp
from routes.usuarios import usuarios_bp
from routes.logs import logs_bp
from routes.dashboard import dashboard_bp  # ✅ Aqui em cima com os demais

app = Flask(__name__)
app.secret_key = 'chave_secreta_segura'
app.permanent_session_lifetime = timedelta(minutes=15)

# Registro dos blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(itens_bp)
app.register_blueprint(saidas_bp)
app.register_blueprint(usuarios_bp)
app.register_blueprint(logs_bp)
app.register_blueprint(dashboard_bp)  # ✅ Registrado no momento certo

# Middleware
@app.before_request
def proteger_rotas():
    print(f"DEBUG - Endpoint acessado: {request.endpoint}")

    rotas_livres = [
        'auth.login',
        'static',
        'usuarios.cadastro_usuario',
    ]

    if 'usuario' not in session and request.endpoint not in rotas_livres:
        flash("Sua sessão expirou. Faça login novamente.", "erro")
        return redirect('/')


@app.route('/home')  # OBS: esse pode ser removido se o dashboard cuidar do /home
def home():
    return render_template('home.html', ano=datetime.datetime.now().year)

if __name__ == '__main__':
    app.run(debug=True)
