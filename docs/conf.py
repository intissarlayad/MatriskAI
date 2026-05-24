import os
import sys
sys.path.insert(0, os.path.abspath('..'))

project = 'MatriskAI'
author = 'Intis'
release = '4.1'

extensions = [
    'myst_parser',
]

templates_path = []
exclude_patterns = []

html_theme = 'sphinx_rtd_theme'
html_static_path = []

# Enable markdown support
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}
