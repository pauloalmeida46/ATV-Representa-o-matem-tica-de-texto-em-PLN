"""Roda o TC.3 e o PC.7 com um unico comando.

Execucao:  python rodar.py   (no Windows, tambem da para dar dois cliques em rodar.bat)

Etapas: instala as dependencias em um ambiente virtual, liga o PostgreSQL, carrega as
30 pessoas no banco, mostra o resultado do TC.3 e abre a aplicacao do PC.7 no navegador.

Sem o arquivo PC7/.env, usa um PostgreSQL proprio, baixado na primeira execucao, que fica
ligado somente enquanto este script roda. Com PC7/.env, usa o servidor indicado nele.

O ambiente virtual e o banco ficam em ~/.pln_tc3_pc7, fora da pasta do trabalho. Este
arquivo usa somente a biblioteca padrao porque roda antes de qualquer instalacao.
"""

import hashlib
import os
import shutil
import socket
import subprocess
import sys
import time
import venv
import webbrowser
from pathlib import Path

VERSAO_MINIMA = (3, 12)  # exigida pelo numpy de PC7/requirements.txt
PACOTE_POSTGRES = "pgserver==0.1.4"  # distribui os executaveis do PostgreSQL 16
PORTA_APLICACAO = 5000
ENDERECO_LOCAL = "127.0.0.1"

RAIZ = Path(__file__).resolve().parent
TC3 = RAIZ / "TC3"
PC7 = RAIZ / "PC7"



def escolher_pasta_local() -> Path:
    base = Path.home()
    # No Windows, o initdb do PostgreSQL falha se o caminho da instalacao tiver acento.
    if os.name == "nt" and not str(base).isascii():
        base = Path(os.environ.get("ProgramData", r"C:\ProgramData"))
    return base / ".pln_tc3_pc7"


PASTA_LOCAL = escolher_pasta_local()
VENV = PASTA_LOCAL / "venv"
PYTHON = VENV / "Scripts" / "python.exe" if os.name == "nt" else VENV / "bin" / "python"
CARIMBO = VENV / "dependencias_instaladas.txt"
PG_INSTALACAO = PASTA_LOCAL / "postgres"
PG_BIN = PG_INSTALACAO / "pgserver" / "pginstall" / "bin"
PG_DADOS = PASTA_LOCAL / "pgdata"
PG_LOG = PASTA_LOCAL / "postgres.log"
SAIDA_COMANDO = PASTA_LOCAL / "ultimo_comando.log"

ERRO_POSTGRES = (
    "Não consegui ligar o PostgreSQL próprio do script. Como alternativa, instale o PostgreSQL,\n"
    "copie PC7/.env.example para PC7/.env, coloque a senha nele e rode este script de novo."
)


class Falha(Exception):
    """Problema que o usuario consegue resolver; a mensagem diz como."""


def etapa(texto: str) -> None:
    print(f"\n=== {texto}", flush=True)


def ultimas_linhas(arquivo: Path, quantidade: int = 15) -> str:
    try:
        linhas = arquivo.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(linhas[-quantidade:])


def em_silencio(comando: list, erro: str) -> None:
    """Executa um comando e so mostra a saida dele se falhar."""
    try:
        with open(SAIDA_COMANDO, "w", encoding="utf-8") as saida:
            concluido = subprocess.run(comando, stdin=subprocess.DEVNULL, stdout=saida, stderr=subprocess.STDOUT)
    except OSError as problema:
        raise Falha(f"{erro}\n\n{problema}")
    if concluido.returncode != 0:
        raise Falha(f"{erro}\n\n{ultimas_linhas(SAIDA_COMANDO)}")


def visivel(comando: list, pasta: Path, ambiente: dict, erro: str) -> None:
    """Executa um comando mostrando a saida dele no terminal."""
    if subprocess.run(comando, cwd=pasta, env=ambiente).returncode != 0:
        raise Falha(erro)


def porta_livre(preferida: int = 0) -> int:
    """Devolve a porta preferida, se estiver livre, ou outra escolhida pelo sistema."""
    for porta in (preferida, 0):
        with socket.socket() as teste:
            try:
                teste.bind((ENDERECO_LOCAL, porta))
            except OSError:
                continue
            return teste.getsockname()[1]
    raise Falha("Não encontrei uma porta local livre.")


def python_pronto(impressao: str) -> bool:
    try:
        return (
            CARIMBO.read_text(encoding="utf-8") == impressao
            and subprocess.run([PYTHON, "-c", ""], capture_output=True).returncode == 0
        )
    except OSError:
        return False


def preparar_python() -> None:
    requisitos = (TC3 / "requirements.txt", PC7 / "requirements.txt")
    impressao = hashlib.sha256(b"".join(arquivo.read_bytes() for arquivo in requisitos)).hexdigest()
    if python_pronto(impressao):
        return

    etapa("Instalando as dependências (só na primeira vez; pode levar alguns minutos)")
    try:
        venv.create(VENV, with_pip=True, clear=True)
    except (subprocess.CalledProcessError, OSError) as problema:
        raise Falha(
            f"Não consegui criar o ambiente virtual em {VENV}.\n"
            f"No Debian ou Ubuntu, instale o pacote python3-venv.\n\n{problema}"
        )

    comando = [PYTHON, "-m", "pip", "install", "--disable-pip-version-check", "--only-binary=:all:"]
    for arquivo in requisitos:
        comando += ["-r", arquivo]
    erro = "Não consegui instalar as dependências. Confira a conexão com a internet."
    if sys.version_info[:2] != (3, 12):
        erro += f"\nO trabalho foi testado no Python 3.12 e você está usando o {sys.version.split()[0]}."
    em_silencio(comando, erro)
    CARIMBO.write_text(impressao, encoding="utf-8")


