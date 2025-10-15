from flask import Blueprint, render_template, request, redirect, flash, send_file, session
from models import conectar_db, registrar_log
from fpdf import FPDF
from io import BytesIO
import datetime
import io

saidas_bp = Blueprint('saidas', __name__, url_prefix='/saidas')


def pode_modificar():
    return session.get('tipo') in ('MASTER', 'COMUM')

#FUNCAO PARA RIGISTRAR SAIDAS DO BANCO DE DADOS
@saidas_bp.route('/registrar', methods=['GET', 'POST'])
def registrar_saida():
    tipo = session.get('tipo')
    conn = conectar_db()
    cursor = conn.cursor()

    # Variáveis padrão para renderização
    item_id = ''
    descricao = ''
    referencia = ''
    quantidade = ''
    placa = ''
    termo = request.form.get('termo', '').strip()
    acao = request.form.get('acao')

    # 🔍 Busca por termo (nome ou referência)
    if request.method == 'POST' and acao == 'buscar':
        if termo:
            cursor.execute("""
                SELECT id, descricao, referencia, quantidade
                FROM itens
                WHERE descricao LIKE ? OR referencia LIKE ?
                ORDER BY id ASC
            """, (f"%{termo}%", f"%{termo}%"))
        else:
            cursor.execute("SELECT id, descricao, referencia, quantidade FROM itens ORDER BY id ASC")

        itens_disponiveis = cursor.fetchall()
        conn.close()
        return render_template("registrar_saida.html",
                               itens=itens_disponiveis,
                               item_id='',
                               descricao='',
                               referencia='',
                               quantidade='',
                               placa='',
                               termo=termo,
                               pode_modificar=pode_modificar())

    # Consulta padrão dos itens
    cursor.execute("SELECT id, descricao, referencia, quantidade FROM itens ORDER BY id ASC")
    itens_disponiveis = cursor.fetchall()

    # 📝 Registro de saída ou preenchimento automático por ID
    if request.method == 'POST' and acao != 'buscar':
        if not pode_modificar():
            flash("Acesso negado: você não tem permissão para registrar saídas.", "erro")
            conn.close()
            return redirect('/saidas/registrar')

        item_id = request.form.get('item_id', '').strip()
        quantidade = request.form.get('quantidade', '').strip()
        placa = request.form.get('placa', '').strip().upper()

        # 🔍 Apenas consulta por ID (sem registrar)
        if item_id and not quantidade:
            if item_id.isdigit():
                cursor.execute("SELECT descricao, referencia, quantidade FROM itens WHERE id = ?", (item_id,))
                item = cursor.fetchone()
                if item:
                    descricao = item["descricao"]
                    referencia = item["referencia"]
                else:
                    flash("Item não encontrado.", "erro")
            else:
                flash("ID inválido.", "erro")

            conn.close()
            return render_template("registrar_saida.html",
                                   itens=itens_disponiveis,
                                   item_id=item_id,
                                   descricao=descricao,
                                   referencia=referencia,
                                   quantidade='',
                                   placa=placa,
                                   termo=termo,
                                   pode_modificar=pode_modificar())

        # ✅ Registro efetivo da saída
        if not item_id.isdigit():
            flash("ID inválido.", "erro")
        elif not quantidade.isdigit():
            flash("A quantidade deve ser um número inteiro.", "erro")
        else:
            item_id = int(item_id)
            quantidade = int(quantidade)

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
                    cursor.execute("UPDATE itens SET quantidade = ? WHERE id = ?", (nova_qtd, item_id))
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
                           placa=placa,
                           termo=termo,
                           pode_modificar=pode_modificar())

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
                SELECT id, item_id, descricao, quantidade, placa, data_saida, referencia
                FROM saidas
                WHERE placa LIKE ?
                ORDER BY data_saida DESC
            """, (f"%{placa}%",))
        else:
            cursor.execute("""
                SELECT id, item_id, descricao, quantidade, placa, data_saida, referencia
                FROM saidas
                ORDER BY data_saida DESC
            """)

        registros = cursor.fetchall()
        conn.close()

        if acao == 'pdf':
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
            SELECT id, item_id, descricao, quantidade, placa, data_saida, referencia
            FROM saidas
            ORDER BY data_saida DESC
        """)
        registros = cursor.fetchall()
        conn.close()

    return render_template("relatorio.html", registros=registros, placa=placa, pode_modificar=pode_modificar())


@saidas_bp.route('/relatorio/pdf', methods=['POST'])
def relatorio_pdf():
    placa = request.form.get('placa', '').strip().upper()

    conn = conectar_db()
    cursor = conn.cursor()

    if placa:
        cursor.execute("""
            SELECT id, item_id, descricao, quantidade, placa, data_saida, referencia
            FROM saidas
            WHERE placa LIKE ?
            ORDER BY data_saida DESC
        """, (f"%{placa}%",))

    else:
        cursor.execute("""
            SELECT id, item_id, descricao, quantidade, placa, data_saida, referencia
            FROM saidas
            ORDER BY data_saida DESC
        """)


    registros = cursor.fetchall()
    conn.close()

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
    tipo = session.get('tipo')
    if tipo not in ('MASTER', 'COMUM'):
        flash("Acesso negado: você não tem permissão para editar saídas.", "erro")
        return redirect('/saidas/relatorio')

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

    return render_template("editar_saida.html", item_id=item_id, saida=saida, pode_modificar=True)


@saidas_bp.route('/remover-saida/<int:id>', methods=['POST'])
def remover_saida_unica(id):
    tipo = session.get('tipo')
    if tipo != 'MASTER':
        flash("Apenas usuários MASTER podem remover registros de saída.", "erro")
        return redirect('/saidas/relatorio')

    conn = conectar_db()
    cursor = conn.cursor()

    # Busca a saída
    cursor.execute("SELECT item_id, descricao, quantidade, placa FROM saidas WHERE id = ?", (id,))
    saida = cursor.fetchone()

    if not saida:
        flash("Registro de saída não encontrado.", "erro")
        conn.close()
        return redirect('/saidas/relatorio')

    # Atualiza o estoque
    cursor.execute("UPDATE itens SET quantidade = quantidade + ? WHERE id = ?", (saida['quantidade'], saida['item_id']))

    # Remove a saída
    cursor.execute("DELETE FROM saidas WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    registrar_log("REMOÇÃO", f"Removida saída: {saida['descricao']} - Qtd: {saida['quantidade']} - Placa: {saida['placa']}", session.get('usuario', 'web'))
    flash("Saída removida e estoque restaurado com sucesso!", "sucesso")
    return redirect('/saidas/relatorio')
