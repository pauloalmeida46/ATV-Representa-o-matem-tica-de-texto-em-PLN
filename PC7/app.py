"""Aplicacao Flask de pagina unica: busca de pessoas em linguagem natural.

Execucao:  python app.py
"""

from flask import Flask, jsonify, render_template, request, url_for

import banco
from pln.motor import MotorBusca

TAMANHO_MAXIMO_CONSULTA = 300

EXEMPLOS = (
    "Quantas pessoas estão cadastradas?",
    "Mostre as pessoas de cabelo ruivo",
    "Crianças indígenas",
    "Quantas pessoas pardas têm entre 18 e 29 anos?",
    "Quantas pessoas por etnia?",
    "Qual a cor do cabelo da Ana?",
    "qunatas pesoas loiras?",
)

app = Flask(__name__)
app.json.sort_keys = False  # mostra as correcoes na ordem em que foram digitadas

try:
    motor = MotorBusca(banco.listar_nomes())
except banco.ERROS_BANCO as erro:
    raise SystemExit(
        "Não consegui ler o banco de dados. Confira o arquivo .env e rode: python init_db.py\n"
        f"{erro}"
    )


@app.get("/")
def pagina_inicial():
    return render_template("index.html", exemplos=EXEMPLOS)


@app.post("/api/buscar")
def buscar():
    dados = request.get_json(silent=True) or {}
    consulta = str(dados.get("consulta", "")).strip()
    if not consulta:
        return jsonify(erro="Digite uma pergunta."), 400
    if len(consulta) > TAMANHO_MAXIMO_CONSULTA:
        return jsonify(erro=f"Use no máximo {TAMANHO_MAXIMO_CONSULTA} caracteres."), 400

    try:
        resposta = motor.responder(consulta, banco.executar)
    except banco.ERROS_BANCO:
        app.logger.exception("Falha ao consultar o banco")
        return jsonify(erro="O banco de dados não respondeu. Verifique se o PostgreSQL está ativo."), 503

    for pessoa in resposta["pessoas"]:
        pessoa["imagem_url"] = url_for("static", filename=pessoa["arquivo_imagem"])
    return jsonify(resposta)


if __name__ == "__main__":
    app.run(debug=False)
