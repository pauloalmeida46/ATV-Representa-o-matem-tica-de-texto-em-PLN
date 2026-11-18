"""Testes do motor de PLN (nao precisam de banco de dados).

Execucao, a partir da pasta PC7:  python -m unittest discover -s tests -t .
"""

import unittest

from pln.motor import LIMIAR_SIMILARIDADE, MotorBusca, montar_sql, montar_where

NOMES = ["Ana Beatriz Souza", "João Pedro Almeida", "Maria Eduarda Santos", "Hiroshi Tanaka"]
motor = MotorBusca(NOMES)


def interpretar(consulta: str):
    analise = motor.analisar(consulta)
    tokens_bow, _ignorados = motor.vetorizar(analise)
    referencia, similaridade = motor.ranquear(tokens_bow)[0]
    entendido = bool(tokens_bow) and similaridade >= LIMIAR_SIMILARIDADE
    return referencia, entendido, analise.filtros


class TestIntencoes(unittest.TestCase):
    def verificar(self, consulta, acao, filtros=None, coluna=None):
        referencia, entendido, encontrados = interpretar(consulta)
        self.assertTrue(entendido, f"{consulta!r} nao foi entendida")
        self.assertEqual(referencia.acao, acao, consulta)
        self.assertEqual(encontrados, filtros or {}, consulta)
        if coluna:
            self.assertEqual(referencia.coluna_grupo, coluna, consulta)

    def test_exemplos_do_enunciado(self):
        self.verificar("Quantas imagens estão catalogadas?", "contar")
        self.verificar("Há quantas imagens?", "contar")
        self.verificar("Quais imagens possuem cabelo ruivo?", "listar", {"cor_cabelo": {"ruivo"}})

    def test_contagem(self):
        self.verificar("quantas pessoas estão cadastradas", "contar")
        self.verificar("qual o total de pessoas?", "contar")
        self.verificar("número de fotos", "contar")
        self.verificar("quantas pessoas têm cabelo loiro?", "contar", {"cor_cabelo": {"loiro"}})
        self.verificar("quantas loiras tem?", "contar", {"cor_cabelo": {"loiro"}})
        self.verificar("quantos idosos existem", "contar", {"faixa_etaria": {"60+"}})

    def test_listagem(self):
        self.verificar("mostre todas as pessoas", "listar")
        self.verificar("quem está cadastrado?", "listar")
        self.verificar("loiras", "listar", {"cor_cabelo": {"loiro"}})
        self.verificar("quero ver as pessoas de etnia parda", "listar", {"etnia": {"parda"}})
        self.verificar("tem alguém ruivo?", "listar", {"cor_cabelo": {"ruivo"}})
        self.verificar("me mostre os adolescentes", "listar", {"faixa_etaria": {"13-17"}})
        self.verificar(
            "exiba as crianças indígenas",
            "listar",
            {"faixa_etaria": {"0-5", "6-12"}, "etnia": {"indígena"}},
        )
        self.verificar(
            "pessoas pardas de cabelo castanho entre 30 e 44 anos",
            "listar",
            {"etnia": {"parda"}, "cor_cabelo": {"castanho"}, "faixa_etaria": {"30-44"}},
        )

    def test_varios_valores_no_mesmo_atributo(self):
        self.verificar("pessoas loiras ou ruivas", "listar", {"cor_cabelo": {"loiro", "ruivo"}})
        self.verificar("quantas pessoas negras?", "contar", {"etnia": {"preta", "parda"}})

    def test_preto_e_branco_dependem_do_contexto(self):
        self.verificar("pessoas pretas", "listar", {"etnia": {"preta"}})
        self.verificar("pessoas de cabelo preto", "listar", {"cor_cabelo": {"preto"}})
        self.verificar("pessoas de cabelo de cor preta", "listar", {"cor_cabelo": {"preto"}})
        self.verificar("pessoas brancas", "listar", {"etnia": {"branca"}})
        self.verificar("cabelos brancos", "listar", {"cor_cabelo": {"grisalho"}})
        self.verificar(
            "pessoas pretas de cabelo preto", "listar", {"etnia": {"preta"}, "cor_cabelo": {"preto"}}
        )
        self.verificar(
            "pessoas de cabelo preto e brancas", "listar", {"cor_cabelo": {"preto"}, "etnia": {"branca"}}
        )
        self.verificar("cabelo loiro ou preto", "listar", {"cor_cabelo": {"loiro", "preto"}})

    def test_idades_numericas(self):
        self.verificar("pessoas de 6 a 12 anos", "listar", {"faixa_etaria": {"6-12"}})
        self.verificar("pessoas com 8 anos", "listar", {"faixa_etaria": {"6-12"}})
        self.verificar("faixa 18-29", "listar", {"faixa_etaria": {"18-29"}})
        self.verificar("quantas pessoas com mais de 60 anos", "contar", {"faixa_etaria": {"60+"}})
        self.verificar("pessoas com 60 anos ou mais", "listar", {"faixa_etaria": {"60+"}})
        self.verificar(
            "pessoas com menos de 18 anos", "listar", {"faixa_etaria": {"0-5", "6-12", "13-17"}}
        )
        self.verificar("pessoas de meia-idade", "listar", {"faixa_etaria": {"45-59"}})
        self.verificar("mostre os menores de idade", "listar", {"faixa_etaria": {"0-5", "6-12", "13-17"}})

    def test_agrupamentos(self):
        self.verificar("quais etnias existem?", "agrupar", coluna="etnia")
        self.verificar("quantas pessoas por cor de cabelo?", "agrupar", coluna="cor_cabelo")
        self.verificar("quantas pessoas por faixa etária", "agrupar", coluna="faixa_etaria")
        self.verificar(
            "quantas pessoas loiras por etnia", "agrupar", {"cor_cabelo": {"loiro"}}, coluna="etnia"
        )

    def test_nomes(self):
        ana = {"Ana Beatriz Souza"}
        self.verificar("mostre a foto da Ana", "listar", {"nome": ana})
        self.verificar("quem é Ana Beatriz Souza?", "listar", {"nome": ana})
        self.verificar("qual a etnia da Ana?", "listar", {"nome": ana})
        self.verificar("Joao Pedro", "listar", {"nome": {"João Pedro Almeida"}})
        self.verificar(
            "mostre a Ana e o Hiroshi", "listar", {"nome": {"Ana Beatriz Souza", "Hiroshi Tanaka"}}
        )