def desligar_postgres() -> None:
    if PG_BIN.is_dir():
        subprocess.run(
            [PG_BIN / "pg_ctl", "-D", PG_DADOS, "-m", "fast", "-w", "stop"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def ligar_postgres() -> dict:
    """Liga o PostgreSQL proprio do script e devolve as variaveis para conectar nele."""
    if not PG_BIN.is_dir():
        etapa("Baixando o PostgreSQL (só na primeira vez)")
        # O pacote so publica versoes ate o Python 3.12, mas aqui interessam apenas os
        # executaveis do PostgreSQL, que nao dependem do Python em uso.
        em_silencio(
            [
                PYTHON, "-m", "pip", "install", "--disable-pip-version-check", "--target", PG_INSTALACAO,
                "--no-deps", "--only-binary=:all:", "--python-version", "3.12", PACOTE_POSTGRES,
            ],
            f"{ERRO_POSTGRES}\n\nO download falhou:",
        )

    etapa("Ligando o PostgreSQL")
    if not (PG_DADOS / "PG_VERSION").exists():
        shutil.rmtree(PG_DADOS, ignore_errors=True)
        em_silencio([PG_BIN / "initdb", "-D", PG_DADOS, "-U", "postgres", "-A", "trust", "-E", "UTF8"], ERRO_POSTGRES)

    desligar_postgres()  # pode ter sobrado de uma execucao interrompida
    porta = str(porta_livre())
    # A saida nao pode ir para um pipe: o processo do servidor o manteria aberto e o script travaria.
    iniciado = subprocess.run(
        [PG_BIN / "pg_ctl", "-D", PG_DADOS, "-l", PG_LOG, "-o", f"-h {ENDERECO_LOCAL} -p {porta}", "-w", "start"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if iniciado.returncode == 0:
        for _ in range(60):
            if subprocess.run([PG_BIN / "pg_isready", "-q", "-h", ENDERECO_LOCAL, "-p", porta]).returncode == 0:
                return {
                    "PGHOST": ENDERECO_LOCAL,
                    "PGPORT": porta,
                    "PGUSER": "postgres",
                    "PGPASSWORD": "",
                    "PGDATABASE": "pc7_pessoas",
                }
            time.sleep(0.5)
    raise Falha(f"{ERRO_POSTGRES}\n\n{ultimas_linhas(PG_LOG)}")


def esperar_aplicacao(processo: subprocess.Popen, porta: int) -> None:
    limite = time.monotonic() + 60
    while time.monotonic() < limite:
        if processo.poll() is not None:
            raise Falha("A aplicação não iniciou; veja a mensagem acima.")
        try:
            socket.create_connection((ENDERECO_LOCAL, porta), timeout=1).close()
            return
        except OSError:
            time.sleep(0.3)
    raise Falha("A aplicação demorou demais para iniciar.")


def abrir_aplicacao(ambiente: dict) -> None:
    porta = porta_livre(PORTA_APLICACAO)
    url = f"http://{ENDERECO_LOCAL}:{porta}"
    etapa(f"PC.7: aplicação em {url} (Ctrl+C encerra tudo)")
    processo = subprocess.Popen(
        [PYTHON, "-m", "flask", "--app", "app", "run", "--port", str(porta)], cwd=PC7, env=ambiente
    )
    try:
        esperar_aplicacao(processo, porta)
        webbrowser.open(url)
        while processo.poll() is None:
            time.sleep(0.5)
    finally:
        if processo.poll() is None:
            processo.terminate()
            processo.wait()
    raise Falha("A aplicação parou; veja a mensagem acima.")


def main() -> int:
    if sys.version_info < VERSAO_MINIMA:
        minima = ".".join(map(str, VERSAO_MINIMA))
        print(f"ERRO: é preciso ter o Python {minima} ou mais novo (encontrei o {sys.version.split()[0]}).", file=sys.stderr)
        print("Baixe em https://www.python.org/downloads/", file=sys.stderr)
        return 1

    PASTA_LOCAL.mkdir(parents=True, exist_ok=True)
    usa_postgres_proprio = not (PC7 / ".env").exists()
    ambiente = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}  # nao deixa __pycache__ na pasta do trabalho

    try:
        preparar_python()
        if usa_postgres_proprio:
            ambiente.update(ligar_postgres())
        else:
            etapa("Usando o PostgreSQL configurado em PC7/.env")

        etapa("Carregando as pessoas no banco")
        visivel([PYTHON, "init_db.py"], PC7, ambiente, "O banco não foi preparado; veja a mensagem acima.")

        etapa("TC.3: léxico e vetores n-gram")
        visivel([PYTHON, "tc3_ngrams.py"], TC3, ambiente, "O TC.3 falhou; veja a mensagem acima.")

        abrir_aplicacao(ambiente)
    except KeyboardInterrupt:
        pass
    except Falha as erro:
        print(f"\nERRO: {erro}", file=sys.stderr)
        return 1
    finally:
        if usa_postgres_proprio:
            desligar_postgres()

    print(f"\nEncerrado. Para liberar espaço, pode apagar a pasta {PASTA_LOCAL}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
