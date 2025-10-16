import sqlite3
import datetime
import os

# Caminho do banco de dados
DB_PATH = os.path.join(os.path.dirname(__file__), 'database/almoxarifado.db')

def conectar_db():
    # Garante que o diretório do banco de dados exista
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def registrar_log(acao, descricao="", usuario="Sistema"):
    data_hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO logs (acao, descricao, data_hora, usuario)
        VALUES (?, ?, ?, ?)
    """, (acao, descricao, data_hora, usuario))
    conn.commit()
    conn.close()

def criar_tabelas():
    conn = conectar_db()
    cursor = conn.cursor()

    # Tabela de itens
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            quantidade INTEGER,
            estoque TEXT,
            referencia TEXT,
            categoria TEXT,
            unidade TEXT,
            minimo INTEGER,
            observacoes TEXT
        )
    """)

    # Tabela de logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            acao TEXT NOT NULL,
            descricao TEXT,
            data_hora TEXT NOT NULL,
            usuario TEXT
        )
    """)

    # Tabela de usuários
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK (tipo IN ('MASTER', 'COMUM', 'VISUALIZADOR'))
        )
    """)

    # Criação de usuário padrão
    cursor.execute("SELECT * FROM usuarios WHERE nome = 'master'")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO usuarios (nome, senha, tipo)
            VALUES (?, ?, ?)
        """, ('master', 'admin123', 'MASTER'))

    # Tabela de saídas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            descricao TEXT,
            quantidade INTEGER,
            placa TEXT,
            data_saida TEXT,
            referencia TEXT,
            FOREIGN KEY (item_id) REFERENCES itens(id)
        )
    """)

    # ✅ Tabela de entradas (agora incluída)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entradas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            descricao TEXT,
            quantidade INTEGER,
            data_entrada TEXT,
            referencia TEXT,
            FOREIGN KEY (item_id) REFERENCES itens(id)
        )
    """)

    conn.commit()

    # Adicionar colunas ausentes à tabela de itens se não existirem
    try:
        cursor.execute("ALTER TABLE itens ADD COLUMN categoria TEXT")
        cursor.execute("ALTER TABLE itens ADD COLUMN unidade TEXT")
        cursor.execute("ALTER TABLE itens ADD COLUMN minimo INTEGER")
        cursor.execute("ALTER TABLE itens ADD COLUMN observacoes TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        # Colunas já existem, o que é esperado após a primeira execução
        pass

    conn.close()

# Executa a criação das tabelas automaticamente ao importar
criar_tabelas()
