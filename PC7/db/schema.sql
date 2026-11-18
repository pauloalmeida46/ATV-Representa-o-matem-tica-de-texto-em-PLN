DROP TABLE IF EXISTS metadata_pessoas;

CREATE TABLE metadata_pessoas (
    id             SERIAL PRIMARY KEY,
    nome           TEXT NOT NULL,
    etnia          TEXT NOT NULL CHECK (etnia IN ('branca', 'preta', 'parda', 'amarela', 'indígena')),
    cor_cabelo     TEXT NOT NULL CHECK (cor_cabelo IN ('preto', 'castanho', 'loiro', 'ruivo', 'grisalho')),
    faixa_etaria   TEXT NOT NULL CHECK (faixa_etaria IN ('0-5', '6-12', '13-17', '18-29', '30-44', '45-59', '60+')),
    -- Caminho relativo a pasta static/
    arquivo_imagem TEXT NOT NULL
);
