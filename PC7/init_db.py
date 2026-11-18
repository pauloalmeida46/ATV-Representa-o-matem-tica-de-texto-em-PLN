"""Cria o banco (se necessario), recria a tabela e importa data/pessoas.csv.

Execucao:  python init_db.py
"""

import csv
from contextlib import closing
from pathlib import Path

from pg8000.native import identifier

import banco
from config import DB_CONFIG

RAIZ = Path(__file__).parent
COLUNAS = ("nome", "etnia", "cor_cabelo", "faixa_etaria", "arquivo_imagem")
INSERIR = f"INSERT INTO metadata_pessoas ({', '.join(COLUNAS)}) VALUES (%s, %s, %s, %s, %s);"


def criar_banco() -> None:
    nome_banco = DB_CONFIG["database"]
    with closing(banco.conectar(database="postgres")) as conexao:
        conexao.autocommit = True
        cursor = conexao.cursor()
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (nome_banco,))
        if not cursor.fetchone():
            cursor.execute(f"CREATE DATABASE {identifier(nome_banco)} ENCODING 'UTF8' TEMPLATE template0;")


def importar_dados() -> int:
    with open(RAIZ / "data" / "pessoas.csv", encoding="utf-8", newline="") as arquivo:
        pessoas = [tuple(linha[coluna] for coluna in COLUNAS) for linha in csv.DictReader(arquivo)]

    with closing(banco.conectar()) as conexao:
        cursor = conexao.cursor()
        cursor.execute((RAIZ / "db" / "schema.sql").read_text(encoding="utf-8"))
        cursor.executemany(INSERIR, pessoas)
        conexao.commit()
    return len(pessoas)


if __name__ == "__main__":
    try:
        criar_banco()
        total = importar_dados()
    except banco.ERROS_BANCO as erro:
        raise SystemExit(f"Não consegui preparar o PostgreSQL. Confira o arquivo .env.\n{erro}")
    print(f"Banco '{DB_CONFIG['database']}' pronto com {total} pessoas.")
