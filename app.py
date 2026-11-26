"""Streamlit app for the core-satellite trend portfolio.

The strategy calculations are NOT written here: they are read from the notebook
(strategy_backtest.ipynb). Every notebook code cell that starts with
"# STRATEGY FUNCTIONS" is executed below, so a change in the notebook is picked
up by the app automatically. Run locally with:  streamlit run app.py
"""
import json
import sys
from pathlib import Path

NOTEBOOK = Path(__file__).with_name("strategy_backtest.ipynb")
MARKER = "# STRATEGY FUNCTIONS"


def load_strategy_cells(namespace):
    """Execute the notebook's strategy cells inside `namespace`."""
    cells = json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]
    sources = ["".join(c["source"]) for c in cells if c["cell_type"] == "code"]
    strategy = [s for s in sources if s.startswith(MARKER)]
    if not strategy:
        raise RuntimeError(f"No cells starting with '{MARKER}' found in {NOTEBOOK.name}.")
    for source in strategy:
        exec(source, namespace)


load_strategy_cells(globals())


if __name__ == "__main__":
    from portal import render_app

    render_app(sys.modules[__name__])
