from flask import Blueprint, render_template, request, redirect, flash, send_file
from models import conectar_db, registrar_log
from fpdf import FPDF
from io import BytesIO
import datetime
import io



saidas_bp = Blueprint('saidas', __name__, url_prefix='/saidas')



@saidas_bp.route('/registrar', methods=['GET', 'POST'])
def registrar_saida():
    conn = conectar_db()
    cursor = conn.cursor()

    # Carrega todos os itens para a tabela lateral
    cursor.execute("SELECT id, descricao, referencia, quantidade FROM itens ORDER BY id ASC")
    itens_disponiveis = cursor.fetchall()

    # Variáveis padrão para o template
    item_id = ''
    descricao = ''
    referencia = ''
    quantidade = ''
    placa = ''

    if request.method == 'POST':
        item_id = request.form.get('item_id', '').strip()
        quantidade = request.form.get('quantidade', '').strip()
        placa = request.form.get('placa', '').strip().upper()

        # Se ID foi informado, mas a quantidade não — só preencher dados
        if item_id and not quantidade:
            cursor.execute("SELECT descricao, referencia, quantidade FROM itens WHERE id = ?", (item_id,))
            item = cursor.fetchone()
            if item:
                descricao = item['descricao']
                referencia = item['referencia']
                quantidade = ''  # Não preenche, espera usuário digitar
            else:
                flash("Item não encontrado.", "erro")

            conn.close()
            return render_template("registrar_saida.html",
                                   itens=itens_disponiveis,
                                   item_id=item_id,
                                   descricao=descricao,
                                   referencia=referencia,
                                   quantidade=quantidade,
                                   placa=placa)

        # Validação do ID
        if not item_id.isdigit():
            flash("ID inválido.", "erro")
            conn.close()
            return render_template("registrar_saida.html",
                                   itens=itens_disponiveis,
                                   item_id='', descricao='', referencia='',
                                   quantidade=quantidade, placa=placa)

        item_id = int(item_id)

        # Validação da quantidade
        if not quantidade.isdigit():
            flash("A quantidade deve ser um número inteiro.", "erro")
            conn.close()
            return render_template("registrar_saida.html",
                                   itens=itens_disponiveis,
                                   item_id=item_id, descricao='', referencia='',
                                   quantidade=quantidade, placa=placa)

        quantidade = int(quantidade)

        # Busca dados do item
        cursor.execute("SELECT descricao, referencia, quantidade FROM itens WHERE id = ?", (item_id,))
        item = cursor.fetchone()

        if not item:
            flash("Item não encontrado.", "erro")
        else:
            descricao = item["descricao"]
            referencia = item["referencia"]
            estoque_atual = item["quantidade"]

            if quantidade > estoque_atual:
                flash(f"Quantidade indisponível em estoque (disponível: {estoque_atual}).", "erro")
            elif quantidade <= 0:
                flash("A quantidade deve ser maior que zero.", "erro")
            else:
                nova_qtd = estoque_atual - quantidade

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

                # Limpa campos
                item_id = descricao = referencia = quantidade = placa = ''

    conn.close()
    return render_template("registrar_saida.html",
                           itens=itens_disponiveis,
                           item_id=item_id,
                           descricao=descricao,
                           referencia=referencia,
                           quantidade=quantidade,
                           placa=placa)


@saidas_bp.route('/relatorio', methods=['GET', 'POST'])
def relatorio():
    placa = ''
    registros = []

    conn = conectar_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        placa = request.form.get('placa', '').strip().upper()
        acao = request.form.get('acao')

        if placa:
            cursor.execute("""
                SELECT item_id, descricao, quantidade, placa, data_saida, referencia 
                FROM saidas 
                WHERE placa LIKE ? 
                ORDER BY data_saida DESC
            """, (f"%{placa}%",))
        else:
            cursor.execute("""
                SELECT item_id, descricao, quantidade, placa, data_saida, referencia 
                FROM saidas 
                ORDER BY data_saida DESC
            """)

        registros = cursor.fetchall()
        conn.close()

        if acao == 'pdf':
            # Gera o PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, txt="Relatório de Saídas", ln=True, align='C')
            pdf.ln(10)

            for item in registros:
                linha = f"{item['data_saida']} | {item['descricao']} | Qtd: {item['quantidade']} | Placa: {item['placa']} | Ref: {item['referencia']}"
                pdf.multi_cell(0, 10, txt=linha)

            pdf_output = BytesIO()
            pdf_output.write(pdf.output(dest='S').encode('latin-1'))
            pdf_output.seek(0)

            return send_file(pdf_output, download_name="relatorio_saidas.pdf", as_attachment=True)

    else:
        cursor.execute("""
            SELECT item_id, descricao, quantidade, placa, data_saida, referencia 
            FROM saidas 
            ORDER BY data_saida DESC
        """)
        registros = cursor.fetchall()
        conn.close()

    return render_template("relatorio.html", registros=registros, placa=placa)


@saidas_bp.route('/relatorio/pdf', methods=['POST'])
def relatorio_pdf():
    placa = request.form.get('placa', '').strip().upper()

    conn = conectar_db()
    cursor = conn.cursor()

    if placa:
        cursor.execute("""
            SELECT item_id, descricao, quantidade, placa, data_saida, referencia 
            FROM saidas 
            WHERE placa LIKE ? 
            ORDER BY data_saida DESC
        """, (f"%{placa}%",))
    else:
        cursor.execute("""
            SELECT item_id, descricao, quantidade, placa, data_saida, referencia 
            FROM saidas 
            ORDER BY data_saida DESC
        """)

    registros = cursor.fetchall()
    conn.close()

    # Gera o PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, txt="Relatório de Saídas", ln=True, align='C')
    pdf.ln(10)

    for item in registros:
        linha = f"{item['data_saida']} | {item['descricao']} | Qtd: {item['quantidade']} | Placa: {item['placa']} | Ref: {item['referencia']}"
        pdf.multi_cell(0, 10, txt=linha)

    pdf_output = io.BytesIO()
    pdf_output.write(pdf.output(dest='S').encode('latin-1'))
    pdf_output.seek(0)

    return send_file(pdf_output, download_name="relatorio_saidas.pdf", as_attachment=True)


@saidas_bp.route('/editar/<int:item_id>/<data_saida>', methods=['GET', 'POST'])
def editar_saida(item_id, data_saida):
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT descricao, quantidade, placa, data_saida, referencia 
        FROM saidas WHERE item_id = ? AND data_saida = ?
    """, (item_id, data_saida))
    saida = cursor.fetchone()

    if not saida:
        flash("Saída não encontrada.", "erro")
        return redirect('/saidas/relatorio')

    if request.method == 'POST':
        nova_quant = request.form['quantidade']
        nova_placa = request.form['placa'].strip().upper()
        nova_data = request.form['data_saida'].strip()
        nova_ref = request.form['referencia'].strip()

        if not nova_quant.isdigit():
            flash("Quantidade deve ser um número.", "erro")
            return redirect(request.url)

        cursor.execute("""
            UPDATE saidas SET quantidade = ?, placa = ?, data_saida = ?, referencia = ?
            WHERE item_id = ? AND data_saida = ?
        """, (int(nova_quant), nova_placa, nova_data, nova_ref, item_id, data_saida))
        conn.commit()
        conn.close()

        registrar_log("EDIÇÃO DE SAÍDA", f"Edição na saída do item ID {item_id}", "web")
        flash("Saída atualizada com sucesso!", "sucesso")
        return redirect('/saidas/relatorio')

    return render_template("editar_saida.html", item_id=item_id, saida=saida)
