import os
import sys
sys.path.insert(0, os.path.abspath('..'))

# ── Informations du projet ──────────────────────────────────────
project = 'MatriskAI'
author = 'Intissar LAYAD & Aya IDHAMOUCH'
copyright = '2026, Intissar LAYAD & Aya IDHAMOUCH'
release = '4.2'
language = 'fr'

# ── Extensions ──────────────────────────────────────────────────
extensions = [
    'myst_parser',
]

# ── MyST (Markdown) configuration ───────────────────────────────
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "tasklist",
]
myst_heading_anchors = 3

# ── Chemins ─────────────────────────────────────────────────────
templates_path = []
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# ── Thème HTML ──────────────────────────────────────────────────
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_logo = '_static/images/logo_nouveau.jpeg'
html_favicon = '_static/images/logo_nouveau.jpeg'

html_theme_options = {
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': True,
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'includehidden': True,
    'titles_only': False,
}

html_show_sourcelink = False
