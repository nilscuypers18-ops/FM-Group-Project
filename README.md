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

Nils arbeitet dauerhaft auf `nils/work`. Der Workflow `.github/workflows/open-work-pull-request.yml` erstellt nach einem Push dieses Branches automatisch einen Pull Request nach `main`, sobald Dateiaenderungen vorliegen. Ein bereits offener Pull Request wird durch weitere Pushes aktualisiert. Nach einem Merge wird beim naechsten Push mit neuen Aenderungen ein neuer Pull Request erstellt.

1. Dateien hier mit Codex bearbeiten und in GitHub Desktop unter **Changes** pruefen.
2. Eine Commit-Nachricht eingeben und **Commit to nils/work** anklicken.
3. **Push origin** anklicken; beim ersten Veroeffentlichen heisst die Schaltflaeche **Publish branch**.
4. Auf GitHub unter **Pull requests** den automatisch vorbereiteten Request oeffnen, pruefen und mit **Merge pull request** sowie **Confirm merge** annehmen. Ein manuelles **Create pull request** entfaellt.

Den Branch `nils/work` nach dem Merge behalten. Vor neuer Arbeit **Fetch origin** ausfuehren; Aenderungen von `main` bei Bedarf in den Arbeitsbranch uebernehmen, insbesondere nach Beitraegen anderer Gruppenmitglieder. Codex kann diese lokale Zusammenfuehrung vorbereiten. `main` bleibt der gemeinsam freigegebene Stand.

Einmalige Voraussetzung fuer die Automatik: Unter **Settings > Actions > General > Workflow permissions** muss **Allow GitHub Actions to create and approve pull requests** aktiviert sein. Der Workflow erstellt Requests; die Freigabe und der Merge erfolgen durch die Gruppe.

Jedes Gruppenmitglied verwendet einen eigenen lokalen Klon. GitHub teilt Projektdateien und Commits; lokale Chatverlaeufe werden dadurch nicht geteilt.

Die Originale unter `inputs/course/` als Referenz aufbewahren; neue Analysen in eigenen Dateien erstellen. Gleichzeitige Aenderungen an demselben Notebook oder derselben Excel-Datei vorher absprechen.
