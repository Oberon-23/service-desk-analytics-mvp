"""
Roda o mesmo pipeline Bronze -> Silver -> Gold (sql/silver.sql, sql/gold.sql)
contra a base REAL da UCI, em um banco e pasta de saída separados dos
dados sintéticos, para não misturar os dois no repositório.

A base real (incident_event_log.csv, ~46 MB) não é commitada no git por
tamanho; apenas os resultados agregados (pequenos) ficam em data/gold_real/.

Fonte: Incident management process enriched event log (UCI), Amaral,
Fantinato & Peres (2018), DOI 10.24432/C57S4H, licença CC BY 4.0.
https://archive.ics.uci.edu/dataset/498/incident+management+process+enriched+event+log

Uso: python src/run_real_analysis.py [--input data/real/incident_event_log.csv]
"""
import argparse
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SQL = ROOT / "sql"

SILVER_TABLES = ["dim_prioridade", "dim_categoria", "dim_grupo", "dim_canal", "dim_tempo", "fato_chamado"]
GOLD_TABLES = ["gold_kpis_mensal", "gold_sla_categoria_prioridade", "gold_pico_dia_hora",
               "gold_retrabalho", "gold_top_demanda"]


def run(input_csv: Path) -> None:
    db_path = DATA / "warehouse_real.duckdb"
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))

    con.execute(f"""
        CREATE TABLE bronze_events AS
        SELECT *, now() AS _ingested_at, '{input_csv.name}' AS _source_file
        FROM read_csv('{input_csv}', all_varchar=true, header=true)
    """)
    n_bronze = con.execute("SELECT count(*) FROM bronze_events").fetchone()[0]
    print(f"[bronze] {n_bronze:,} linhas (eventos)")

    con.execute((SQL / "silver.sql").read_text(encoding="utf-8"))
    n_silver = con.execute("SELECT count(*) FROM fato_chamado").fetchone()[0]
    print(f"[silver] {n_silver:,} chamados (grão: 1 linha por chamado)")

    con.execute((SQL / "gold.sql").read_text(encoding="utf-8"))
    (DATA / "gold_real").mkdir(parents=True, exist_ok=True)
    (ROOT / "powerbi_real").mkdir(parents=True, exist_ok=True)
    for t in GOLD_TABLES:
        con.execute(f"COPY {t} TO '{DATA / 'gold_real' / (t + '.parquet')}' (FORMAT PARQUET)")
        con.execute(f"COPY {t} TO '{ROOT / 'powerbi_real' / (t + '.csv')}' (HEADER, DELIMITER ';')")
    print(f"[gold] {len(GOLD_TABLES)} tabelas -> data/gold_real e powerbi_real/")

    # ---- resumo para o README ------------------------------------------------
    periodo = con.execute("SELECT min(data_abertura), max(data_abertura) FROM fato_chamado").fetchone()
    geral = con.execute("""
        SELECT round(100.0*avg(sla_cumprido::int),1) AS pct_sla,
               round(avg(tempo_resolucao_h),1)        AS mttr_medio_h,
               round(median(tempo_resolucao_h),1)     AS mttr_mediana_h,
               round(100.0*avg(reaberto::int),1)      AS pct_reabertura,
               round(100.0*avg(multi_reatribuicao::int),1) AS pct_multi_reatrib
        FROM fato_chamado WHERE resolvido
    """).fetchone()
    print(f"\nPeríodo: {periodo[0]} a {periodo[1]}")
    print(f"SLA (alvos padrão) = {geral[0]}% | MTTR médio = {geral[1]}h | MTTR mediana = {geral[2]}h "
          f"| reabertura = {geral[3]}% | multi-reatribuição = {geral[4]}%")
    con.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=DATA / "real" / "incident_event_log.csv")
    run(ap.parse_args().input)
