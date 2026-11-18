"""Acesso ao PostgreSQL.

Usa o driver pg8000, escrito somente em Python: ele funciona mesmo em um Windows
cuja politica de seguranca bloqueia as DLLs de outros drivers.
"""

from contextlib import closing

import pg8000.dbapi

from config import DB_CONFIG

# Em um Windows em portugues, a mensagem de senha incorreta pode chegar em outra
# codificacao e aparecer como UnicodeDecodeError em vez de erro do driver.
ERROS_BANCO = (pg8000.dbapi.Error, UnicodeDecodeError)


def conectar(**alteracoes) -> pg8000.dbapi.Connection:
    return pg8000.dbapi.connect(**{**DB_CONFIG, **alteracoes})


def executar(sql: str, parametros=()) -> list[dict]:
    with closing(conectar()) as conexao:
        cursor = conexao.cursor()
        cursor.execute(sql, parametros)
        colunas = [coluna[0] for coluna in cursor.description]
        return [dict(zip(colunas, linha)) for linha in cursor.fetchall()]


def listar_nomes() -> list[str]:
    return [linha["nome"] for linha in executar("SELECT DISTINCT nome FROM metadata_pessoas;")]
