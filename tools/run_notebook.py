"""Execute the standalone notebook in a fresh local kernel with live API data.

pip install -r requirements-dev.txt
python tools/run_notebook.py
Writes an executed copy under output; the submission source stays unexecuted.
The environment must already have requirements.txt installed. Only the %pip
installation cell is skipped; every analysis cell is executed unchanged.
"""
from pathlib import Path
import sys
import time
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

root = Path(__file__).resolve().parents[1]
nb = nbformat.read(root / "strategy_backtest.ipynb", as_version=4)
km = KernelManager(kernel_name="python3")
km.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
client = NotebookClient(nb, km=km, timeout=240, resources={"metadata": {"path": str(root)}},
                        skip_cells_with_tag="setup-install")
start = time.monotonic()
try:
    client.execute()
finally:
    (root / "output").mkdir(exist_ok=True)
    nbformat.write(nb, root / "output" / "strategy_backtest_executed.ipynb")
    if km.has_kernel:
        km.shutdown_kernel(now=True)
print(f"Executed analysis in a fresh kernel in {time.monotonic()-start:.1f}s.")
