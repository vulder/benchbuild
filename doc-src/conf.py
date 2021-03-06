#!/usr/bin/env python3
import recommonmark
from pkg_resources import DistributionNotFound, get_distribution
from recommonmark.parser import CommonMarkParser
from recommonmark.transform import AutoStructify

try:
    __version__ = get_distribution("benchbuild").version
except DistributionNotFound:
    pass

project = 'benchbuild'
copyright = '2018, Andreas Simbürger'
author = 'Andreas Simbürger'
version = '.'.join(__version__.split('.')[:2])
release = __version__
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode']

templates_path = ['_templates']
source_suffix = ['.rst', '.md']
source_parsers = {
	'.md': 'recommonmark.parser.CommonMarkParser',
}
master_doc = 'index'
language = 'en'
pygments_style = 'sphinx'
todo_include_todos = True
html_theme = 'nature'
# html_theme_options = {}
# html_static_path = ['_static']


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'benchbuild', 'benchbuild Documentation',
     [author], 1)
]

def setup(app):
    app.add_config_value('recommonmark_config', {
        'auto_toc_tree_section': 'Contents',
        'enable_eval_rst': True,
        'enable_auto_doc_ref': True,
    }, True)
    app.add_transform(AutoStructify)
