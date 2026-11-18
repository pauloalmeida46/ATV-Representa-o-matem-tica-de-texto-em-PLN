"""Conhecimento do dominio usado pelo pipeline de PLN.

Todas as palavras estao sem acento porque o pipeline remove os acentos antes de
consultar estes dicionarios.
"""

# Rotulo gravado no banco, idade minima e idade maxima de cada faixa.
FAIXAS_ETARIAS = (
    ("0-5", 0, 5),
    ("6-12", 6, 12),
    ("13-17", 13, 17),
    ("18-29", 18, 29),
    ("30-44", 30, 44),
    ("45-59", 45, 59),
    ("60+", 60, 150),
)

# Lista propria em vez da lista pronta do NLTK: as listas prontas removem
# "quais" e "quantas", justamente as palavras que definem a intencao da consulta.
STOPWORDS = set(
    """
    a o as os um uma uns umas ao aos
    de do da dos das em no na nos nas num numa
    por pelo pela pelos pelas para pra pro com que e ou se
    sao ser sera seria eh esta estao estar estava estavam foi foram sou somos
    tem tenho temos tenha tenham tinha tinham ha haver havia houver
    possui possuem possuir
    me mim meu minha meus minhas eu voce voces vc vcs ele ela eles elas
    isso isto aquilo esse essa esses essas este estes estas aquele aquela aqueles aquelas
    quero queria gostaria desejo preciso precisava poderia pode podem consegue
    favor obrigado obrigada cada todos todas todo toda tudo
    ai aqui la ja so somente apenas mais muito muita muitos muitas bem
    sistema banco dados base catalogo
    cor cores tom tons tonalidade tipo tipos faixa faixas
    nome nomes chama chamam chamado chamada chamados chamadas
    ano anos agora como onde qualquer algum alguma alguns algumas entre
    """.split()
)

# Filtro por exclusao nao e suportado; estas palavras disparam um aviso em vez
# de mostrar justamente o grupo que a pessoa quis excluir.
NEGACOES = {"nao", "sem", "exceto", "excluindo", "tirando", "menos"}

# Expressoes de varias palavras que viram um unico termo.
EXPRESSOES = {
    "todo mundo": "pessoas",
    "meia idade": "meiaidade",
    "terceira idade": "idosos",
    "melhor idade": "idosos",
    "menor de idade": "menoridade",
    "menores de idade": "menoridade",
    "maior de idade": "maioridade",
    "maiores de idade": "maioridade",
    "cor de pele": "etnia",
    "cor da pele": "etnia",
    "tom de pele": "etnia",
    "faixa etaria": "idade",
    "faixas etarias": "idade",
}


def _flexoes(*radicais: str) -> set[str]:
    return {radical + final for radical in radicais for final in ("o", "a", "os", "as")}


# Lematizacao por dicionario: variantes de um conceito viram uma palavra so.
SINONIMOS = {"quais": "qual"}
for _forma in """pessoa pessoas gente alguem foto fotos fotografia fotografias
                 imagem imagens retrato retratos registro registros individuo individuos""".split():
    SINONIMOS[_forma] = "pessoa"
for _forma in ("cabelo", "cabelos", "fios"):
    SINONIMOS[_forma] = "cabelo"
for _forma in ("etnia", "etnias", "raca", "racas", "pele"):
    SINONIMOS[_forma] = "etnia"
for _forma in ("idade", "idades", "etaria", "etarias", "etario", "etarios"):
    SINONIMOS[_forma] = "idade"

# Palavra-chave do atributo -> coluna do banco. Quando o valor aparece na frase
# ("etnia parda"), a palavra-chave some para nao parecer um agrupamento por etnia.
PALAVRA_CHAVE_COLUNA = {"etnia": "etnia", "cabelo": "cor_cabelo", "idade": "faixa_etaria"}

# Forma escrita -> (coluna, valores no banco).
VALORES: dict[str, tuple[str, tuple[str, ...]]] = {}


def _registrar(formas: set[str], coluna: str, *valores: str) -> None:
    for forma in formas:
        VALORES[forma] = (coluna, valores)


_registrar(_flexoes("loir", "lour"), "cor_cabelo", "loiro")
_registrar(_flexoes("ruiv"), "cor_cabelo", "ruivo")
_registrar(_flexoes("grisalh"), "cor_cabelo", "grisalho")
_registrar(_flexoes("castanh"), "cor_cabelo", "castanho")

_registrar(_flexoes("pard"), "etnia", "parda")
_registrar(_flexoes("amarel", "asiatic") | {"oriental", "orientais"}, "etnia", "amarela")
_registrar({"indigena", "indigenas", "indio", "india", "indios", "indias"}, "etnia", "indígena")
_registrar(_flexoes("caucasian"), "etnia", "branca")
# IBGE: a populacao negra corresponde a soma de pretos e pardos.
_registrar({"afrodescendente", "afrodescendentes"}, "etnia", "preta", "parda")

_registrar({"bebe", "bebes"}, "faixa_etaria", "0-5")
_registrar({"crianca", "criancas"}, "faixa_etaria", "0-5", "6-12")
_registrar({"adolescente", "adolescentes"}, "faixa_etaria", "13-17")
_registrar({"jovem", "jovens"}, "faixa_etaria", "18-29")
_registrar(_flexoes("adult"), "faixa_etaria", "18-29", "30-44", "45-59")
_registrar({"meiaidade"}, "faixa_etaria", "45-59")
_registrar(_flexoes("idos", "velh"), "faixa_etaria", "60+")
_registrar({"menoridade"}, "faixa_etaria", "0-5", "6-12", "13-17")
_registrar({"maioridade"}, "faixa_etaria", "18-29", "30-44", "45-59", "60+")

# "Preto" e "branco" servem para etnia e para cabelo; o contexto decide.
# Forma escrita -> (valor de cabelo, valores de etnia).
CORES_AMBIGUAS: dict[str, tuple[str, tuple[str, ...]]] = {}
for _forma in _flexoes("pret"):
    CORES_AMBIGUAS[_forma] = ("preto", ("preta",))
for _forma in _flexoes("negr"):
    CORES_AMBIGUAS[_forma] = ("preto", ("preta", "parda"))
for _forma in _flexoes("branc"):
    CORES_AMBIGUAS[_forma] = ("grisalho", ("branca",))
