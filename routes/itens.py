from flask import Blueprint, render_template, request, redirect, flash
from models import conectar_db, registrar_log

itens_bp = Blueprint('itens', __name__, url_prefix='/itens')

@itens_bp.route('/cadastro', methods=['GET', 'POST'])
def cadastro_item():
    if request.method == 'POST':
        descricao = request.form['descricao'].strip().upper()
        referencia = request.form['referencia'].strip().upper()

        if not descricao or not referencia:
            flash("Descrição e referência são obrigatórias.", "erro")
            return redirect('/itens/cadastro')

        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO itens (descricao, quantidade, estoque, referencia) VALUES (?, ?, ?, ?)",
                       (descricao, 0, '', referencia))
        conn.commit()
        conn.close()

        registrar_log("CADASTRO", f"Item cadastrado: {descricao} | Referência: {referencia}")
        flash("Item cadastrado com sucesso!", "sucesso")
        return redirect('/itens/cadastro')

    return render_template("cadastro_item.html")


@itens_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_item(id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM itens WHERE id = ?", (id,))
    item = cursor.fetchone()

    if not item:
        flash("Item não encontrado.", "erro")
        conn.close()
        return redirect('/itens/cadastro')

    if request.method == 'POST':
        descricao = request.form['descricao'].strip().upper()
        quantidade = request.form['quantidade']
        estoque = request.form['estoque']
        referencia = request.form['referencia'].strip().upper()

        if not quantidade.isdigit() or not estoque.isdigit():
            flash("Quantidade e Estoque devem ser números.", "erro")
            return redirect(request.url)

        cursor.execute("""
            UPDATE itens SET descricao = ?, quantidade = ?, estoque = ?, referencia = ?
            WHERE id = ?
        """, (descricao, int(quantidade), int(estoque), referencia, id))
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
            SELECT id, descricao, quantidade, estoque, referencia 
            FROM itens 
            WHERE descricao LIKE ? OR CAST(id AS TEXT) LIKE ? OR referencia LIKE ?
        """, (like_term, like_term, like_term))
    else:
        cursor.execute("""
            SELECT id, descricao, quantidade, estoque, referencia 
            FROM itens 
            ORDER BY id ASC
        """)

    resultados = cursor.fetchall()
    conn.close()

    return render_template("pesquisar_itens.html", resultados=resultados, termo=termo)

@itens_bp.route('/entrada', methods=['GET', 'POST'])
def entrada_estoque():
    conn = conectar_db()
    cursor = conn.cursor()

    # Lista de itens cadastrados (para exibir na tabela)
    cursor.execute("SELECT id, descricao, referencia FROM itens ORDER BY id ASC")
    itens_disponiveis = cursor.fetchall()

    descricao = ''
    referencia = ''
    item_id = ''
    quantidade = ''
    estoque_nome = 'TRANSP'

    if request.method == 'POST':
        item_id = request.form.get('item_id', '').strip()
        if not item_id.isdigit():
            flash("ID inválido.", "erro")
            conn.close()
            return render_template("entrada_estoque.html",
                                itens=itens_disponiveis,
                                item_id='', descricao='', referencia='',
                                quantidade=quantidade, estoque=estoque_nome)

        item_id = int(item_id)

        quantidade = request.form.get('quantidade', '').strip()
        estoque_nome = request.form.get('estoque', 'TRANSP').strip().upper()

        # Busca os dados do item
        cursor.execute("SELECT descricao, referencia FROM itens WHERE id = ?", (item_id,))
        item = cursor.fetchone()

        if not item:
            flash("Item não encontrado.", "erro")
            conn.close()
            return render_template("entrada_estoque.html", itens=itens_disponiveis)

        descricao = item['descricao']
        referencia = item['referencia']

        # Se quantidade for enviada, registrar a entrada
        if quantidade.isdigit():
            cursor.execute("UPDATE itens SET quantidade = quantidade + ? WHERE id = ?", (int(quantidade), item_id))
            conn.commit()

            registrar_log("ENTRADA", f"{quantidade} unidades adicionadas ao item {descricao} (REF: {referencia}) no estoque {estoque_nome}", "web")
            flash("Entrada registrada com sucesso!", "sucesso")

            # Limpa os campos após confirmação
            item_id = ''
            descricao = ''
            referencia = ''
            quantidade = ''
            estoque_nome = 'TRANSP'

    conn.close()
    return render_template("entrada_estoque.html", itens=itens_disponiveis,
                           descricao=descricao, referencia=referencia,
                           item_id=item_id, quantidade=quantidade, estoque=estoque_nome)


@itens_bp.route('/saida', methods=['GET', 'POST'])
def registrar_saida():
    conn = conectar_db()
    cursor = conn.cursor()

    # Carrega todos os itens para exibir na tabela lateral
    cursor.execute("SELECT id, descricao, referencia, quantidade FROM itens ORDER BY id ASC")
    itens_disponiveis = cursor.fetchall()
    print("Itens carregados:", len(itens_disponiveis))


    item_id = ''
    descricao = ''
    referencia = ''
    quantidade = ''
    placa = ''

    if request.method == 'POST':
        item_id = request.form.get('item_id', '').strip()
        quantidade = request.form.get('quantidade', '').strip()
        placa = request.form.get('placa', '').strip().upper()

        # Validação do ID
        if not item_id.isdigit():
            flash("ID inválido.", "erro")
            conn.close()
            return render_template("registrar_saida.html",
                                   itens=itens_disponiveis,
                                   item_id='', descricao='', referencia='',
                                   quantidade=quantidade, placa=placa)

        item_id = int(item_id)

        # Busca dados do item
        cursor.execute("SELECT descricao, referencia, quantidade FROM itens WHERE id = ?", (item_id,))
        item = cursor.fetchone()

        if not item:
            flash("Item não encontrado.", "erro")
        else:
            descricao = item["descricao"]
            referencia = item["referencia"]
            estoque_atual = item["quantidade"]

            if not quantidade.isdigit():
                flash("A quantidade deve ser um número inteiro.", "erro")
            elif int(quantidade) > estoque_atual:
                flash(f"Quantidade indisponível em estoque (disponível: {estoque_atual}).", "erro")
            elif int(quantidade) <= 0:
                flash("A quantidade deve ser maior que zero.", "erro")
            else:
                nova_qtd = estoque_atual - int(quantidade)

                # Atualiza estoque
                cursor.execute("UPDATE itens SET quantidade = ? WHERE id = ?", (nova_qtd, item_id))

                # Registra saída
                cursor.execute("""
                    INSERT INTO saidas (item_id, descricao, quantidade, placa, data_saida, referencia)
                    VALUES (?, ?, ?, ?, datetime('now', 'localtime'), ?)
                """, (item_id, descricao, quantidade, placa, referencia))
                conn.commit()

                registrar_log("SAÍDA", f"{quantidade} unidades removidas do item {descricao} (REF: {referencia}) - Placa: {placa}", "web")
                flash("Saída registrada com sucesso!", "sucesso")

                # Limpa os campos
                item_id = ''
                descricao = ''
                referencia = ''
                quantidade = ''
                placa = ''

    conn.close()
    return render_template("registrar_saida.html",
                           itens=itens_disponiveis,
                           item_id=item_id,
                           descricao=descricao,
                           referencia=referencia,
                           quantidade=quantidade,
                           placa=placa)
