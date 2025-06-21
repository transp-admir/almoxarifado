from flask import Flask, session, request, redirect, render_template
from routes.auth import auth_bp
from routes.itens import itens_bp
from routes.saidas import saidas_bp
from routes.usuarios import usuarios_bp
from routes.logs import logs_bp
import datetime

app = Flask(__name__)
app.secret_key = 'chave_super_secreta'

# Registro dos blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(itens_bp)
app.register_blueprint(saidas_bp)
app.register_blueprint(usuarios_bp)
app.register_blueprint(logs_bp)

# Middleware para proteger rotas
@app.before_request
def proteger_rotas():
    rotas_livres = ['auth.login', 'static']
    if not session.get('usuario') and request.endpoint not in rotas_livres:
        return redirect('/')
    
@app.route('/home')
def home():
    return render_template('home.html', ano=datetime.datetime.now().year)

if __name__ == '__main__':
    app.run(debug=True)
