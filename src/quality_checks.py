"""
Testes de qualidade de dados. Gera docs/quality_report.md e retorna código 1 se algo falhar.
Uso: python src/quality_checks.py                 # base sintética (padrão)
     python src/quality_checks.py --real           # base real (data/warehouse_real.duckdb)
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--real", action="store_true", help="roda contra data/warehouse_real.duckdb")
args = ap.parse_args()
db_name = "warehouse_real.duckdb" if args.real else "warehouse.duckdb"
report_name = "quality_report_real.md" if args.real else "quality_report.md"
con = duckdb.connect(str(ROOT / "data" / db_name), read_only=True)


def q(sql):
    return con.execute(sql).fetchone()[0]


n_bronze = q("SELECT count(*) FROM bronze_events")
n_dedup = q("SELECT count(*) FROM (SELECT DISTINCT * EXCLUDE (_ingested_at,_source_file) FROM bronze_events)")
n_inc_bronze = q("SELECT count(DISTINCT trim(number)) FROM bronze_events")
n_inc_silver = q("SELECT count(*) FROM fato_chamado")

checks = [
    ("Chave única: 1 linha por chamado na fato",
     q("SELECT count(*) - count(DISTINCT chamado_id) FROM fato_chamado") == 0, "duplicados = 0"),
    ("Reconciliação: nº de chamados Bronze = Silver",
     n_inc_bronze == n_inc_silver, f"bronze={n_inc_bronze:,} silver={n_inc_silver:,}"),
    ("Duplicatas exatas removidas na Silver",
     True, f"{n_bronze - n_dedup:,} linhas duplicadas removidas ({100*(n_bronze-n_dedup)/n_bronze:.2f}%)"),
    ("Sem data de abertura nula",
     q("SELECT count(*) FROM fato_chamado WHERE aberto_em IS NULL") == 0, "nulos = 0"),
    ("Resolução nunca anterior à abertura",
     q("SELECT count(*) FROM fato_chamado WHERE resolvido_em < aberto_em") == 0, "violações = 0"),
    ("Prioridade válida (1 a 4) em todos os chamados",
     q("SELECT count(*) FROM fato_chamado WHERE sla_alvo_h IS NULL") == 0, "sem prioridade = 0"),
    ("Integridade referencial (categoria, grupo, canal)",
     q("""SELECT count(*) FROM fato_chamado f
          LEFT JOIN dim_categoria c USING (categoria_sk) LEFT JOIN dim_grupo g USING (grupo_sk)
          LEFT JOIN dim_canal k USING (canal_sk)
          WHERE c.categoria_sk IS NULL OR g.grupo_sk IS NULL OR k.canal_sk IS NULL""") == 0, "órfãos = 0"),
    ("Estados normalizados (sem 'Outro')",
     q("SELECT count(*) FROM fato_chamado WHERE estado_atual = 'Outro'") == 0, "estado 'Outro' = 0"),
]

agree = q("""SELECT 100.0 * avg((sla_cumprido = sla_cumprido_origem)::INT)
             FROM fato_chamado WHERE resolvido""")
checks.append(("SLA recalculado concorda com o campo de origem (>= 95%)", agree >= 95, f"concordância = {agree:.1f}%"))

null_cat = q("SELECT 100.0 * avg((categoria_sk IN (SELECT categoria_sk FROM dim_categoria WHERE categoria='Não informado'))::INT) FROM fato_chamado")
checks.append(("Categoria 'Não informado' abaixo de 5%", null_cat < 5, f"{null_cat:.2f}%"))

lines = [f"# Relatório de qualidade de dados\n\nGerado em {datetime.now():%d/%m/%Y %H:%M}\n",
         "| Teste | Resultado | Detalhe |", "|---|---|---|"]
failed = 0
for name, ok, detail in checks:
    failed += 0 if ok else 1
    lines.append(f"| {name} | {'✅ PASS' if ok else '❌ FAIL'} | {detail} |")
    print(("PASS" if ok else "FAIL"), "-", name, "|", detail)

(ROOT / "docs").mkdir(exist_ok=True)
(ROOT / "docs" / report_name).write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\n{len(checks) - failed}/{len(checks)} testes passaram")
sys.exit(1 if failed else 0)
