# Guia: dashboard no Power BI

Os CSVs em `powerbi/` usam **separador `;`** e codificação UTF-8.

## 1. Importar
1. **Obter dados → Texto/CSV** e importar: `fato_chamado`, `dim_categoria`, `dim_grupo`, `dim_canal`, `dim_prioridade`, `dim_tempo`.
2. No Power Query, confira os tipos: datas em `data_abertura`/`dim_tempo[data]`, Verdadeiro/Falso nas colunas booleanas e decimal em `tempo_resolucao_h`.

## 2. Relacionamentos (modelo estrela, 1:* e filtro único)
| De (1) | Para (*) |
|---|---|
| `dim_categoria[categoria_sk]` | `fato_chamado[categoria_sk]` |
| `dim_grupo[grupo_sk]` | `fato_chamado[grupo_sk]` |
| `dim_canal[canal_sk]` | `fato_chamado[canal_sk]` |
| `dim_prioridade[prioridade_cod]` | `fato_chamado[prioridade_cod]` |
| `dim_tempo[data]` | `fato_chamado[data_abertura]` |

Marque `dim_tempo` como **tabela de datas**.

## 3. Medidas DAX
```DAX
Chamados = COUNTROWS ( fato_chamado )

Resolvidos = CALCULATE ( [Chamados], fato_chamado[resolvido] = TRUE () )

% SLA Cumprido =
DIVIDE ( CALCULATE ( [Chamados], fato_chamado[sla_cumprido] = TRUE () ), [Resolvidos] )

MTTR (h) = AVERAGE ( fato_chamado[tempo_resolucao_h] )

Mediana Resolução (h) = MEDIAN ( fato_chamado[tempo_resolucao_h] )

% Reabertura = DIVIDE ( CALCULATE ( [Chamados], fato_chamado[reaberto] = TRUE () ), [Chamados] )

% Multi-reatribuição =
DIVIDE ( CALCULATE ( [Chamados], fato_chamado[multi_reatribuicao] = TRUE () ), [Chamados] )

Chamados Mês Anterior = CALCULATE ( [Chamados], DATEADD ( dim_tempo[data], -1, MONTH ) )

Var % Mês = DIVIDE ( [Chamados] - [Chamados Mês Anterior], [Chamados Mês Anterior] )
```

## 4. Layout sugerido (1 página + 1 de detalhe)
**Página "Visão Geral"**
- Linha de **cartões**: Chamados · % SLA Cumprido · MTTR (h) · % Reabertura · % Multi-reatribuição
- **Gráfico de linhas**: Chamados por `dim_tempo[ano_mes]`
- **Barras horizontais**: % SLA Cumprido por `dim_categoria[categoria]`
- **Matriz como mapa de calor** (formatação condicional): linhas `dia_semana`, colunas `hora_abertura`, valor Chamados
- **Segmentações** no topo: período, prioridade e grupo

**Página "Retrabalho e Demanda"**
- Pareto: Chamados por subcategoria com % acumulado (use `gold_top_demanda` ou medida DAX)
- Tabela: grupo × categoria com % Multi-reatribuição e % Reabertura

## 5. Para o portfólio
- Exporte prints das duas páginas para `docs/img/` e adicione ao README.
- Opcional: publique na Web (Power BI Service → *Publicar na Web*) **somente porque os dados são sintéticos**.
