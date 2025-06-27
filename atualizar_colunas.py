import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'database/almoxarifado.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Tenta adicionar colunas — ignora erro se já existir
for comando in [
    "ALTER TABLE itens ADD COLUMN categoria TEXT",
    "ALTER TABLE itens ADD COLUMN unidade TEXT",
    "ALTER TABLE itens ADD COLUMN minimo INTEGER",
    "ALTER TABLE itens ADD COLUMN observacoes TEXT"
]:
    try:
        cursor.execute(comando)
        print(f"✅ {comando}")
    except sqlite3.OperationalError as e:
        print(f"⚠️ Ignorado: {comando} — {str(e)}")

conn.commit()
conn.close()
print("✅ Atualização concluída com sucesso.")
