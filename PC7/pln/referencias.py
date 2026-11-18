"""Banco de consultas de referencia.

Cada referencia e uma consulta-modelo cuja resposta e SQL ja sao conhecidos.
O marcador <filtro> representa qualquer valor de metadado citado na frase
("loira", "parda", "6-12", "Ana"). Assim, poucas frases-modelo cobrem todas as
combinacoes de valores.
"""

from dataclasses import dataclass

FILTRO = "<filtro>"

LISTAR = "listar"
CONTAR = "contar"
AGRUPAR = "agrupar"


@dataclass(frozen=True)
class Referencia:
    texto: str
    acao: str
    coluna_grupo: str | None = None


# O imperativo entra junto do infinitivo para que o corretor reconheca "mostre"
# com erro de digitacao; depois do stemming as duas formas sao o mesmo termo.
_VERBOS_LISTAR = (
    "mostrar", "mostre", "exibir", "exiba", "listar", "liste", "ver", "veja", "visualizar",
    "buscar", "busque", "procurar", "procure", "encontrar", "encontre", "selecionar",
    "selecione", "filtrar", "filtre", "apresentar", "apresente", "trazer", "traga",
    "quais", "quem",
)
_PREFIXOS_CONTAR = (
    "quantas", "total", "qual total", "numero", "qual numero",
    "quantidade", "qual quantidade", "contar",
)
_ATRIBUTOS = (("etnias", "etnia"), ("cabelos", "cor_cabelo"), ("idades", "faixa_etaria"))


def montar_referencias() -> list[Referencia]:
    # Em empate de similaridade vence a primeira da lista, por isso "listar" vem antes.
    referencias = [
        Referencia("pessoas", LISTAR),
        Referencia(FILTRO, LISTAR),
        Referencia(f"pessoas {FILTRO}", LISTAR),
    ]

    for verbo in _VERBOS_LISTAR:
        for modelo in (
            f"{verbo} pessoas",
            f"{verbo} pessoas cadastradas",
            f"{verbo} pessoas {FILTRO}",
            f"{verbo} {FILTRO}",
        ):
            referencias.append(Referencia(modelo, LISTAR))

    # "Qual a etnia da Ana?": o cartao da pessoa ja traz o dado pedido.
    for palavra, _coluna in _ATRIBUTOS:
        referencias.append(Referencia(f"qual {palavra} {FILTRO}", LISTAR))

    # "Quantas" sozinho nao entra: faria "quantas bananas?" responder o total de pessoas.
    referencias += [Referencia("total", CONTAR), Referencia("qual total", CONTAR)]
    for prefixo in _PREFIXOS_CONTAR:
        for modelo in (
            f"{prefixo} pessoas",
            f"{prefixo} pessoas cadastradas",
            f"{prefixo} pessoas catalogadas",
            f"{prefixo} pessoas existem",
            f"{prefixo} pessoas {FILTRO}",
            f"{prefixo} {FILTRO}",
        ):
            referencias.append(Referencia(modelo, CONTAR))

    for palavra, coluna in _ATRIBUTOS:
        for modelo in (
            palavra,
            f"quais {palavra}",
            f"quais {palavra} existem",
            f"quais {palavra} cadastradas",
            f"quais {palavra} pessoas",
            f"listar {palavra}",
            f"mostrar {palavra}",
            f"quantas {palavra}",
            f"quantas {palavra} existem",
            f"distribuicao {palavra}",
            f"quantas pessoas {palavra}",
            f"total pessoas {palavra}",
            f"contar pessoas {palavra}",
            f"agrupar pessoas {palavra}",
            f"distribuicao pessoas {palavra}",
            f"quantas pessoas {FILTRO} {palavra}",
            f"distribuicao pessoas {FILTRO} {palavra}",
        ):
            referencias.append(Referencia(modelo, AGRUPAR, coluna))

    return referencias
