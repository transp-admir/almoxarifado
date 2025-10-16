from flask import Blueprint, render_template, request, redirect, flash, session, Response
from models import conectar_db, registrar_log
import datetime
import csv
import io


itens_bp = Blueprint('itens', __name__, url_prefix='/itens')


@itens_bp.route('/cadastro', methods=['GET', 'POST'])
def cadastro_item():
    tipo = session.get('tipo')
    if request.method == 'POST':
        if tipo not in ('MASTER', 'COMUM'):
            flash("Acesso negado: você não tem permissão para cadastrar itens.", "erro")
            return redirect('/itens/cadastro')

        descricao = request.form['descricao'].strip().upper()
        referencia = request.form['referencia'].strip().upper()
        categoria = request.form.get('categoria', '').strip().upper()
        estoque = request.form.get('estoque', '').strip().upper()
        unidade = request.form.get('unidade', '').strip().upper()
        minimo = request.form.get('minimo', '0').strip()
        observacoes = request.form.get('obs', '').strip()

        if not descricao or not referencia or not categoria or not unidade:
            flash("Todos os campos obrigatórios devem ser preenchidos.", "erro")
            return redirect('/itens/cadastro')

        try:
            minimo = int(minimo)
        except ValueError:
            minimo = 0

        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO itens (descricao, quantidade, estoque, referencia, categoria, unidade, minimo, observacoes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (descricao, 0, estoque, referencia, categoria, unidade, minimo, observacoes))
        conn.commit()
        conn.close()

        registrar_log("CADASTRO", f"Novo item: {descricao} | REF: {referencia} | Categoria: {categoria}", "web")
        flash("Item cadastrado com sucesso!", "sucesso")
        return redirect('/itens/cadastro')

    return render_template("cadastro_item.html")


@itens_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_item(id):
    tipo = session.get('tipo')
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM itens WHERE id = ?", (id,))
    item = cursor.fetchone()

    if not item:
        flash("Item não encontrado.", "erro")
        conn.close()
        return redirect('/itens/pesquisar')

    if request.method == 'POST':
        if tipo not in ('MASTER', 'COMUM'):
            flash("Acesso negado: você não tem permissão para editar itens.", "erro")
            conn.close()
            return redirect(f'/itens/editar/{id}')

        descricao = request.form['descricao'].strip().upper()
        quantidade_raw = request.form['quantidade']
        estoque_raw = request.form['estoque']
        quantidade = quantidade_raw.strip()
        estoque = estoque_raw.strip()
        referencia = request.form['referencia'].strip().upper()

        try:
            quantidade = int(quantidade)
        except (ValueError, TypeError):
            flash("Quantidade deve ser um número inteiro.", "erro")
            conn.close()
            return redirect(request.url)

        cursor.execute("""
            UPDATE itens SET descricao = ?, quantidade = ?, estoque = ?, referencia = ?
            WHERE id = ?
        """, (descricao, int(quantidade), estoque, referencia, id))
        conn.commit()
        conn.close()

        registrar_log("EDIÇÃO", f"Item {id} editado: {descricao}", "web")
        flash("Item atualizado com sucesso!", "sucesso")
        return redirect('/itens/pesquisar')

    conn.close()
    return render_template("editar_item.html", item=item)


@itens_bp.route('/pesquisar', methods=['GET', 'POST'])
def pesquisar_itens():
    termo = ''
    resultados = []

    conn = conectar_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        termo = request.form.get('termo', '').strip().upper()
        like_term = f"%{termo}%"
        cursor.execute("""
            SELECT id, descricao, quantidade, estoque, referencia, categoria, unidade, minimo, observacoes
            FROM itens
            WHERE descricao LIKE ? OR CAST(id AS TEXT) LIKE ? OR referencia LIKE ?
            ORDER BY descricao ASC
        """, (like_term, like_term, like_term))

    elif request.method == 'GET' and request.args.get('quantidade') == '0':
        cursor.execute("""
            SELECT id, descricao, quantidade, estoque, referencia, categoria, unidade, minimo, observacoes
            FROM itens
            WHERE quantidade = 0
            ORDER BY descricao ASC
        """)

    else:
        cursor.execute("""
            SELECT id, descricao, quantidade, estoque, referencia, categoria, unidade, minimo, observacoes
            FROM itens
            ORDER BY descricao ASC
        """)

    resultados = cursor.fetchall()
    conn.close()

    return render_template('pesquisar_itens.html', resultados=resultados, termo=termo)

