from flask import Blueprint, render_template
from models import conectar_db

# ✅ Declare o blueprint antes de usá-lo
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/')

@dashboard_bp.route('/home')
def home():
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM itens")
    total_estoque = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM itens WHERE quantidade = 0")
    itens_zerados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM entradas WHERE date(data_entrada) = date('now')")
    entradas_hoje = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM saidas WHERE date(data_saida) = date('now')")
    saidas_hoje = cursor.fetchone()[0]

    dias_labels = []
    entradas_data = []
    saidas_data = []

    for dias_atras in range(6, -1, -1):
        cursor.execute("SELECT date('now', ?)", (f'-{dias_atras} days',))
        data_alvo = cursor.fetchone()[0]
        dias_labels.append(data_alvo[-5:])  # Ex: "07-02"

        cursor.execute("SELECT SUM(quantidade) FROM entradas WHERE date(data_entrada) = ?", (data_alvo,))
        entradas_data.append(cursor.fetchone()[0] or 0)

        cursor.execute("SELECT SUM(quantidade) FROM saidas WHERE date(data_saida) = ?", (data_alvo,))
        saidas_data.append(cursor.fetchone()[0] or 0)

    conn.close()
    return render_template("home.html",
                           total_estoque=total_estoque,
                           itens_zerados=itens_zerados,
                           entradas_hoje=entradas_hoje,
                           saidas_hoje=saidas_hoje,
                           dias_labels=dias_labels,
                           entradas_data=entradas_data,
                           saidas_data=saidas_data)
