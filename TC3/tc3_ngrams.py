"""TC.3 - Lexico e vetores de caracteristicas n-gram para n = 1, 2 e 3.

Execucao:     python tc3_ngrams.py
Dependencia:  scikit-learn
"""

from sklearn.feature_extraction.text import CountVectorizer

FRASES = {
    "Frase 1": "Eu não gostei do produto e o produto parece ruim.",
    "Frase 2": "O produto parece bom.",
    "Frase 3": "O produto parece ruim.",
    "Frase 4": "Parece muito ruim esse produto.",
}


def main() -> None:
    for n in (1, 2, 3):
        # O padrao do scikit-learn descarta palavras de uma letra, o que
        # eliminaria "e" e "o" do lexico; por isso o token_pattern e explicito.
        vetorizador = CountVectorizer(ngram_range=(n, n), token_pattern=r"(?u)\b\w+\b")
        matriz = vetorizador.fit_transform(FRASES.values()).toarray()
        lexico = list(vetorizador.get_feature_names_out())

        print(f"\n=== n = {n} | |lexico| = {len(lexico)} ===")
        print(lexico)
        for rotulo, vetor in zip(FRASES, matriz):
            print(f"{rotulo}: {vetor.tolist()}")

        nao_zeros = int((matriz > 0).sum())
        print(f"Componentes nao nulas: {nao_zeros}/{matriz.size} ({nao_zeros / matriz.size:.1%})")


if __name__ == "__main__":
    main()
