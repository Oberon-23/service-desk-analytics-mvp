"""
Gera os gráficos estáticos (PNG) usados no README e no post do LinkedIn.
Uso: python src/charts.py   (rodar depois do pipeline)
"""
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "img"
OUT.mkdir(parents=True, exist_ok=True)
con = duckdb.connect(str(ROOT / "data" / "warehouse.duckdb"), read_only=True)

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


# 1) Volume mensal ----------------------------------------------------------
df = con.sql("SELECT ano_mes, chamados_abertos FROM gold_kpis_mensal ORDER BY 1").df()
fig, ax = plt.subplots(figsize=(10, 5))
x = np.arange(len(df))
ax.plot(x, df.chamados_abertos, color=BLUE, lw=2, marker="o", ms=5)
i = int(df.chamados_abertos.idxmax())
ax.annotate(f"{df.chamados_abertos[i]:,} chamados\nincidente grave".replace(",", "."),
            (i, df.chamados_abertos[i]), xytext=(i + 1.2, df.chamados_abertos[i] - 120),
            color=INK, fontsize=10, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.set_xticks(x[::2], df.ano_mes[::2], rotation=0, fontsize=9)
ax.set_ylim(0, df.chamados_abertos.max() * 1.15)
ax.grid(axis="x", visible=False)
title(ax, "Chamados abertos por mês", "Um único mês concentrou quase 3x o volume normal")
fig.tight_layout(); fig.savefig(OUT / "01_volume_mensal.png", dpi=160); plt.close(fig)

# 2) Volume x esforço por categoria (dois painéis, mesma escala %) ---------
df = con.sql("""SELECT categoria,
                  100*sum(chamados)/(SELECT sum(chamados) FROM gold_top_demanda) AS pct_vol,
                  100*sum(horas_totais_resolucao)/(SELECT sum(horas_totais_resolucao) FROM gold_top_demanda) AS pct_horas
                FROM gold_top_demanda WHERE categoria <> 'Não informado'
                GROUP BY 1 ORDER BY pct_vol""").df()
fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharey=True)
for ax, col, lab in [(axes[0], "pct_vol", "% dos chamados"), (axes[1], "pct_horas", "% das horas de resolução")]:
    colors = [ORANGE if c == "Acesso e Senha" else BLUE for c in df.categoria]
    ax.barh(df.categoria, df[col], color=colors, height=0.62)
    for yy, v in enumerate(df[col]):
        ax.text(v + 0.6, yy, f"{v:.1f}%".replace(".", ","), va="center", fontsize=9.5, color=INK2)
    ax.set_xlim(0, 52); ax.set_xlabel(lab); ax.grid(axis="y", visible=False)
axes[0].set_title("Volume x esforço por categoria", loc="left", fontsize=15, fontweight="bold", pad=28)
axes[0].text(0, 1.03, "Acesso e Senha: muito volume, pouco esforço. Candidato a autosserviço",
             transform=axes[0].transAxes, color=INK2, fontsize=10.5)
fig.tight_layout(); fig.savefig(OUT / "02_volume_x_esforco.png", dpi=160); plt.close(fig)

# 3) Heatmap dia x hora -----------------------------------------------------
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
title(ax, "Quando os chamados chegam", "Segunda de manhã é o pico: 35% do volume entra entre 8h e 11h")
fig.tight_layout(); fig.savefig(OUT / "03_pico_dia_hora.png", dpi=160); plt.close(fig)

# 4) Violação de SLA (P1+P2) por categoria ---------------------------------
df = con.sql("""SELECT categoria, 100.0*sum(violacoes_sla)/sum(resolvidos) AS pct
                FROM gold_sla_categoria_prioridade
                WHERE prioridade IN ('P1 - Crítica','P2 - Alta') AND categoria <> 'Não informado'
                GROUP BY 1 ORDER BY pct""").df()
fig, ax = plt.subplots(figsize=(10, 5))
colors = [ORANGE if v == df.pct.max() else MUTED for v in df.pct]
ax.barh(df.categoria, df.pct, color=colors, height=0.62)
for yy, v in enumerate(df.pct):
    ax.text(v + 1, yy, f"{v:.0f}%", va="center", fontsize=10, color=INK2)
ax.set_xlim(0, 100); ax.set_xlabel("% de chamados P1/P2 fora do SLA"); ax.grid(axis="y", visible=False)
title(ax, "Onde o SLA de alta prioridade estoura", "Chamados críticos e altos resolvidos, por categoria")
fig.tight_layout(); fig.savefig(OUT / "04_sla_alta_prioridade.png", dpi=160); plt.close(fig)

print("Gráficos gerados em", OUT)
