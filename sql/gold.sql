-- =====================================================================
-- CAMADA GOLD: tabelas analíticas que respondem perguntas de negócio
-- Entrada: fato_chamado + dim_* (Silver)
-- =====================================================================

-- P1: Como evoluem volume, SLA, tempo de resolução e reabertura mês a mês?
CREATE OR REPLACE TABLE gold_kpis_mensal AS
SELECT
    strftime(f.data_abertura, '%Y-%m')                              AS ano_mes,
    count(*)                                                        AS chamados_abertos,
    count(*) FILTER (WHERE f.resolvido)                             AS chamados_resolvidos,
    round(100.0 * count(*) FILTER (WHERE f.sla_cumprido)
          / nullif(count(*) FILTER (WHERE f.resolvido), 0), 1)      AS pct_sla_cumprido,
    round(avg(f.tempo_resolucao_h), 1)                              AS mttr_medio_h,
    round(median(f.tempo_resolucao_h), 1)                           AS mttr_mediana_h,
    round(100.0 * avg(f.reaberto::INT), 1)                          AS pct_reabertura,
    round(100.0 * avg(f.multi_reatribuicao::INT), 1)                AS pct_multi_reatribuicao
FROM fato_chamado f
GROUP BY 1 ORDER BY 1;

-- P2: Quais categorias/prioridades mais estouram SLA?
CREATE OR REPLACE TABLE gold_sla_categoria_prioridade AS
SELECT
    c.categoria,
    p.prioridade,
    count(*) FILTER (WHERE f.resolvido)                             AS resolvidos,
    count(*) FILTER (WHERE f.sla_cumprido = FALSE)                  AS violacoes_sla,
    round(100.0 * count(*) FILTER (WHERE f.sla_cumprido = FALSE)
          / nullif(count(*) FILTER (WHERE f.resolvido), 0), 1)      AS pct_violacao,
    round(median(f.tempo_resolucao_h), 1)                           AS mediana_resolucao_h,
    max(p.sla_alvo_h)                                               AS sla_alvo_h
FROM fato_chamado f
JOIN (SELECT DISTINCT categoria_sk, categoria FROM dim_categoria) c USING (categoria_sk)
JOIN dim_prioridade p USING (prioridade_cod)
GROUP BY 1, 2 ORDER BY pct_violacao DESC NULLS LAST;

-- P3: Qual o horário/dia de pico? (dimensionamento de equipe)
CREATE OR REPLACE TABLE gold_pico_dia_hora AS
SELECT
    t.dia_semana_num, t.dia_semana, f.hora_abertura,
    count(*)                                                        AS chamados
FROM fato_chamado f
JOIN dim_tempo t ON t.data = f.data_abertura
GROUP BY 1, 2, 3 ORDER BY 1, 3;

-- P4: Onde há mais reatribuição e reabertura (retrabalho)?
CREATE OR REPLACE TABLE gold_retrabalho AS
SELECT
    c.categoria, g.grupo,
    count(*)                                                        AS chamados,
    round(avg(f.reatribuicoes), 2)                                  AS media_reatribuicoes,
    round(100.0 * avg(f.multi_reatribuicao::INT), 1)                AS pct_multi_reatribuicao,
    round(100.0 * avg(f.reaberto::INT), 1)                          AS pct_reabertura
FROM fato_chamado f
JOIN (SELECT DISTINCT categoria_sk, categoria FROM dim_categoria) c USING (categoria_sk)
JOIN dim_grupo g USING (grupo_sk)
GROUP BY 1, 2 HAVING count(*) >= 30
ORDER BY media_reatribuicoes DESC;

-- P5: Quais subcategorias mais geram demanda (candidatas a automação/autosserviço)?
CREATE OR REPLACE TABLE gold_top_demanda AS
SELECT
    c.categoria, c.subcategoria,
    count(*)                                                        AS chamados,
    round(100.0 * count(*) / sum(count(*)) OVER (), 1)              AS pct_do_total,
    round(100.0 * sum(count(*)) OVER (ORDER BY count(*) DESC
          ROWS UNBOUNDED PRECEDING) / sum(count(*)) OVER (), 1)     AS pct_acumulado,   -- Pareto
    round(median(f.tempo_resolucao_h), 1)                           AS mediana_resolucao_h,
    round(sum(f.tempo_resolucao_h), 0)                              AS horas_totais_resolucao
FROM fato_chamado f
JOIN dim_categoria c USING (categoria_sk)
GROUP BY 1, 2 ORDER BY chamados DESC;
