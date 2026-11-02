# Relatório de qualidade de dados

Gerado em 02/11/2026 12:25

| Teste | Resultado | Detalhe |
|---|---|---|
| Chave única: 1 linha por chamado na fato | ✅ PASS | duplicados = 0 |
| Reconciliação: nº de chamados Bronze = Silver | ✅ PASS | bronze=12,000 silver=12,000 |
| Duplicatas exatas removidas na Silver | ✅ PASS | 252 linhas duplicadas removidas (0.50%) |
| Sem data de abertura nula | ✅ PASS | nulos = 0 |
| Resolução nunca anterior à abertura | ✅ PASS | violações = 0 |
| Prioridade válida (1 a 4) em todos os chamados | ✅ PASS | sem prioridade = 0 |
| Integridade referencial (categoria, grupo, canal) | ✅ PASS | órfãos = 0 |
| Estados normalizados (sem 'Outro') | ✅ PASS | estado 'Outro' = 0 |
| SLA recalculado concorda com o campo de origem (>= 95%) | ✅ PASS | concordância = 98.5% |
| Categoria 'Não informado' abaixo de 5% | ✅ PASS | 1.55% |
