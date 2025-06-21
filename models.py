import sqlite3
import datetime

DB_PATH = 'database/almoxarifado.db'

def conectar_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def registrar_log(acao, descricao="", usuario="Sistema"):
    data_hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO logs (acao, descricao, data_hora, usuario) VALUES (?, ?, ?, ?)",
                   (acao, descricao, data_hora, usuario))
    conn.commit()
    conn.close()

def criar_tabelas():
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            quantidade INTEGER,
            estoque TEXT,
            referencia TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            acao TEXT NOT NULL,
            descricao TEXT,
            data_hora TEXT NOT NULL,
            usuario TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK (tipo IN ('MASTER', 'COMUM'))
        )
    """)
    # Usuário padrão
    cursor.execute("SELECT * FROM usuarios WHERE nome = 'master'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO usuarios (nome, senha, tipo) VALUES (?, ?, ?)",
                       ('master', 'admin123', 'MASTER'))

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


    conn.commit()
    conn.close()

# Executa a criação das tabelas ao importar o módulo
criar_tabelas()