class TestErrosDeDigitacao(unittest.TestCase):
    def test_correcoes(self):
        casos = {
            "qunatas pesoas tem cabelo loro?": ("contar", {"cor_cabelo": {"loiro"}}),
            "mosttre as pessoas ruibas": ("listar", {"cor_cabelo": {"ruivo"}}),
            "qunatos idozos": ("contar", {"faixa_etaria": {"60+"}}),
            "quantas pesoas indijenas": ("contar", {"etnia": {"indígena"}}),
            "cabeo grizalho": ("listar", {"cor_cabelo": {"grisalho"}}),
            "adolecentes pardos": ("listar", {"faixa_etaria": {"13-17"}, "etnia": {"parda"}}),
            "CABELO CASTANO": ("listar", {"cor_cabelo": {"castanho"}}),
            "mostre a foto da Mraia": ("listar", {"nome": {"Maria Eduarda Santos"}}),
        }
        for consulta, (acao, filtros) in casos.items():
            with self.subTest(consulta=consulta):
                referencia, entendido, encontrados = interpretar(consulta)
                self.assertTrue(entendido)
                self.assertEqual(referencia.acao, acao)
                self.assertEqual(encontrados, filtros)

    def test_palavra_correta_nao_e_alterada(self):
        self.assertEqual(motor.analisar("mostrem os homens").correcoes, {})


class TestForaDeEscopo(unittest.TestCase):
    def test_frases_rejeitadas(self):
        for consulta in (
            "qual a capital da França?",
            "gosto de pizza",
            "mostre o carro",
            "quantas bananas?",
            "previsão do tempo para amanhã",
            "???",
            "de que para",
        ):
            with self.subTest(consulta=consulta):
                self.assertFalse(interpretar(consulta)[1])

    def test_negacao_e_sinalizada(self):
        analise = motor.analisar("pessoas que não são loiras")
        self.assertTrue(analise.tem_negacao)
        self.assertEqual(analise.filtros, {"cor_cabelo": {"loiro"}})


class TestSql(unittest.TestCase):
    def test_valores_vao_como_parametros(self):
        where, parametros = montar_where({"etnia": {"parda", "preta"}, "cor_cabelo": {"loiro"}})
        self.assertEqual(where, " WHERE etnia = ANY(%s) AND cor_cabelo = ANY(%s)")
        self.assertEqual(parametros, [["parda", "preta"], ["loiro"]])

    def test_contagem_sem_filtro(self):
        referencia = interpretar("quantas pessoas")[0]
        self.assertEqual(montar_sql(referencia, {})[0], "SELECT COUNT(*) AS total FROM metadata_pessoas;")


if __name__ == "__main__":
    unittest.main()