@itens_bp.route('/relatorio_csv')
def relatorio_csv():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, descricao, referencia, quantidade
        FROM itens
        ORDER BY descricao ASC
    """)
    resultados = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')

    writer.writerow(['ID', 'Descricao', 'Referencia', 'Quantidade'])

    for item in resultados:
        writer.writerow([item['id'], item['descricao'], item['referencia'], item['quantidade']])

    output.seek(0)

    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment;filename=relatorio_almoxarifado.csv"}
    )


@itens_bp.route('/entrada', methods=['GET', 'POST'])
def entrada_estoque():
    tipo = session.get('tipo')
    conn = conectar_db()
    cursor = conn.cursor()

    descricao = ''
    referencia = ''
    item_id = ''
    quantidade = ''
    estoque_nome = 'TRANSP'
    termo = request.form.get('termo', '').strip().upper()
    acao = request.form.get('acao')

    if request.method == 'POST' and acao == 'buscar' and termo:
        like_term = f"%{termo}%"
        cursor.execute("""
            SELECT id, descricao, referencia FROM itens
            WHERE descricao LIKE ? OR CAST(id AS TEXT) LIKE ? OR referencia LIKE ?
            ORDER BY id ASC
        """, (like_term, like_term, like_term))
        itens_disponiveis = cursor.fetchall()
        conn.close()
        return render_template("entrada_estoque.html",
                               itens=itens_disponiveis,
                               descricao='', referencia='',
                               item_id='', quantidade='', estoque='TRANSP',
                               termo=termo)

    cursor.execute("SELECT id, descricao, referencia FROM itens ORDER BY id ASC")
    itens_disponiveis = cursor.fetchall()

    if request.method == 'POST' and not acao:
        if tipo not in ('MASTER', 'COMUM'):
            flash("Acesso negado: você não tem permissão para registrar entrada.", "erro")
            conn.close()
            return render_template("entrada_estoque.html",
                                   itens=itens_disponiveis,
                                   descricao=descricao, referencia=referencia,
                                   item_id=item_id, quantidade=quantidade,
                                   estoque=estoque_nome, termo=termo)

        item_id = request.form.get('item_id', '').strip()
        quantidade = request.form.get('quantidade', '').strip()
        estoque_nome = request.form.get('estoque', 'TRANSP').strip().upper()

        if not item_id.isdigit():
            flash("ID inválido.", "erro")
            conn.close()
            return render_template("entrada_estoque.html",
                                   itens=itens_disponiveis,
                                   item_id='', descricao='', referencia='',
                                   quantidade=quantidade, estoque=estoque_nome)

        item_id = int(item_id)

        cursor.execute("SELECT descricao, referencia FROM itens WHERE id = ?", (item_id,))
        item = cursor.fetchone()

        if not item:
            flash("Item não encontrado.", "erro")
            conn.close()
            return render_template("entrada_estoque.html", itens=itens_disponiveis)

        descricao = item['descricao']
        referencia = item['referencia']

        if quantidade.isdigit():
            cursor.execute("UPDATE itens SET quantidade = quantidade + ? WHERE id = ?", (int(quantidade), item_id))

            data_entrada = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO entradas (item_id, descricao, quantidade, data_entrada, referencia)
                VALUES (?, ?, ?, ?, ?)
            """, (item_id, descricao, int(quantidade), data_entrada, referencia))

            conn.commit()

            registrar_log("ENTRADA", f"{quantidade} unidades adicionadas ao item {descricao} (REF: {referencia}) no estoque {estoque_nome}", "web")
            flash("Entrada registrada com sucesso!", "sucesso")

            item_id = ''
            descricao = ''
            referencia = ''
            quantidade = ''
            estoque_nome = 'TRANSP'

    conn.close()
    return render_template("entrada_estoque.html",
                           itens=itens_disponiveis,
                           descricao=descricao, referencia=referencia,
                           item_id=item_id, quantidade=quantidade,
                           estoque=estoque_nome, termo=termo)

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/')

@itens_bp.route('/remover/<int:id>', methods=['POST'])
def remover_item(id):
    tipo = session.get('tipo')
    if tipo != 'MASTER':
        flash("Acesso negado: apenas usuários MASTER podem remover itens.", "erro")
        return redirect('/itens/pesquisar')

    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT descricao, referencia FROM itens WHERE id = ?", (id,))
    item = cursor.fetchone()

    if not item:
        conn.close()
        flash("Item não encontrado.", "erro")
        return redirect('/itens/pesquisar')

    cursor.execute("DELETE FROM itens WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    registrar_log("REMOÇÃO", f"Item removido: {item['descricao']} (REF: {item['referencia']})", session.get('usuario', 'Sistema'))
    flash("Item removido com sucesso!", "sucesso")
    return redirect('/itens/pesquisar')
