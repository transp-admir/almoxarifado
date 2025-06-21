from flask import Blueprint, render_template, request, redirect, flash
from models import conectar_db, registrar_log

usuarios_bp = Blueprint('usuarios', __name__, url_prefix='/usuarios')

@usuarios_bp.route('/')
def listar_usuarios():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, tipo FROM usuarios")
    usuarios = cursor.fetchall()
    conn.close()
    return render_template("usuarios.html", usuarios=usuarios)

@usuarios_bp.route('/adicionar', methods=['POST'])
def adicionar_usuario():
    nome = request.form['nome'].strip()
    senha = request.form['senha'].strip()
    tipo = request.form['tipo'].strip().upper()

    if not nome or not senha or not tipo:
        flash("Todos os campos são obrigatórios.", "erro")
        return redirect('/usuarios')

    if tipo not in ['MASTER', 'COMUM']:
        flash("Tipo de usuário inválido.", "erro")
        return redirect('/usuarios')

    try:
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO usuarios (nome, senha, tipo) VALUES (?, ?, ?)", (nome, senha, tipo))
        conn.commit()
        conn.close()
        registrar_log("USUÁRIO ADICIONADO", f"{nome} ({tipo})", "web")
        flash("Usuário adicionado com sucesso.", "sucesso")
    except:
        flash("Erro: nome de usuário já existe.", "erro")

    return redirect('/usuarios')

@usuarios_bp.route('/remover/<int:id>', methods=['POST'])
def remover_usuario(id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT nome FROM usuarios WHERE id = ?", (id,))
    user = cursor.fetchone()

    if not user:
        flash("Usuário não encontrado.", "erro")
    elif user["nome"] == "master":
        flash("Não é permitido excluir o usuário master.", "erro")
    else:
        cursor.execute("DELETE FROM usuarios WHERE id = ?", (id,))
        conn.commit()
        registrar_log("USUÁRIO REMOVIDO", f"{user['nome']}", "web")
        flash("Usuário removido com sucesso.", "sucesso")

    conn.close()
    return redirect('/usuarios')
