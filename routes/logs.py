from flask import Blueprint, render_template
from models import conectar_db

logs_bp = Blueprint('logs', __name__, url_prefix='/logs')

@logs_bp.route('/')
def visualizar_logs():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT acao, descricao, data_hora, usuario FROM logs ORDER BY data_hora DESC")
    logs = cursor.fetchall()
    conn.close()
    return render_template("logs.html", logs=logs)
