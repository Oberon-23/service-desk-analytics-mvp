"""
Gera os gráficos estáticos (PNG) a partir da base REAL da UCI, em
docs/img_real/ — separados dos gráficos de demonstração (dados sintéticos)
em docs/img/, para não misturar os dois no README.

Uso: python src/charts_real.py   (rodar depois de src/run_real_analysis.py)
"""
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "img_real"
OUT.mkdir(parents=True, exist_ok=True)
con = duckdb.connect(str(ROOT / "data" / "warehouse_real.duckdb"), read_only=True)

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, MUTED = "#2a78d6", "#eb6834", "#b9b8b2"
BLUES = ["#f0f6fe", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.axisbelow": True, "grid.color": GRID, "grid.linewidth": 0.8,
})


def title(ax, t, sub):
    ax.set_title(t, loc="left", fontsize=15, fontweight="bold", pad=28)
    ax.text(0, 1.03, sub, transform=ax.transAxes, color=INK2, fontsize=10.5)


# 1) Volume mensal -----------------------------------------------------------
df = con.sql("SELECT ano_mes, chamados_abertos FROM gold_kpis_mensal ORDER BY 1").df()
fig, ax = plt.subplots(figsize=(10, 5))
x = np.arange(len(df))
ax.plot(x, df.chamados_abertos, color=BLUE, lw=2, marker="o", ms=5)
i = int(df.chamados_abertos.idxmax())
ax.annotate(f"{df.chamados_abertos[i]:,} chamados\nmaior volume do período".replace(",", "."),
            (i, df.chamados_abertos[i]), xytext=(min(i + 2.0, len(df) - 2.8), df.chamados_abertos[i] * 0.78),
            color=INK, fontsize=10, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.set_xticks(x[::1], df.ano_mes, rotation=35, fontsize=9, ha="right")
ax.set_ylim(0, df.chamados_abertos.max() * 1.15)
ax.grid(axis="x", visible=False)
title(ax, "Chamados abertos por mês — base real (UCI)", "Fev/2016 a fev/2017, instância ServiceNow anonimizada")
fig.tight_layout(); fig.savefig(OUT / "01_volume_mensal.png", dpi=160); plt.close(fig)

# 2) Pareto de subcategorias (volume x % acumulado) --------------------------
df = con.sql("""SELECT categoria || ' / ' || subcategoria AS rotulo, chamados, pct_acumulado
                FROM gold_top_demanda ORDER BY chamados DESC LIMIT 12""").df()
fig, ax = plt.subplots(figsize=(11, 5.2))
colors = [ORANGE if v <= 80 else MUTED for v in df.pct_acumulado]
ax.bar(range(len(df)), df.chamados, color=colors)
ax2 = ax.twinx()
ax2.plot(range(len(df)), df.pct_acumulado, color=INK, lw=1.6, marker="o", ms=4)
ax2.axhline(80, color=INK2, lw=0.8, ls="--")
ax2.set_ylim(0, 105); ax2.set_ylabel("% acumulado"); ax2.grid(False)
ax.set_xticks(range(len(df)), [f"Sub {i+1}" for i in range(len(df))], fontsize=9)
ax.set_ylabel("chamados"); ax.grid(axis="x", visible=False)
title(ax, "Pareto das subcategorias — base real (UCI)",
      "Categorias/subcategorias anonimizadas pela UCI; poucas concentram a maior parte do volume")
fig.tight_layout(); fig.savefig(OUT / "02_pareto_subcategorias.png", dpi=160); plt.close(fig)

# 3) Heatmap dia x hora -------------------------------------------------------
df = con.sql("SELECT dia_semana_num, hora_abertura, chamados FROM gold_pico_dia_hora").df()
m = np.zeros((7, 24))
for r in df.itertuples():
    m[r.dia_semana_num - 1, r.hora_abertura] = r.chamados
from matplotlib.colors import LinearSegmentedColormap
cmap = LinearSegmentedColormap.from_list("blues", BLUES)
fig, ax = plt.subplots(figsize=(11, 4.2))
im = ax.imshow(m, cmap=cmap, aspect="auto")
ax.set_yticks(range(7), ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"])
ax.set_xticks(range(0, 24, 2), [f"{h}h" for h in range(0, 24, 2)])
ax.grid(False)
for s in ax.spines.values():
    s.set_visible(False)
cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01); cb.outline.set_visible(False)
cb.set_label("chamados", color=INK2)
title(ax, "Quando os chamados chegam — base real (UCI)", "Distribuição real de abertura por dia da semana e hora")
fig.tight_layout(); fig.savefig(OUT / "03_pico_dia_hora.png", dpi=160); plt.close(fig)

# 4) Retrabalho: reatribuição média por grupo (top 10, agregado só por grupo) -
df = con.sql("""SELECT g.grupo AS grupo, round(avg(f.reatribuicoes), 2) AS media_reatribuicoes,
                        count(*) AS chamados
                 FROM fato_chamado f JOIN dim_grupo g USING (grupo_sk)
                 GROUP BY 1 HAVING count(*) >= 30
                 ORDER BY media_reatribuicoes DESC LIMIT 10""").df()
df = df.iloc[::-1].reset_index(drop=True)  # maior no topo da barra horizontal
fig, ax = plt.subplots(figsize=(10, 5.5))
colors = [ORANGE if v == df.media_reatribuicoes.max() else MUTED for v in df.media_reatribuicoes]
ax.barh(df.grupo, df.media_reatribuicoes, color=colors, height=0.62)
ax.set_xlim(0, df.media_reatribuicoes.max() * 1.28)
for yy, (v, n) in enumerate(zip(df.media_reatribuicoes, df.chamados)):
    ax.text(v + df.media_reatribuicoes.max() * 0.02, yy, f"{v:.1f}  (n={n})".replace(".", ","),
            va="center", fontsize=9.5, color=INK2)
ax.set_xlabel("reatribuições médias por chamado"); ax.grid(axis="y", visible=False)
title(ax, "Onde há mais retrabalho — base real (UCI)", "Grupos de atendimento com maior nº médio de reatribuições (mín. 30 chamados)")
fig.tight_layout(); fig.savefig(OUT / "04_retrabalho_grupos.png", dpi=160); plt.close(fig)

print("Gráficos (base real) gerados em", OUT)
