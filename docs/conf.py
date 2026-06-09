from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

project = "TSTLAN web platform"
author = "TSTLAN"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns: list[str] = []

language = "ru"
html_theme = "alabaster"

autodoc_member_order = "bysource"
autodoc_typehints = "description"
add_module_names = False
