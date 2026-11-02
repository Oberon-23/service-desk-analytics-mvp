# Dicionário de dados

## Bronze: `bronze_events`
Cópia fiel do CSV de origem (36 colunas, **todas como texto**) mais duas colunas de auditoria:

| Coluna | Descrição |
|---|---|
| `number` | ID do chamado (repete-se: uma linha por evento) |
| `incident_state` | Estado no momento do evento (New, Active, Resolved, Closed…) |
| `reassignment_count` / `reopen_count` / `sys_mod_count` | Contadores acumulados até o evento |
| `made_sla` | Flag de SLA vinda da ferramenta de origem |
| `opened_at`, `sys_updated_at`, `resolved_at`, `closed_at` | Datas em texto `dd/mm/AAAA HH:MM` (`?` = nulo) |
| `category`, `subcategory`, `assignment_group`, `contact_type`, `priority` … | Atributos do chamado |
| `_ingested_at` | Data e hora da ingestão (auditoria) |
| `_source_file` | Nome do arquivo de origem (auditoria) |

Referência completa das 36 colunas: [UCI #498](https://archive.ics.uci.edu/dataset/498/incident+management+process+enriched+event+log).

## Silver

### `fato_chamado` (grão: 1 linha por chamado)
| Coluna | Tipo | Regra |
|---|---|---|
| `chamado_id` | texto | `trim(number)`, chave única |
| `data_abertura` / `aberto_em` / `hora_abertura` | data / timestamp / int | menor `opened_at` do chamado |
| `resolvido_em` / `fechado_em` | timestamp | maior `resolved_at` / `closed_at` do chamado |
| `estado_atual` | texto | estado do evento mais recente, traduzido |
| `resolvido` | bool | `resolvido_em IS NOT NULL` |
| `categoria_sk`, `grupo_sk`, `canal_sk`, `prioridade_cod` | int | chaves para as dimensões |
| `reatribuicoes`, `reaberturas`, `qtd_atualizacoes` | int | valores do evento mais recente |
| `reaberto` | bool | `reaberturas > 0` |
| `multi_reatribuicao` | bool | `reatribuicoes >= 2` |
| `ligado_a_problema` | bool | chamado associado a um registro de problema |
| `tempo_resolucao_h` | decimal | horas corridas entre abertura e resolução |
| `sla_alvo_h` | int | meta da prioridade (ver `dim_prioridade`) |
| `sla_cumprido` | bool | `tempo_resolucao_h <= sla_alvo_h` (recalculado) |
| `sla_cumprido_origem` | bool | `made_sla` original, usado na validação cruzada |

### Dimensões
| Tabela | Colunas | Observação |
|---|---|---|
| `dim_prioridade` | `prioridade_cod`, `prioridade`, `sla_alvo_h` | P1=4h, P2=8h, P3=24h, P4=72h (metas ilustrativas) |
| `dim_categoria` | `categoria_sk`, `categoria`, `subcategoria` | `?` vira "Não informado" |
| `dim_grupo` | `grupo_sk`, `grupo` | grupo solucionador |
| `dim_canal` | `canal_sk`, `canal` | Phone, Email, Self service, Direct opening |
| `dim_tempo` | `data`, `ano`, `mes`, `ano_mes`, `dia_semana_num`, `dia_semana`, `dia_util` | calendário contínuo |

## Gold
| Tabela | Pergunta que responde |
|---|---|
| `gold_kpis_mensal` | Como evoluem volume, % SLA, MTTR (média e mediana), % reabertura e % multi-reatribuição? |
| `gold_sla_categoria_prioridade` | Quais combinações de categoria e prioridade mais violam o SLA? |
| `gold_pico_dia_hora` | Em que dia e hora os chamados chegam? |
| `gold_retrabalho` | Que categorias e grupos têm mais reatribuição e reabertura? (mínimo de 30 chamados) |
| `gold_top_demanda` | Quais subcategorias concentram volume e horas? (com % acumulado de Pareto) |

## Glossário
- **SLA**: acordo de nível de serviço; aqui, o tempo máximo de resolução por prioridade.
- **MTTR**: *Mean Time To Resolve*, tempo médio de resolução.
- **Reatribuição**: troca de grupo ou analista responsável. Indica triagem imprecisa.
- **Reabertura**: o usuário rejeitou a solução. Indica falha de qualidade na resolução.
