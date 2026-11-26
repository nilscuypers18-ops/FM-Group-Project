# FM Group Project

Gemeinsames Projekt fuer den Kurs Financial Modelling.

## Dateien

- `2270_FM_group_assignment_v2 (1).pdf`: Aufgabenstellung.
- `ETF_Datencheck.ipynb`: bisheriges Arbeitsnotebook zum ETF-Datencheck.
- `inputs/course/`: unveraenderte Vorlesungsnotebooks, Einfuehrung, Formelsammlung und Syllabus aus dem Kurs.
- `requirements.txt`: Python-Pakete fuer das Arbeitsnotebook und einen lokalen Jupyter-Kernel.
- `output/`: erzeugte Ergebnisse; wird nicht in Git aufgenommen.
- `tmp/`: lokale Hilfsdateien und API-Caches; wird nicht in Git aufgenommen.

## Lokal arbeiten

Das Repository in GitHub Desktop klonen und genau diesen lokalen Ordner als Projekt in Codex oeffnen. Codex bearbeitet die Dateien dieses Ordners; GitHub Desktop zeigt diese Aenderungen unter **Changes**.

Fuer eine neue Python-Umgebung im Projektordner:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Das Notebook in einem Notebook-Editor oeffnen und `.venv` als Python-Kernel auswaehlen. Fuer Marktdatenabrufe ist eine Internetverbindung erforderlich. Die erste Notebook-Zelle prueft die verwendeten Paketversionen und installiert sie bei Bedarf. Kursnotebooks sind Referenzmaterial und koennen weitere Pakete benoetigen.

## Zusammenarbeit mit GitHub Desktop

1. Vor einer neuen Aufgabe auf `main` wechseln und **Fetch origin / Pull origin** ausfuehren. Vorhandene eigene Aenderungen zuvor committen.
2. Ueber **Current branch > New branch** einen eigenen Branch anlegen, zum Beispiel `nils/portfolio-analysis`.
3. Dateien lokal mit Codex bearbeiten und die Aenderungen unter **Changes** pruefen.
4. Eine Commit-Nachricht eingeben und **Commit to ...** anklicken.
5. Beim ersten Mal **Publish branch**, danach **Push origin** anklicken.
6. Auf GitHub einen Pull Request von diesem Branch nach `main` oeffnen, gemeinsam pruefen und online mergen.
7. Anschliessend lokal auf `main` wechseln und erneut **Fetch origin / Pull origin** ausfuehren.

Der erste vorbereitete Arbeitsbranch heisst `nils/project-setup`. Seine Dateien sind noch nicht committet. Jedes Gruppenmitglied verwendet einen eigenen lokalen Klon. GitHub teilt Projektdateien und Commits; lokale Chatverlaeufe werden dadurch nicht geteilt.

Die Originale unter `inputs/course/` als Referenz aufbewahren; neue Analysen in eigenen Dateien erstellen. Gleichzeitige Aenderungen an demselben Notebook oder derselben Excel-Datei vorher absprechen.
