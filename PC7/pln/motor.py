"""Motor de busca: BOW, similaridade de cosseno e montagem do SQL."""

from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer

from .dominio import EXPRESSOES, FAIXAS_ETARIAS, NEGACOES, SINONIMOS, STOPWORDS, VALORES, CORES_AMBIGUAS
from .preprocessamento import Analise, CorretorOrtografico, analisar, normalizar, tokens_de_referencia
from .referencias import AGRUPAR, CONTAR, FILTRO, Referencia, montar_referencias

# Abaixo disto a frase e considerada fora do escopo do sistema.
LIMIAR_SIMILARIDADE = 0.6

# Dimensao unica para palavras fora do lexico. Nenhuma referencia a usa; ela so
# aumenta a norma da consulta e, portanto, reduz o cosseno de frases fora do tema.
OOV = "<oov>"

TABELA = "metadata_pessoas"
COLUNAS = "id, nome, etnia, cor_cabelo, faixa_etaria, arquivo_imagem"
ORDEM_FILTROS = ("etnia", "cor_cabelo", "faixa_etaria", "nome")
ROTULO_GRUPO = {"etnia": "etnia", "cor_cabelo": "cor de cabelo", "faixa_etaria": "faixa etária"}
ORDEM_FAIXAS = {rotulo: posicao for posicao, (rotulo, _inicio, _fim) in enumerate(FAIXAS_ETARIAS)}


def _identidade(documento: list[str]) -> list[str]:
    return documento


def similaridade_cosseno(consulta: np.ndarray, referencias: np.ndarray) -> np.ndarray:
    """Calcula cos(θ) = (v1 · v2) / (||v1|| ||v2||) entre a consulta e cada referencia."""
    normas = np.linalg.norm(referencias, axis=1) * np.linalg.norm(consulta)
    return np.divide(
        referencias @ consulta, normas, out=np.zeros(len(referencias)), where=normas > 0
    )


def montar_where(filtros: dict[str, set[str]]) -> tuple[str, list[list[str]]]:
    """Monta o WHERE sempre com parametros: o texto do usuario nunca entra no SQL."""
    condicoes, parametros = [], []
    for coluna in ORDEM_FILTROS:
        if filtros.get(coluna):
            condicoes.append(f"{coluna} = ANY(%s)")
            parametros.append(sorted(filtros[coluna]))
    return (" WHERE " + " AND ".join(condicoes) if condicoes else ""), parametros


def montar_sql(referencia: Referencia, filtros: dict[str, set[str]]) -> tuple[str, list[list[str]]]:
    where, parametros = montar_where(filtros)
    if referencia.acao == CONTAR:
        return f"SELECT COUNT(*) AS total FROM {TABELA}{where};", parametros
    if referencia.acao == AGRUPAR:
        coluna = referencia.coluna_grupo
        sql = (
            f"SELECT {coluna} AS categoria, COUNT(*) AS total FROM {TABELA}{where} "
            f"GROUP BY {coluna} ORDER BY total DESC, categoria;"
        )
        return sql, parametros
    return f"SELECT {COLUNAS} FROM {TABELA}{where} ORDER BY nome;", parametros


def _juntar(partes: list[str]) -> str:
    if len(partes) <= 1:
        return "".join(partes)
    return ", ".join(partes[:-1]) + " e " + partes[-1]


def _ordenar_valores(coluna: str, valores: set[str]) -> list[str]:
    if coluna == "faixa_etaria":
        return sorted(valores, key=ORDEM_FAIXAS.__getitem__)
    return sorted(valores)


def descrever_filtros(filtros: dict[str, set[str]]) -> str:
    modelos = {
        "etnia": "de etnia {}",
        "cor_cabelo": "com cabelo {}",
        "faixa_etaria": "na faixa de {} anos",
        "nome": "com o nome {}",
    }
    return _juntar(
        [
            modelos[coluna].format(" ou ".join(_ordenar_valores(coluna, filtros[coluna])))
            for coluna in ORDEM_FILTROS
            if filtros.get(coluna)
        ]
    )


def _pessoas(total: int) -> str:
    return "1 pessoa" if total == 1 else f"{total} pessoas"


