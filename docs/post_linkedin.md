# Rascunho do post de lançamento (LinkedIn)

> Anexe as 4 imagens de `docs/img/` (o carrossel aceita até 20). Ordem sugerida: 02 → 04 → 03 → 01. Inclua um print do dashboard Power BI quando estiver pronto.
> Na seção **Projetos** do perfil, use o título "MVP de Engenharia de Dados: Service Desk Analytics" e associe as competências Python, SQL, DuckDB, Power BI, Modelagem Dimensional e Qualidade de Dados.

---

Todo dia eu vejo chamados chegando no service desk. Neste projeto, quis ver o que eles dizem quando viram dados.

Desenvolvi um MVP de Engenharia de Dados que transforma o log bruto de uma ferramenta de ITSM em indicadores prontos para gestão: SLA, tempo de resolução, retrabalho e picos de demanda.

🔧 O desafio
O log exportado traz uma linha por evento (não por chamado), nulos como "?", datas em texto, prioridade como "3 - Moderate", estados inconsistentes e duplicatas. Montar indicadores assim vira trabalho manual e sujeito a erro.

🏗️ A solução: pipeline em arquitetura Medallion (Python + SQL + DuckDB)
• Bronze: ingestão fiel dos dados brutos, com colunas de auditoria para rastreabilidade
• Silver: limpeza, padronização e redução do log a 1 linha por chamado, com modelagem dimensional em Star Schema (fato + 5 dimensões)
• Gold: 5 tabelas analíticas que respondem perguntas de negócio, prontas para o Power BI
• 10 testes automatizados de qualidade de dados, incluindo a validação cruzada do SLA recalculado contra o da ferramenta de origem

📊 O que os dados mostraram
• Acesso e Senha = 21,7% dos chamados, mas só 3,5% das horas de resolução → candidato natural a autosserviço
• 73% dos chamados críticos e altos de Software e Instalação estouram o SLA
• 62% dos chamados de Rede passam por 2+ reatribuições → oportunidade de melhorar a triagem
• Segunda de manhã concentra o pico: 35% do volume entra entre 8h e 11h

Aqui a Engenharia de Produção encontra os dados: é o mesmo raciocínio de Pareto, PDCA e controle de processo, só que aplicado à operação de TI.

⚠️ Transparência: usei dados sintéticos, gerados com o mesmo esquema de um dataset público e real de incidentes ServiceNow (UCI Machine Learning Repository, CC BY 4.0). O pipeline também roda sobre esse dataset real. Nenhum dado de cliente ou empregador foi utilizado.

Código, documentação, dicionário de dados e guia do dashboard:
🔗 github.com/Oberon-23/service-desk-analytics-mvp

#EngenhariaDeDados #DataAnalytics #PowerBI #SQL #Python #DuckDB #ITSM #ServiceDesk #QualidadeDeDados #EngenhariaDeProducao #Portfolio

---

## Ideias de posts de continuação (1 por semana)
1. **"Por que um log de eventos engana"**: o erro de contar linhas em vez de chamados (Silver).
2. **"Pareto no service desk"**: o gráfico volume x esforço e a lógica do autosserviço.
3. **"Testes de qualidade de dados"**: o que é reconciliação entre camadas e por que o SLA recalculado importa.
4. **"Do CSV ao dashboard"**: bastidores do modelo estrela no Power BI, com as medidas DAX.
