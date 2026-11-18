# PLN – TC.3 e PC.7: Representação matemática de texto

Disciplina: Processamento de Linguagem Natural – Prof. Fabrício Galende Marques de Carvalho

Integrantes:

- José Eduardo Fernandes Pereira (RA 1461392321029)
- Eduardo Kuwahara Junior
- Paulo Henrique Martins de Almeida

Enunciado original: [`PLN TC.3 e PC.7.pdf`](<PLN TC.3 e PC.7.pdf>).

Este diretório reúne os dois exercícios da atividade "Representação matemática de texto em PLN":
TC.3 (léxico e vetores n-gram) e PC.7 (busca de pessoas em linguagem natural). Ambos exploram o
mesmo tema — como o pré-processamento decide o que um modelo de saco de palavras (BOW) consegue
representar.

## TC.3 – Léxico e vetores n-gram

Script (`TC3/tc3_ngrams.py`) que gera, para n = 1, 2 e 3, o léxico e os vetores de n-gramas de um
corpus de 4 frases sobre um produto (duas delas opostas em sentimento, duas parafraseando a mesma
opinião). Para cada n, imprime o léxico, os vetores de cada frase e a proporção de componentes
não nulas.

Conclusões do exercício:

- Aumentar n (de 1 para 3) reduz o léxico e deixa os vetores mais esparsos (45,8% → 31,3% de
  componentes não nulas).
- Com n maior, frases opostas ("bom" vs. "ruim") se separam melhor: cos(F2, F3) cai de 0,750
  para 0,500.
- Com n maior, paráfrases (mesma opinião em outra ordem) perdem a semelhança: cos(F3, F4) cai de
  0,671 para 0.
- Manter stopwords como "não" é necessário: removê-la eliminaria o bigrama "não gostei",
  decisivo para capturar negação.

Executar:

```powershell
cd TC3
python -m pip install -r requirements.txt
python tc3_ngrams.py
```

## PC.7 – Busca de pessoas em linguagem natural

Aplicação de página única (Flask + PostgreSQL) em que o usuário faz perguntas em português sobre
um banco de 30 pessoas fictícias (retrato ilustrado, nome, etnia, cor do cabelo e faixa etária). A
frase é convertida em saco de palavras (BOW), comparada por similaridade de cosseno com 207
consultas de referência (léxico de 33 termos), e a referência mais próxima define o SQL executado
— sem nunca concatenar o texto digitado à consulta.

Principais características do pipeline (normalização → tokenização → correção ortográfica por
distância OSA → remoção de stopwords → lematização por dicionário de domínio → stemming →
BOW → cosseno → SQL), exemplos de perguntas e limitações conhecidas (sem suporte a exclusão como
"não loiras", sem metadado de gênero, BOW não considera ordem das palavras) estão documentados na
interface da própria aplicação, no painel "Como o motor entendeu a frase".

Validado com 14 testes automáticos do motor, 35 perguntas via API com PostgreSQL real, teste de
interface (desktop e largura de celular) e tentativa de SQL injection recusada sem efeito na
tabela.

### Como executar

Com um comando, a partir do diretório principal:

```powershell
python rodar.py
```

ou, no Windows, dois cliques em `rodar.bat`. O script instala as dependências, sobe um PostgreSQL
16 próprio (ou usa o indicado em `PC7/.env`, se existir), carrega o banco de 30 pessoas, mostra o
resultado do TC.3 no terminal e abre o PC.7 no navegador em `http://127.0.0.1:5000`. Requer apenas
Python 3.12+ e, na primeira execução, internet; o ambiente virtual e o banco ficam em
`~/.pln_tc3_pc7` e podem ser apagados depois.

Para rodar o PC.7 manualmente (PowerShell, dentro de `PC7/`), com um PostgreSQL 16 já instalado:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
# edite .env com a senha do PostgreSQL (PGPASSWORD)
.venv\Scripts\python init_db.py
.venv\Scripts\python app.py
```

Testes do motor (não precisam de banco):

```powershell
.venv\Scripts\python -m unittest discover -s tests -t .
```

## Estrutura

```text
PLN TC.3 e PC.7.pdf   Enunciado da atividade
rodar.py, rodar.bat   Executa TC.3 e PC.7 com um comando
TC3/                  Exercício TC.3 (léxico e vetores n-gram)
  tc3_ngrams.py
  requirements.txt
PC7/                  Exercício PC.7 (busca de pessoas em linguagem natural)
  app.py              Rotas Flask
  banco.py            Acesso ao PostgreSQL
  config.py           Leitura do .env
  init_db.py          Criação do banco e importação do CSV
  db/schema.sql        Tabela metadata_pessoas
  data/pessoas.csv      Metadados das 30 pessoas
  pln/dominio.py          Stopwords, sinônimos e valores dos metadados
  pln/preprocessamento.py Etapas do pipeline
  pln/referencias.py      Consultas de referência
  pln/motor.py            BOW, cosseno e montagem do SQL
  static/, templates/   Interface
  tests/                 Testes do motor
```

## Imagens e dados (PC.7)

As 30 pessoas são fictícias e as imagens são retratos ilustrados, gerados a partir dos próprios
metadados. Fotos reais associadas a etnia são dados pessoais sensíveis (LGPD, art. 5º, II) e o
banco inclui crianças (art. 14), o que exigiria consentimento. A coluna `etnia` usa as categorias
de cor ou raça do IBGE: branca, preta, parda, amarela e indígena.

Para usar fotos com autorização: coloque os arquivos em `PC7/static/fotos/`, atualize
`arquivo_imagem` e os demais campos em `PC7/data/pessoas.csv` e rode `init_db.py` de novo.