class MotorBusca:
    def __init__(self, nomes_completos: list[str]):
        self.nomes = self._indexar_nomes(nomes_completos)
        self.referencias = montar_referencias()
        self.corretor = CorretorOrtografico(self._vocabulario())

        documentos = [tokens_de_referencia(r.texto) for r in self.referencias]
        self.vetorizador = CountVectorizer(analyzer=_identidade)
        # O documento extra coloca <oov> no lexico; ele nao entra na matriz de referencias.
        matriz = self.vetorizador.fit_transform(documentos + [[OOV]])
        self.matriz_referencias = matriz[:-1].toarray()
        self.lexico = set(self.vetorizador.vocabulary_)

    @staticmethod
    def _indexar_nomes(nomes_completos: list[str]) -> dict[str, set[str]]:
        indice: dict[str, set[str]] = {}
        for nome in nomes_completos:
            for parte in normalizar(nome).split():
                indice.setdefault(parte, set()).add(nome)
        return indice

    def _vocabulario(self) -> list[set[str]]:
        """Palavras aceitas pelo corretor, da maior para a menor prioridade."""
        do_dominio = set(VALORES) | set(CORES_AMBIGUAS) | set(SINONIMOS) | NEGACOES
        das_referencias = {
            palavra
            for referencia in self.referencias
            for palavra in referencia.texto.split()
            if palavra != FILTRO
        }
        das_expressoes = {palavra for expressao in EXPRESSOES for palavra in expressao.split()}
        return [do_dominio, das_referencias, das_expressoes, STOPWORDS, set(self.nomes)]

    def analisar(self, consulta: str) -> Analise:
        return analisar(consulta, self.corretor, self.nomes)

    def vetorizar(self, analise: Analise) -> tuple[list[str], list[str]]:
        """Substitui por <oov> os termos fora do lexico, informando quais foram."""
        tokens = [t if t in self.lexico else OOV for t in analise.tokens_finais]
        ignorados = [
            forma
            for forma, token in zip(analise.formas_finais, analise.tokens_finais)
            if token not in self.lexico
        ]
        return tokens, ignorados

    def ranquear(self, tokens_bow: list[str]) -> list[tuple[Referencia, float]]:
        vetor = self.vetorizador.transform([tokens_bow]).toarray()[0]
        similaridades = similaridade_cosseno(vetor, self.matriz_referencias)
        # Ordenacao estavel: em empate, vale a ordem do banco de referencias.
        ordem = np.argsort(-similaridades, kind="stable")
        return [(self.referencias[i], float(similaridades[i])) for i in ordem]

    def responder(self, consulta: str, executar) -> dict:
        """Executa o fluxo completo; `executar(sql, parametros)` acessa o banco."""
        analise = self.analisar(consulta)
        tokens_bow, ignorados = self.vetorizar(analise)
        ranking = self.ranquear(tokens_bow)
        referencia, similaridade = ranking[0]
        entendido = bool(tokens_bow) and similaridade >= LIMIAR_SIMILARIDADE

        resposta = {
            "entendido": False,
            "acao": None,
            "mensagem": "",
            "pessoas": [],
            "grupos": [],
            "ignorados": ignorados,
            "correcoes": analise.correcoes,
        }
        sql, parametros = None, []

        if analise.tem_negacao and analise.filtros:
            resposta["mensagem"] = (
                "Ainda não sei filtrar por exclusão (“não”, “sem”, “exceto”). "
                "Diga quem você quer ver, por exemplo: “pessoas de cabelo castanho”."
            )
        elif not entendido:
            resposta["mensagem"] = (
                "Não entendi. Pergunte sobre pessoas, etnia, cor do cabelo, faixa etária ou nome."
            )
        else:
            sql, parametros = montar_sql(referencia, analise.filtros)
            self._preencher(resposta, referencia, analise.filtros, executar(sql, parametros))

        resposta["passos"] = self._passos(
            analise, tokens_bow, ignorados, ranking[:3], sql, parametros
        )
        return resposta

    def _preencher(self, resposta: dict, referencia: Referencia, filtros: dict, linhas: list[dict]) -> None:
        descricao = descrever_filtros(filtros)
        resposta["entendido"] = True
        resposta["acao"] = referencia.acao

        if referencia.acao == CONTAR:
            total = linhas[0]["total"]
            if descricao:
                resposta["mensagem"] = (
                    f"Há {_pessoas(total)} {descricao}." if total else f"Não há nenhuma pessoa {descricao}."
                )
            else:
                cadastradas = "cadastrada" if total == 1 else "cadastradas"
                resposta["mensagem"] = f"No total, há {_pessoas(total)} {cadastradas}."
        elif referencia.acao == AGRUPAR:
            coluna = referencia.coluna_grupo
            if coluna == "faixa_etaria":
                linhas = sorted(linhas, key=lambda linha: ORDEM_FAIXAS[linha["categoria"]])
            resposta["grupos"] = linhas
            complemento = f" das pessoas {descricao}" if descricao else ""
            resposta["mensagem"] = f"Distribuição por {ROTULO_GRUPO[coluna]}{complemento}."
        else:
            resposta["pessoas"] = linhas
            total = len(linhas)
            if not total:
                resposta["mensagem"] = f"Não encontrei nenhuma pessoa {descricao}."
            elif descricao:
                resposta["mensagem"] = f"Encontrei {_pessoas(total)} {descricao}."
            else:
                resposta["mensagem"] = f"Aqui estão as {_pessoas(total)} cadastradas."

    def _passos(self, analise, tokens_bow, ignorados, melhores, sql, parametros) -> list[dict]:
        correcoes = [f"{errado} → {certo}" for errado, certo in analise.correcoes.items()]
        filtros = [
            f"{coluna}: {', '.join(_ordenar_valores(coluna, analise.filtros[coluna]))}"
            for coluna in ORDEM_FILTROS
            if analise.filtros.get(coluna)
        ]
        bow = [f"{token}: {total}" for token, total in Counter(tokens_bow).items()]
        passos = [
            {"titulo": "Minúsculas e remoção de acentos", "valor": analise.normalizado},
            {"titulo": "Tokenização", "itens": analise.tokens},
            {"titulo": "Correção de digitação", "itens": correcoes, "vazio": "nenhuma correção"},
            {"titulo": "Remoção de stopwords", "itens": analise.sem_stopwords},
            {"titulo": "Valores de metadados encontrados", "itens": filtros, "vazio": "nenhum"},
            {"titulo": "Stemming e marcador <filtro>", "itens": analise.tokens_finais},
            {"titulo": "Saco de palavras (termo: contagem)", "itens": bow, "vazio": "vazio"},
            {"titulo": "Termos fora do léxico", "itens": ignorados, "vazio": "nenhum"},
            {
                "titulo": "Referências mais similares (cosseno)",
                "ranking": [
                    {"texto": referencia.texto, "acao": referencia.acao, "similaridade": round(valor, 3)}
                    for referencia, valor in melhores
                ],
            },
        ]
        if sql:
            passos.append(
                {"titulo": "SQL executado", "codigo": sql, "parametros": parametros or None}
            )
        return passos
