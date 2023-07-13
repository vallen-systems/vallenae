# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from datetime import date

import pkg_resources
from sphinx_gallery.sorting import FileNameSortKey

# -- Project information -----------------------------------------------------

project = "vallenae"
copyright = f"{date.today().year}, Vallen Systeme GmbH"  # noqa
author = "Lukas Berbuer, Daniel Altmann (Vallen Systeme GmbH)"
release = pkg_resources.get_distribution("vallenae").version

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "sphinx_autodoc_typehints",
    "sphinx_gallery.gen_gallery",
    "myst_parser",
]

source_suffix = [".rst", ".md"]

autosummary_generate = True
autodoc_member_order = "bysource"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/", None),
}

templates_path = ["templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

default_role = "autolink"
add_function_parentheses = True

sphinx_gallery_conf = {
     "examples_dirs": "../examples",  # path to your example scripts
     "gallery_dirs": "_examples",  # path to where to save gallery generated output
     "filename_pattern": "",
     "ignore_pattern": r"[\\,/]_",  # files starting with an underscore
     "within_subsection_order": FileNameSortKey,
     "download_all_examples": False,
}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
# html_static_path = ["_static"]
