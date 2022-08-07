# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import pkg_resources
from datetime import date

# -- Project information -----------------------------------------------------

project = "vallenae"
copyright = f"{date.today().year}, Vallen Systeme GmbH"
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
    "m2r2",
]

source_suffix = [".rst", ".md"]

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

templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

default_role = "autolink"
add_function_parentheses = True

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
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
# html_static_path = ["_static"]
