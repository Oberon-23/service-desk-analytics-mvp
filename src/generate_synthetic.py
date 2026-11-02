"""
Gerador de dados SINTÉTICOS de chamados de service desk.

Reproduz o ESQUEMA (36 colunas) e as "sujeiras" típicas do dataset público
"Incident management process enriched event log" (UCI, ServiceNow):
  - log de eventos (várias linhas por chamado)
  - nulos como '?'
  - datas em texto dd/mm/AAAA HH:MM
  - prioridade/impacto/urgência como texto ("3 - Moderate")
  - estados com caixa/espaços inconsistentes
  - linhas duplicadas

Os dados NÃO são reais. Os padrões (pico na segunda de manhã, mês de
incidente grave, categorias com mais reatribuição) foram embutidos de
propósito para que a análise tenha o que mostrar.

Uso: python src/generate_synthetic.py [--n 12000] [--seed 42]
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

START = pd.Timestamp("2025-01-01")
END = pd.Timestamp("2026-06-30 23:59")
OUTAGE_MONTH = "2025-06"  # mês com incidente grave (pico de volume)

# categoria: (peso, subcategorias, mediana_h, lambda_reatribuicao, prob_reabertura, grupo)
CATEGORIES = {
    "Acesso e Senha": (0.22, ["Reset de senha", "Conta bloqueada", "Permissão de acesso"], 1.5, 0.2, 0.04, "Service Desk N1"),
    "Software e Instalação": (0.20, ["Instalação de software", "Atualização", "Licença"], 20.0, 0.8, 0.12, "Suporte em Campo"),
    "Hardware e Periféricos": (0.15, ["Notebook", "Impressora", "Monitor/Periférico"], 12.0, 0.6, 0.07, "Suporte em Campo"),
    "Rede e Conectividade": (0.13, ["Wi-Fi", "VPN", "Link remoto"], 9.0, 2.0, 0.09, "Infraestrutura de Redes"),
    "E-mail e Colaboração": (0.12, ["Outlook", "Teams", "Caixa compartilhada"], 3.0, 0.3, 0.04, "Service Desk N2"),
    "Sistemas Corporativos": (0.12, ["ServiceNow", "ERP", "Acesso a relatório"], 14.0, 1.2, 0.08, "Sistemas Corporativos"),
    "Dúvidas e Orientação": (0.06, ["Orientação de uso", "Treinamento"], 1.0, 0.1, 0.02, "Service Desk N1"),
}
PRIORITY_LABEL = {1: "1 - Critical", 2: "2 - High", 3: "3 - Moderate", 4: "4 - Low"}
IMPACT_LABEL = {1: "1 - High", 2: "2 - Medium", 3: "3 - Low"}
PRIORITY_MULT = {1: 0.4, 2: 0.7, 3: 1.0, 4: 1.5}
SLA_TARGET_H = {1: 4, 2: 8, 3: 24, 4: 72}  # horas corridas (simplificação)
CONTACTS = ["Phone", "Email", "Self service", "Direct opening"]
DOW_W = np.array([1.35, 1.10, 1.00, 1.00, 0.90, 0.12, 0.08])  # seg..dom
HOUR_W = np.array([0.1, 0.05, 0.05, 0.05, 0.1, 0.2, 0.5, 1.5, 4.0, 4.5, 3.5, 2.5,
                   2.0, 3.0, 3.5, 3.0, 2.2, 1.4, 0.8, 0.5, 0.3, 0.2, 0.15, 0.1])


def fmt(ts):
    return ts.strftime("%d/%m/%Y %H:%M") if pd.notna(ts) else "?"


def main(n: int, seed: int) -> Path:
    rng = np.random.default_rng(seed)

    # --- dias de abertura ---------------------------------------------------
    days = pd.date_range(START, END.normalize(), freq="D")
    w = DOW_W[days.dayofweek]
    months = days.strftime("%Y-%m")
    w = w * np.where(months == OUTAGE_MONTH, 3.0, 1.0)
    w = w * (1 + 0.012 * (np.arange(len(days)) / 30))  # leve crescimento
    w = w / w.sum()
    open_days = rng.choice(days, size=n, p=w)
    hours = rng.choice(24, size=n, p=HOUR_W / HOUR_W.sum())
    minutes = rng.integers(0, 60, size=n)
    opened = pd.to_datetime(open_days) + pd.to_timedelta(hours, "h") + pd.to_timedelta(minutes, "m")

    cats = list(CATEGORIES)
    cat_w = np.array([CATEGORIES[c][0] for c in cats])
    cat_idx = rng.choice(len(cats), size=n, p=cat_w / cat_w.sum())
    prio = rng.choice([1, 2, 3, 4], size=n, p=[0.03, 0.12, 0.55, 0.30])

    rows = []
    for i in range(n):
        cat = cats[cat_idx[i]]
        _, subs, median_h, lam, p_reopen, group = CATEGORIES[cat]
        sub = subs[rng.integers(len(subs))]
        p = int(prio[i])
        op = opened[i]
        in_outage = op.strftime("%Y-%m") == OUTAGE_MONTH
        mult = PRIORITY_MULT[p] * (1.8 if in_outage and cat in ("Rede e Conectividade", "Sistemas Corporativos") else 1.0)
        res_h = float(rng.lognormal(np.log(median_h * mult), 0.8))
        resolved = op + pd.Timedelta(hours=res_h)
        reassign = int(rng.poisson(lam * (1.5 if p <= 2 else 1.0)))
        reopen = int(rng.random() < p_reopen) + int(rng.random() < p_reopen / 5)
        closed = resolved + pd.Timedelta(hours=float(rng.uniform(24, 72)))
        made_sla = res_h <= SLA_TARGET_H[p]
        if rng.random() < 0.015:  # divergência de origem (qualidade de dado)
            made_sla = not made_sla

        still_open = resolved > END
        # sequência de eventos
        states = ["New", "Active"]
        if rng.random() < 0.20:
            states.append("Awaiting User Info")
        if not still_open:
            states.append("Resolved")
            if closed <= END:
                states.append("Closed")
        t_points = [op, op + pd.Timedelta(minutes=float(rng.uniform(1, 30)))]
        if "Awaiting User Info" in states:
            t_points.append(t_points[1] + (resolved - t_points[1]) * 0.5)
        if "Resolved" in states:
            t_points.append(resolved)
        if "Closed" in states:
            t_points.append(closed)

        caller = f"Caller {rng.integers(1000, 4500)}"
        opened_by = f"Opened by {rng.integers(1, 250)}"
        loc = f"Location {rng.integers(1, 120)}" if rng.random() > 0.02 else "?"
        contact = CONTACTS[rng.integers(len(CONTACTS))]
        resolver = f"Resolver {rng.integers(1, 90)}"
        sym = f"Symptom {rng.integers(100, 600)}"
        ci = f"CI {rng.integers(1, 400)}" if rng.random() > 0.3 else "?"
        impact = IMPACT_LABEL[min(3, max(1, p if p <= 3 else 3))]
        category_val = cat if rng.random() > 0.015 else "?"
        number = f"INC{100000 + i}"

        for k, (st, ts) in enumerate(zip(states, t_points)):
            st_txt = st
            r = rng.random()
            if r < 0.02:
                st_txt = st.upper()
            elif r < 0.04:
                st_txt = st + " "
            final = k == len(states) - 1
            rows.append({
                "number": number,
                "incident_state": st_txt,
                "active": "true" if st not in ("Closed",) else "false",
                "reassignment_count": min(reassign, k) if not final else reassign,
                "reopen_count": reopen if final else 0,
                "sys_mod_count": k + (reopen if final else 0) + reassign * (1 if final else 0),
                "made_sla": "true" if made_sla else "false",
                "caller_id": caller,
                "opened_by": opened_by,
                "opened_at": fmt(op),
                "sys_created_by": f"Created by {rng.integers(1, 60)}",
                "sys_created_at": fmt(op),
                "sys_updated_by": f"Updated by {rng.integers(1, 120)}",
                "sys_updated_at": fmt(ts),
                "contact_type": contact if rng.random() > 0.01 else contact.lower(),
                "location": loc,
                "category": category_val,
                "subcategory": sub,
                "u_symptom": sym,
                "cmdb_ci": ci,
                "impact": impact,
                "urgency": IMPACT_LABEL[min(3, max(1, p if p <= 3 else 3))],
                "priority": PRIORITY_LABEL[p],
                "assignment_group": group if rng.random() > 0.01 else "?",
                "assigned_to": resolver if k > 0 else "?",
                "knowledge": "true" if rng.random() < 0.25 else "false",
                "u_priority_confirmation": "true" if rng.random() < 0.3 else "false",
                "notify": "Do Not Notify",
                "problem_id": f"Problem {rng.integers(1, 300)}" if rng.random() < 0.04 else "?",
                "rfc": "?",
                "vendor": "?",
                "caused_by": "?",
                "close_code": f"Code {rng.integers(1, 12)}" if st in ("Resolved", "Closed") else "?",
                "resolved_by": resolver if st in ("Resolved", "Closed") else "?",
                "resolved_at": fmt(resolved) if st in ("Resolved", "Closed") else "?",
                "closed_at": fmt(closed) if st == "Closed" else "?",
            })

    df = pd.DataFrame(rows)
    # duplicatas exatas (~0,5%)
    dup = df.sample(frac=0.005, random_state=seed)
    df = pd.concat([df, dup], ignore_index=True).sample(frac=1, random_state=seed).reset_index(drop=True)

    out = ROOT / "data" / "raw" / "incident_event_log.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"OK: {len(df):,} eventos / {df['number'].nunique():,} chamados -> {out}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12000)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    main(a.n, a.seed)
