const formulario = document.querySelector("#form-busca");
const campo = document.querySelector("#consulta");
const botao = formulario.querySelector("button");
const resultado = document.querySelector("#resultado");
const mensagem = document.querySelector("#mensagem");
const avisos = document.querySelector("#avisos");
const grade = document.querySelector("#grade");
const grupos = document.querySelector("#grupos");
const painel = document.querySelector("#painel");
const passos = document.querySelector("#passos");

function criar(tag, classe, texto) {
  const elemento = document.createElement(tag);
  if (classe) elemento.className = classe;
  if (texto !== undefined) elemento.textContent = texto;
  return elemento;
}

function criarCartao(pessoa) {
  const cartao = criar("article", "cartao");

  const foto = criar("img", "foto");
  foto.src = pessoa.imagem_url;
  foto.alt = `Imagem de ${pessoa.nome}`;
  foto.loading = "lazy";

  const dados = criar("dl", "dados");
  for (const [rotulo, valor] of [
    ["Etnia", pessoa.etnia],
    ["Cabelo", pessoa.cor_cabelo],
    ["Faixa etária", pessoa.faixa_etaria],
  ]) {
    dados.append(criar("dt", "", rotulo), criar("dd", "", valor));
  }

  const corpo = criar("div", "corpo");
  corpo.append(criar("h3", "nome", pessoa.nome), dados);
  cartao.append(foto, corpo);
  return cartao;
}

function renderizarGrupos(linhas) {
  const maior = Math.max(...linhas.map((linha) => linha.total), 1);
  for (const linha of linhas) {
    const item = criar("div", "grupo");
    const trilha = criar("div", "trilha");
    const barra = criar("div", "barra");
    barra.style.width = `${(linha.total / maior) * 100}%`;
    trilha.append(barra);
    item.append(criar("span", "categoria", linha.categoria), trilha, criar("span", "total", linha.total));
    grupos.append(item);
  }
}

function renderizarAvisos(dados) {
  const correcoes = Object.entries(dados.correcoes).map(([errado, certo]) => `${errado} → ${certo}`);
  if (correcoes.length) avisos.append(criar("li", "", `Corrigi: ${correcoes.join(", ")}`));
  if (dados.entendido && dados.ignorados.length) {
    avisos.append(criar("li", "", `Não considerei: ${dados.ignorados.join(", ")}`));
  }
}

function criarPasso(passo) {
  const item = criar("li", "passo");
  item.append(criar("h3", "", passo.titulo));

  if (passo.valor !== undefined) item.append(criar("p", "valor", passo.valor));

  if (passo.itens) {
    if (passo.itens.length) {
      const lista = criar("div", "fichas");
      passo.itens.forEach((texto) => lista.append(criar("span", "ficha", texto)));
      item.append(lista);
    } else {
      item.append(criar("p", "valor vazio", passo.vazio || "nenhum"));
    }
  }

  if (passo.ranking) {
    const tabela = criar("table", "ranking");
    const cabecalho = criar("tr");
    ["Referência", "Ação", "Cosseno"].forEach((titulo) => cabecalho.append(criar("th", "", titulo)));
    tabela.append(cabecalho);
    for (const linha of passo.ranking) {
      const tr = criar("tr");
      tr.append(criar("td", "", linha.texto), criar("td", "", linha.acao), criar("td", "numero", linha.similaridade.toFixed(3)));
      tabela.append(tr);
    }
    item.append(tabela);
  }

  if (passo.codigo) {
    item.append(criar("code", "codigo", passo.codigo));
    if (passo.parametros) item.append(criar("p", "valor", `Parâmetros: ${JSON.stringify(passo.parametros)}`));
  }
  return item;
}

function limpar() {
  avisos.replaceChildren();
  grade.replaceChildren();
  grupos.replaceChildren();
  passos.replaceChildren();
}

function renderizar(dados) {
  limpar();
  resultado.hidden = false;
  mensagem.textContent = dados.mensagem;
  mensagem.classList.toggle("nao-entendido", !dados.entendido);
  renderizarAvisos(dados);
  grade.append(...dados.pessoas.map(criarCartao));
  renderizarGrupos(dados.grupos);
  passos.append(...dados.passos.map(criarPasso));
  painel.hidden = false;
}

function mostrarErro(texto) {
  limpar();
  resultado.hidden = false;
  painel.hidden = true;
  mensagem.textContent = texto;
  mensagem.classList.add("nao-entendido");
}

async function buscar(consulta) {
  botao.disabled = true;
  try {
    const resposta = await fetch("/api/buscar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ consulta }),
    });
    const dados = await resposta.json();
    if (resposta.ok) renderizar(dados);
    else mostrarErro(dados.erro);
  } catch {
    mostrarErro("Não consegui falar com o servidor. Verifique se a aplicação está em execução.");
  } finally {
    botao.disabled = false;
  }
}

formulario.addEventListener("submit", (evento) => {
  evento.preventDefault();
  const consulta = campo.value.trim();
  if (consulta) buscar(consulta);
});

document.querySelectorAll(".exemplo").forEach((exemplo) => {
  exemplo.addEventListener("click", () => {
    campo.value = exemplo.textContent;
    buscar(campo.value);
  });
});
