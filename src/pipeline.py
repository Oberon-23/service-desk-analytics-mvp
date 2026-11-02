"""
Pipeline Bronze -> Silver -> Gold (DuckDB + SQL).

Uso:
  python src/pipeline.py                                  # usa data/raw/incident_event_log.csv
  python src/pipeline.py --input caminho/para/incident_event_log.csv   # CSV real do UCI
"""
import argparse
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SQL = ROOT / "sql"

SILVER_TABLES = ["dim_prioridade", "dim_categoria", "dim_grupo", "dim_canal", "dim_tempo", "fato_chamado"]
GOLD_TABLES = ["gold_kpis_mensal", "gold_sla_categoria_prioridade", "gold_pico_dia_hora",
               "gold_retrabalho", "gold_top_demanda"]


def run(input_csv: Path) -> Path:
    t0 = time.time()
    db_path = DATA / "warehouse.duckdb"
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))

    # ---- BRONZE: ingestão fiel, tudo como texto, + auditoria ----------------
    con.execute(f"""
        CREATE TABLE bronze_events AS
        SELECT *, now() AS _ingested_at, '{input_csv.name}' AS _source_file
        FROM read_csv('{input_csv}', all_varchar=true, header=true)
    """)
    (DATA / "bronze").mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY bronze_events TO '{DATA / 'bronze' / 'incident_event_log.parquet'}' (FORMAT PARQUET)")
    n_bronze = con.execute("SELECT count(*) FROM bronze_events").fetchone()[0]
    print(f"[bronze] {n_bronze:,} linhas")

    # ---- SILVER ---------------------------------------------------------------
    con.execute((SQL / "silver.sql").read_text(encoding="utf-8"))
    (DATA / "silver").mkdir(parents=True, exist_ok=True)
    for t in SILVER_TABLES:
        con.execute(f"COPY {t} TO '{DATA / 'silver' / (t + '.parquet')}' (FORMAT PARQUET)")
    n_silver = con.execute("SELECT count(*) FROM fato_chamado").fetchone()[0]
    print(f"[silver] {n_silver:,} chamados (grão: 1 linha por chamado)")

    # ---- GOLD -----------------------------------------------------------------
    con.execute((SQL / "gold.sql").read_text(encoding="utf-8"))
    (DATA / "gold").mkdir(parents=True, exist_ok=True)
    (ROOT / "powerbi").mkdir(parents=True, exist_ok=True)
    for t in GOLD_TABLES:
        con.execute(f"COPY {t} TO '{DATA / 'gold' / (t + '.parquet')}' (FORMAT PARQUET)")
        # CSVs prontos para o Power BI (UTF-8 com BOM para acentos)
        con.execute(f"COPY {t} TO '{ROOT / 'powerbi' / (t + '.csv')}' (HEADER, DELIMITER ';')")
    # modelo estrela completo para Power BI
    for t in SILVER_TABLES:
        con.execute(f"COPY {t} TO '{ROOT / 'powerbi' / (t + '.csv')}' (HEADER, DELIMITER ';')")
    print(f"[gold] {len(GOLD_TABLES)} tabelas -> data/gold e powerbi/")
    con.close()
    print(f"Pipeline concluído em {time.time() - t0:.1f}s")
    return db_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=DATA / "raw" / "incident_event_log.csv")
    run(ap.parse_args().input)
