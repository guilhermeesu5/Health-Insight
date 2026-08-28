CREATE TABLE estabelecimentos (
    id             NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo_cnes    VARCHAR2(20)  NOT NULL UNIQUE,
    nome           VARCHAR2(200) NOT NULL,
    municipio      VARCHAR2(120) NOT NULL,
    uf             CHAR(2)       NOT NULL,
    regiao         VARCHAR2(20)  NOT NULL,
    tipo           VARCHAR2(40),
    natureza       VARCHAR2(40),
    leitos_totais  NUMBER        NOT NULL
);

CREATE TABLE procedimentos (
    id       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo   VARCHAR2(20)  NOT NULL UNIQUE,
    nome     VARCHAR2(200) NOT NULL,
    tipo     VARCHAR2(40)  NOT NULL  -- clinico, cirurgico, obstetrico, psiquiatrico, outros
);

CREATE TABLE internacoes (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    data_internacao      DATE          NOT NULL,
    estabelecimento_id   NUMBER        NOT NULL REFERENCES estabelecimentos(id),
    procedimento_id      NUMBER        NOT NULL REFERENCES procedimentos(id),
    dias_permanencia     NUMBER        NOT NULL,
    valor_total          NUMBER(12,2)
);

CREATE INDEX idx_internacoes_data  ON internacoes(data_internacao);
CREATE INDEX idx_internacoes_estab ON internacoes(estabelecimento_id);
CREATE INDEX idx_internacoes_proc  ON internacoes(procedimento_id);
