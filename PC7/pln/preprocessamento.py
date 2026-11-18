"""Etapas de pre-processamento que transformam a frase em tokens normalizados."""

import re
import unicodedata
from dataclasses import dataclass, field

from nltk.stem.snowball import SnowballStemmer
from rapidfuzz.distance import OSA

from .dominio import (
    CORES_AMBIGUAS,
    EXPRESSOES,
    FAIXAS_ETARIAS,
    NEGACOES,
    PALAVRA_CHAVE_COLUNA,
    SINONIMOS,
    STOPWORDS,
    VALORES,
)
from .referencias import FILTRO

_stemmer = SnowballStemmer("portuguese")

_NUMERO = r"(\d{1,3})"
_ANOS = r"(?:\s*anos?)?"
IDADE_MAXIMA = 150

# A ordem importa: "6 ate 12" precisa casar como intervalo antes de "ate 12".
_PADROES_IDADE = (
    (re.compile(rf"{_NUMERO}\s*(?:\+|anos?\s+ou\s+mais)"), lambda a: (a, IDADE_MAXIMA)),
    (re.compile(rf"{_NUMERO}\s*(?:a|ate|e|-)\s*{_NUMERO}{_ANOS}"), lambda a, b: (min(a, b), max(a, b))),
    (re.compile(rf"(?:mais\s+de|acima\s+de|maior(?:es)?\s+(?:de|que))\s+{_NUMERO}{_ANOS}"), lambda a: (a + 1, IDADE_MAXIMA)),
    (re.compile(rf"(?:menos\s+de|abaixo\s+de|menor(?:es)?\s+(?:de|que))\s+{_NUMERO}{_ANOS}"), lambda a: (0, a - 1)),
    (re.compile(rf"\bate\s+{_NUMERO}{_ANOS}"), lambda a: (0, a)),
    (re.compile(rf"{_NUMERO}\s*anos?\b"), lambda a: (a, a)),
)

_EXPRESSOES_RE = re.compile(r"\b(" + "|".join(map(re.escape, EXPRESSOES)) + r")\b")


@dataclass
class Analise:
    """Resultado de cada etapa, guardado para o painel de explicacao."""

    original: str
    normalizado: str = ""
    tokens: list[str] = field(default_factory=list)
    correcoes: dict[str, str] = field(default_factory=dict)
    sem_stopwords: list[str] = field(default_factory=list)
    filtros: dict[str, set[str]] = field(default_factory=dict)
    formas_finais: list[str] = field(default_factory=list)  # antes do stemming
    tokens_finais: list[str] = field(default_factory=list)
    tem_negacao: bool = False


def normalizar(texto: str) -> str:
    """Converte para minusculas e remove acentos."""
    decomposto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in decomposto if not unicodedata.combining(c)).strip()


def radical(token: str) -> str:
    return _stemmer.stem(token)


def tokenizar(texto: str) -> list[str]:
    """Separa as palavras, descartando pontuacao e simbolos."""
    return re.findall(r"[a-z0-9]+", texto)


def tokens_de_referencia(texto: str) -> list[str]:
    """Aplica as etapas pertinentes a uma frase-modelo do banco de referencias."""
    tokens = []
    for token in texto.split():
        if token == FILTRO:
            tokens.append(token)
        elif token not in STOPWORDS:
            tokens.append(radical(SINONIMOS.get(token, token)))
    return tokens


def faixas_no_intervalo(minimo: int, maximo: int) -> set[str]:
    return {rotulo for rotulo, inicio, fim in FAIXAS_ETARIAS if inicio <= maximo and minimo <= fim}


def extrair_idades(texto: str) -> tuple[str, set[str]]:
    """Troca expressoes numericas ("de 6 a 12 anos") pelas faixas correspondentes."""
    faixas: set[str] = set()

    def consumir(intervalo):
        def substituir(casamento: re.Match) -> str:
            faixas.update(faixas_no_intervalo(*intervalo(*map(int, casamento.groups()))))
            return " "
        return substituir

    for padrao, intervalo in _PADROES_IDADE:
        texto = padrao.sub(consumir(intervalo), texto)
    return texto, faixas


