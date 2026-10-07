"""Compatibility entry point for actual exported visual revision 2 previews."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('render_redesign.py')),run_name='__main__')
