CREATE TABLE IF NOT EXISTS condominio (
    id_condominio SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    cnpj TEXT NOT NULL UNIQUE,
    endereco TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ativo'
);

CREATE TABLE IF NOT EXISTS usuario (
    id_usuario SERIAL PRIMARY KEY,
    nome_completo TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    tipo_usuario TEXT NOT NULL CHECK(tipo_usuario IN ('administrador', 'proprietario', 'procurador')),
    ativo INTEGER NOT NULL DEFAULT 1 CHECK(ativo IN (0,1))
);

CREATE TABLE IF NOT EXISTS lote (
    id_lote SERIAL PRIMARY KEY,
    id_condominio INTEGER NOT NULL REFERENCES condominio(id_condominio),
    id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario),
    identificacao TEXT NOT NULL,
    peso_original NUMERIC(10,2) NOT NULL CHECK(peso_original > 0),
    inadimplente INTEGER NOT NULL DEFAULT 0 CHECK(inadimplente IN (0,1)),
    UNIQUE(id_condominio, identificacao)
);

CREATE TABLE IF NOT EXISTS reuniao (
    id_reuniao SERIAL PRIMARY KEY,
    id_condominio INTEGER NOT NULL REFERENCES condominio(id_condominio),
    titulo TEXT NOT NULL,
    data TEXT NOT NULL,
    hora TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('agendada', 'em_andamento', 'encerrada'))
);

CREATE TABLE IF NOT EXISTS convidado_reuniao (
    id_convidado SERIAL PRIMARY KEY,
    id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario),
    id_reuniao INTEGER NOT NULL REFERENCES reuniao(id_reuniao),
    status_convite TEXT NOT NULL DEFAULT 'confirmado',
    status_presenca INTEGER NOT NULL DEFAULT 0 CHECK(status_presenca IN (0,1)),
    data_hora_entrada TIMESTAMP,
    data_hora_saida TIMESTAMP,
    UNIQUE(id_usuario, id_reuniao)
);

CREATE TABLE IF NOT EXISTS pauta (
    id_pauta SERIAL PRIMARY KEY,
    id_reuniao INTEGER NOT NULL REFERENCES reuniao(id_reuniao),
    assunto TEXT NOT NULL,
    descricao TEXT
);

CREATE TABLE IF NOT EXISTS votacao (
    id_votacao SERIAL PRIMARY KEY,
    id_pauta INTEGER NOT NULL REFERENCES pauta(id_pauta),
    assunto TEXT NOT NULL,
    pergunta TEXT NOT NULL,
    tipo_votacao TEXT NOT NULL CHECK(tipo_votacao IN ('aberta', 'fechada')),
    tipo_resposta TEXT NOT NULL DEFAULT 'escolha_unica',
    tempo_resposta INTEGER NOT NULL CHECK(tempo_resposta > 0),
    max_marcacoes INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL CHECK(status IN ('agendada', 'ativa', 'encerrada', 'invalidada')) DEFAULT 'agendada',
    iniciou_em TIMESTAMP,
    encerra_em TIMESTAMP,
    encerrada_em TIMESTAMP
);

CREATE TABLE IF NOT EXISTS opcao_voto (
    id_opcao SERIAL PRIMARY KEY,
    id_votacao INTEGER NOT NULL REFERENCES votacao(id_votacao),
    descricao TEXT NOT NULL,
    ordem INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS voto (
    id_voto SERIAL PRIMARY KEY,
    id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario),
    id_votacao INTEGER NOT NULL REFERENCES votacao(id_votacao),
    data_hora_voto TIMESTAMP NOT NULL,
    peso_aplicado NUMERIC(10,2) NOT NULL,
    ip TEXT,
    navegador TEXT,
    UNIQUE(id_usuario, id_votacao)
);

CREATE TABLE IF NOT EXISTS voto_escolha (
    id_voto_escolha SERIAL PRIMARY KEY,
    id_voto INTEGER NOT NULL REFERENCES voto(id_voto),
    id_opcao INTEGER NOT NULL REFERENCES opcao_voto(id_opcao),
    UNIQUE(id_voto, id_opcao)
);

CREATE TABLE IF NOT EXISTS log_auditoria (
    id_log SERIAL PRIMARY KEY,
    id_usuario INTEGER REFERENCES usuario(id_usuario),
    acao TEXT NOT NULL,
    entidade TEXT NOT NULL,
    data_hora TIMESTAMP NOT NULL,
    ip TEXT,
    navegador TEXT
);