class CorretorOrtografico:
    """Aproxima cada palavra desconhecida da palavra conhecida mais parecida.

    Usa a distancia OSA (Levenshtein com transposicao), que conta "qunatas"
    como um unico erro. Os grupos estao em ordem de prioridade para desempate.
    """

    def __init__(self, grupos: list[set[str]]):
        self.grupos = grupos
        self.conhecidas = set().union(*grupos)
        self.radicais = {radical(palavra) for palavra in self.conhecidas}

    @staticmethod
    def _limite(tamanho: int) -> int:
        # Palavras curtas ficam parecidas demais umas com as outras.
        if tamanho <= 3:
            return 0
        return 1 if tamanho <= 6 else 2

    def corrigir(self, token: str) -> str:
        if token.isdigit() or token in self.conhecidas or radical(token) in self.radicais:
            return token
        limite = self._limite(len(token))
        if limite == 0:
            return token

        melhor = None
        for prioridade, grupo in enumerate(self.grupos):
            for palavra in grupo:
                # Em palavras curtas, exigir a mesma inicial evita trocas como franca -> branca.
                if len(token) <= 6 and palavra[0] != token[0]:
                    continue
                distancia = OSA.distance(token, palavra, score_cutoff=limite)
                if distancia <= limite:
                    chave = (distancia, prioridade, palavra[0] != token[0], palavra)
                    if melhor is None or chave < melhor:
                        melhor = chave
        return melhor[-1] if melhor else token


def _juntar_expressoes(tokens: list[str]) -> list[str]:
    return _EXPRESSOES_RE.sub(lambda m: EXPRESSOES[m.group(1)], " ".join(tokens)).split()


def extrair_filtros(
    tokens: list[str], faixas: set[str], nomes: dict[str, set[str]]
) -> tuple[list[str], dict[str, set[str]]]:
    """Separa os valores de metadados das palavras que indicam a intencao."""
    filtros: dict[str, set[str]] = {}
    restantes: list[str] = []
    tokens_de_nome: list[str] = []
    contexto = None  # "cabelo" logo apos a palavra cabelo; "cor" logo apos uma cor de cabelo

    def adicionar(coluna: str, valores) -> None:
        filtros.setdefault(coluna, set()).update(valores)

    if faixas:
        adicionar("faixa_etaria", faixas)

    for token in tokens:
        token = SINONIMOS.get(token, token)
        proximo_contexto = None

        if token in CORES_AMBIGUAS:
            valor_cabelo, valores_etnia = CORES_AMBIGUAS[token]
            # "cabelo preto" e "cabelo loiro ou preto" sao cabelo; "cabelo preto e brancas"
            # concorda no feminino com "pessoas", entao "brancas" e etnia.
            e_cabelo = contexto == "cabelo" or (contexto == "cor" and token.endswith(("o", "os")))
            if e_cabelo:
                adicionar("cor_cabelo", {valor_cabelo})
                proximo_contexto = "cor"
            else:
                adicionar("etnia", valores_etnia)
        elif token in VALORES:
            coluna, valores = VALORES[token]
            adicionar(coluna, valores)
            if coluna == "cor_cabelo":
                proximo_contexto = "cor"
        elif token in nomes:
            tokens_de_nome.append(token)
        else:
            restantes.append(token)
            if token == "cabelo":
                proximo_contexto = "cabelo"

        contexto = proximo_contexto

    if tokens_de_nome:
        conjuntos = [nomes[token] for token in tokens_de_nome]
        # "Ana Souza" e uma pessoa so (intersecao); "Ana e Pedro" sao duas (uniao).
        adicionar("nome", set.intersection(*conjuntos) or set.union(*conjuntos))

    restantes = [
        token
        for token in restantes
        if not (token in PALAVRA_CHAVE_COLUNA and PALAVRA_CHAVE_COLUNA[token] in filtros)
    ]
    return restantes, filtros


def analisar(consulta: str, corretor: CorretorOrtografico, nomes: dict[str, set[str]]) -> Analise:
    """Executa o pipeline completo sobre a frase digitada."""
    analise = Analise(original=consulta)
    analise.normalizado = normalizar(consulta)

    texto, faixas = extrair_idades(analise.normalizado)
    analise.tokens = tokenizar(texto)

    corrigidos = []
    for token in analise.tokens:
        correto = corretor.corrigir(token)
        if correto != token:
            analise.correcoes[token] = correto
        corrigidos.append(correto)

    sem_stopwords = [t for t in _juntar_expressoes(corrigidos) if t not in STOPWORDS]
    analise.sem_stopwords = sem_stopwords
    analise.tem_negacao = any(t in NEGACOES for t in sem_stopwords)

    analise.formas_finais, analise.filtros = extrair_filtros(
        [t for t in sem_stopwords if t not in NEGACOES], faixas, nomes
    )
    analise.tokens_finais = [radical(t) for t in analise.formas_finais]
    if analise.filtros:
        # Um marcador so, para que a quantidade de filtros nao altere a similaridade.
        analise.tokens_finais.append(FILTRO)
    return analise
