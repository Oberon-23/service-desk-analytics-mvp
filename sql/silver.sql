-- =====================================================================
-- CAMADA SILVER: limpeza + modelagem dimensional (Star Schema)
-- Entrada : bronze_events (tudo texto, + colunas de auditoria _*)
-- Saída   : stg_events, dim_*, fato_chamado
-- =====================================================================

-- 1) Staging: padroniza texto, converte tipos, remove duplicatas exatas
CREATE OR REPLACE TABLE stg_events AS
WITH dedup AS (
    SELECT DISTINCT * EXCLUDE (_ingested_at, _source_file) FROM bronze_events
),
clean AS (
    SELECT
        trim(number)                                              AS chamado_id,
        CASE lower(trim(incident_state))
            WHEN 'new'                  THEN 'Novo'
            WHEN 'active'               THEN 'Em atendimento'
            WHEN 'awaiting user info'   THEN 'Aguardando usuário'
            WHEN 'awaiting problem'     THEN 'Aguardando problema'
            WHEN 'awaiting vendor'      THEN 'Aguardando fornecedor'
            WHEN 'awaiting evidence'    THEN 'Aguardando evidência'
            WHEN 'resolved'             THEN 'Resolvido'
            WHEN 'closed'               THEN 'Fechado'
            ELSE 'Outro'
        END                                                       AS estado,
        TRY_CAST(reassignment_count AS INTEGER)                   AS reatribuicoes,
        TRY_CAST(reopen_count       AS INTEGER)                   AS reaberturas,
        TRY_CAST(sys_mod_count      AS INTEGER)                   AS qtd_atualizacoes,
        lower(trim(made_sla)) = 'true'                            AS sla_origem,
        strptime(NULLIF(trim(opened_at),   '?'), '%d/%m/%Y %H:%M') AS aberto_em,
        strptime(NULLIF(trim(sys_updated_at), '?'), '%d/%m/%Y %H:%M') AS atualizado_em,
        strptime(NULLIF(trim(resolved_at), '?'), '%d/%m/%Y %H:%M') AS resolvido_em,
        strptime(NULLIF(trim(closed_at),   '?'), '%d/%m/%Y %H:%M') AS fechado_em,
        upper(left(trim(contact_type), 1)) || lower(substr(trim(contact_type), 2)) AS canal,
        COALESCE(NULLIF(trim(category),    '?'), 'Não informado') AS categoria,
        COALESCE(NULLIF(trim(subcategory), '?'), 'Não informado') AS subcategoria,
        COALESCE(NULLIF(trim(assignment_group), '?'), 'Não informado') AS grupo,
        TRY_CAST(regexp_extract(priority, '^(\d)', 1) AS INTEGER) AS prioridade_cod,
        NULLIF(trim(location), '?')                               AS localidade,
        NULLIF(trim(problem_id), '?')                             AS problema_id
    FROM dedup
)
SELECT * FROM clean;

-- 2) Dimensões --------------------------------------------------------
CREATE OR REPLACE TABLE dim_prioridade AS
SELECT * FROM (VALUES
    (1, 'P1 - Crítica',  4),
    (2, 'P2 - Alta',     8),
    (3, 'P3 - Moderada', 24),
    (4, 'P4 - Baixa',    72)
) t(prioridade_cod, prioridade, sla_alvo_h);

CREATE OR REPLACE TABLE dim_categoria AS
SELECT row_number() OVER (ORDER BY categoria, subcategoria) AS categoria_sk, categoria, subcategoria
FROM (SELECT DISTINCT categoria, subcategoria FROM stg_events);

CREATE OR REPLACE TABLE dim_grupo AS
SELECT row_number() OVER (ORDER BY grupo) AS grupo_sk, grupo
FROM (SELECT DISTINCT grupo FROM stg_events);

CREATE OR REPLACE TABLE dim_canal AS
SELECT row_number() OVER (ORDER BY canal) AS canal_sk, canal
FROM (SELECT DISTINCT canal FROM stg_events);

CREATE OR REPLACE TABLE dim_tempo AS
SELECT
    CAST(d AS DATE)                              AS data,
    year(d)                                      AS ano,
    month(d)                                     AS mes,
    strftime(d, '%Y-%m')                         AS ano_mes,
    isodow(d)                                    AS dia_semana_num,   -- 1=segunda ... 7=domingo
    CASE isodow(d) WHEN 1 THEN 'Seg' WHEN 2 THEN 'Ter' WHEN 3 THEN 'Qua' WHEN 4 THEN 'Qui'
                   WHEN 5 THEN 'Sex' WHEN 6 THEN 'Sáb' ELSE 'Dom' END AS dia_semana,
    isodow(d) <= 5                               AS dia_util
FROM generate_series(
        (SELECT CAST(min(aberto_em) AS DATE) FROM stg_events),
        (SELECT CAST(max(aberto_em) AS DATE) FROM stg_events),
        INTERVAL 1 DAY) AS g(d);

-- 3) Fato (grão: 1 linha por chamado, estado mais recente) -------------
CREATE OR REPLACE TABLE fato_chamado AS
WITH ultimo AS (
    SELECT *,
           row_number() OVER (PARTITION BY chamado_id
                              ORDER BY atualizado_em DESC, qtd_atualizacoes DESC) AS rn,
           min(aberto_em)  OVER (PARTITION BY chamado_id) AS aberto_em_min,
           max(resolvido_em) OVER (PARTITION BY chamado_id) AS resolvido_em_max,
           max(fechado_em)   OVER (PARTITION BY chamado_id) AS fechado_em_max
    FROM stg_events
)
SELECT
    u.chamado_id,
    CAST(u.aberto_em_min AS DATE)                         AS data_abertura,
    u.aberto_em_min                                       AS aberto_em,
    hour(u.aberto_em_min)                                 AS hora_abertura,
    u.resolvido_em_max                                    AS resolvido_em,
    u.fechado_em_max                                      AS fechado_em,
    u.estado                                              AS estado_atual,
    (u.resolvido_em_max IS NOT NULL)                      AS resolvido,
    c.categoria_sk, g.grupo_sk, k.canal_sk, u.prioridade_cod,
    u.reatribuicoes, u.reaberturas, u.qtd_atualizacoes,
    (u.reaberturas > 0)                                   AS reaberto,
    (u.reatribuicoes >= 2)                                AS multi_reatribuicao,
    (u.problema_id IS NOT NULL)                           AS ligado_a_problema,
    round(date_diff('minute', u.aberto_em_min, u.resolvido_em_max) / 60.0, 2) AS tempo_resolucao_h,
    p.sla_alvo_h,
    CASE WHEN u.resolvido_em_max IS NULL THEN NULL
         ELSE date_diff('minute', u.aberto_em_min, u.resolvido_em_max) / 60.0 <= p.sla_alvo_h
    END                                                   AS sla_cumprido,
    u.sla_origem                                          AS sla_cumprido_origem
FROM ultimo u
JOIN dim_categoria c ON c.categoria = u.categoria AND c.subcategoria = u.subcategoria
JOIN dim_grupo     g ON g.grupo = u.grupo
JOIN dim_canal     k ON k.canal = u.canal
LEFT JOIN dim_prioridade p ON p.prioridade_cod = u.prioridade_cod
WHERE u.rn = 1;
