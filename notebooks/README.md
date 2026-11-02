# Notebook para o Kaggle

`analise_eda_kaggle.ipynb` é a versão **exploratória** (pandas + matplotlib) deste projeto, pensada para o Kaggle — uma narrativa de análise de dados, diferente da [versão de engenharia](../README.md) (pipeline Bronze/Silver/Gold em SQL/DuckDB). Já vem executado, com os gráficos prontos, usando a base real da UCI.

## Como subir no Kaggle

1. **Crie o dataset no Kaggle** (uma vez só):
   - Em [kaggle.com/datasets](https://www.kaggle.com/datasets) → **New Dataset**.
   - Envie o arquivo `incident_event_log.csv` (baixe em [archive.ics.uci.edu/dataset/498](https://archive.ics.uci.edu/dataset/498/incident+management+process+enriched+event+log)).
   - Em "License", selecione **CC BY 4.0** e credite: *Amaral, Fantinato & Peres (2018), DOI 10.24432/C57S4H*.
   - Dê um nome como `incident-management-event-log-uci`.

2. **Crie o notebook:**
   - No seu novo dataset → **New Notebook** (ele já vem com o dataset anexado em `/kaggle/input/...`), ou
   - Em [kaggle.com/code](https://www.kaggle.com/code) → **New Notebook** → **File → Upload Notebook** → selecione `analise_eda_kaggle.ipynb` → depois anexe o dataset em **Add Input**.

3. **Rode tudo** (Run All). O notebook já detecta automaticamente o caminho do CSV em `/kaggle/input/`.

4. Preencha o título do notebook (algo como *"Análise de chamados de Service Desk — ITSM real (ServiceNow)"*), adicione uma tag (`itsm`, `service-desk`, `eda`) e publique.

5. No GitHub (`service-desk-analytics-mvp`), me avise o link do notebook publicado que eu adiciono ele ao README principal.
