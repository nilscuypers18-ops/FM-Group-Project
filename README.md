# FM Group Project

Gemeinsames Projekt fuer den Kurs Financial Modelling.

## Aktueller Ansatz

Konservatives Family Office mit langfristigem Vermoegenserhalt und Wachstum; Fokus auf Total Return und ein flexibles Mandat.

- Core: 60 % AGG (US-Anleihen).
- Satellite: 40 % SPY (US-Aktien), GLD (Gold) und DBC (Rohstoffe).
- Monatliches Rebalancing; Trendfilter anhand des gleitenden 10-Monats-Durchschnitts.
- Gewichtung der Satellites anhand inverser Volatilitaet der vergangenen zwoelf Monatsrenditen; ausgeschaltete Anteile werden in T-Bills gehalten.
- Signal am Monatsende fuer die Umsetzung im Folgemonat; Transaktionskosten von 10 Basispunkten je Einheit Turnover.
- Monatliche Daten in USD; Backtest Januar 2007 bis Oktober 2026 mit ausreichender Datenhistorie fuer die Startsignale.
- Vergleiche: 60 % SPY / 40 % AGG sowie eine Buy-and-hold-Version derselben Anlagen.

Die genaue Verteilung zwischen aktiven Satellites und Cash, die Cash-Datenreihe und die Turnover-Konvention sind vor der Implementierung noch festzulegen.

## Dateien

- `2270_FM_group_assignment_v2 (1).pdf`: Aufgabenstellung.
- `inputs/course/`: unveraenderte Vorlesungsnotebooks, Einfuehrung, Formelsammlung und Syllabus aus dem Kurs.
- `requirements.txt`: Python-Pakete fuer Datenabruf, Analyse, Diagramme und einen lokalen Jupyter-Kernel.
- `output/` und `tmp/`: bei Bedarf erzeugte Ergebnisse, Hilfsdateien und API-Caches; werden nicht in Git aufgenommen.

## Lokal arbeiten

Das Repository in GitHub Desktop klonen und genau diesen lokalen Ordner als Projekt in Codex oeffnen. Codex bearbeitet die Dateien dieses Ordners; GitHub Desktop zeigt diese Aenderungen unter **Changes**.

Fuer eine neue Python-Umgebung im Projektordner:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Fuer neue Analysen `.venv` als Python-Umgebung beziehungsweise Notebook-Kernel auswaehlen. Fuer Marktdatenabrufe ist eine Internetverbindung erforderlich. Kursnotebooks sind Referenzmaterial und koennen weitere Pakete benoetigen.

## Zusammenarbeit mit GitHub Desktop

1. Vor einer neuen Aufgabe auf `main` wechseln und **Fetch origin / Pull origin** ausfuehren. Vorhandene eigene Aenderungen zuvor committen.
2. Ueber **Current branch > New branch** einen eigenen Branch anlegen, zum Beispiel `nils/portfolio-analysis`.
3. Dateien lokal mit Codex bearbeiten und die Aenderungen unter **Changes** pruefen.
4. Eine Commit-Nachricht eingeben und **Commit to ...** anklicken.
5. Beim ersten Mal **Publish branch**, danach **Push origin** anklicken.
6. Auf GitHub einen Pull Request von diesem Branch nach `main` oeffnen, gemeinsam pruefen und online mergen.
7. Anschliessend lokal auf `main` wechseln und erneut **Fetch origin / Pull origin** ausfuehren.

Jedes Gruppenmitglied verwendet einen eigenen lokalen Klon. GitHub teilt Projektdateien und Commits; lokale Chatverlaeufe werden dadurch nicht geteilt.

Die Originale unter `inputs/course/` als Referenz aufbewahren; neue Analysen in eigenen Dateien erstellen. Gleichzeitige Aenderungen an demselben Notebook oder derselben Excel-Datei vorher absprechen.

## Strategy code (English)

Core-satellite trend portfolio for a family office: 60% AGG core, 40% satellite across SPY, GLD and DBC.
A satellite asset is held only when its month-end price is above its 10-month moving average,
otherwise its share goes to 3-month T-bills (`^IRX`). Satellite shares are set by inverse 12-month volatility.
Monthly rebalancing, signal at month-end t and trade for month t+1, 10 bps cost per unit of turnover.
Backtest Jan 2007 to Oct 2026, compared with a monthly rebalanced 60/40 SPY/AGG benchmark and buy & hold of the same assets.

| File | What it does |
|---|---|
| `strategy.py` | All calculations for the Streamlit app: data download, signals, weights, backtest, metrics |
| `strategy_backtest.ipynb` | Submitted notebook for the prospectus. Self-contained: it defines the same functions inline and runs on its own in Google Colab |
| `app.py` | Streamlit app: change MA length, core weight and costs |

**Keep them in sync:** the notebook contains a copy of every function in `strategy.py`. If you change the logic in one, make the same change in the other, so the app and the prospectus numbers stay consistent.

Run the app locally: `pip install -r requirements.txt` then `streamlit run app.py`.
Deploy: share.streamlit.io > New app > this repo, branch `main`, main file `app.py`.

Data: Yahoo Finance via `yfinance` (adjusted close, USD), daily prices converted to month-end.
T-bill monthly return = previous month-end `^IRX` yield / 100 / 12.

x
