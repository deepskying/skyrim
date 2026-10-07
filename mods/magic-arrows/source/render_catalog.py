"""Render the current catalog using final exported game NIF geometry."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('render_redesign.py')),run_name='__main__')
