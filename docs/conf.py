# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
import pkg_resources
sys.path.insert(0, os.path.abspath("../"))


# -- Project information -----------------------------------------------------

project = "vallenae"
copyright = "2019, Vallen Systeme GmbH"
author = "Daniel Altmann, Lukas Berbuer (Vallen Systeme GmbH)"

# The full version, including alpha/beta/rc tags
release = pkg_resources.get_distribution("vallenae").version


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named "sphinx.ext.*") or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "sphinx.ext.autosummary",
    "sphinx_autodoc_typehints",
    "sphinx_gallery.gen_gallery",
]

autosummary_generate = True
autodoc_member_order = "bysource"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://docs.scipy.org/doc/numpy/", None),
    # "np": ("https://docs.scipy.org/doc/numpy/", None),
    # "scipy": ("https://docs.scipy.org/doc/scipy/reference/", None),
    # "matplotlib": ("https://matplotlib.org/", None),
    "pandas": ("https://pandas.pydata.org/pandas-docs/stable/", None),
}

todo_include_todos = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# The reST default role (used for this markup: `text`) to use for all documents.
default_role = "autolink"

# If true, "()" will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# Ignored by autosummary, bugfix implemented: https://github.com/sphinx-doc/sphinx/pull/6817
# Wait until bugfix is released with pypi package...
def skip(app, what, name, obj, would_skip, options):
    if name in ("__init__", "__iter__", "__len__", "__enter__", "__exit__"):
        return False
    return would_skip

def setup(app):
    app.connect("autodoc-skip-member", skip)

from sphinx_gallery.sorting import FileNameSortKey
sphinx_gallery_conf = {
     "examples_dirs": "../examples",  # path to your example scripts
     "gallery_dirs": "examples",  # path to where to save gallery generated output
     "filename_pattern": "",
     "within_subsection_order": FileNameSortKey,
     "download_all_examples": False,
}

import warnings
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message="Matplotlib is currently using agg, which is a non-GUI backend, so cannot show the figure.",
)


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
# html_theme = "alabaster"
import sphinx_rtd_theme
html_theme = "sphinx_rtd_theme"
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ["_static"]
