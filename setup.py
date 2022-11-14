from setuptools import setup, find_packages
from os import path

HERE = path.abspath(path.dirname(__file__))

with open(path.join(HERE, "README.md"), encoding="utf-8") as f:
    LONG_DESCRIPTION = f.read()

INSTALL_REQUIRES = [
    "numpy",
    "pandas>=0.24",
    "soundfile",
    "tqdm",
    "typing_extensions",
]

EXTRAS_REQUIRE = {
    "docs": [
        "sphinx>=5",
        "sphinx-autodoc-typehints",
        "sphinx-rtd-theme",
        "sphinx-gallery",
        "pillow",  # required by sphinx-gallery
        "m2r2",  # include markdown files
        "matplotlib",  # used in examples
        "numba",  # used in location example
        "scipy",  # used in location and multiprocessing example
    ],
    "tests": [
        "coverage[toml]>=5",  # pyproject.toml support
        "pytest>=6",  # pyproject.toml support
        "pytest-benchmark",
    ],
    "tools": [
        "mypy>=0.9",  # pyproject.toml support
        "pylint>=2.5",  # pyproject.toml support
        "tox>=3.4",  # pyproject.toml support
    ],
}

EXTRAS_REQUIRE["dev"] = EXTRAS_REQUIRE["docs"] + EXTRAS_REQUIRE["tests"] + EXTRAS_REQUIRE["tools"]

setup(
    name="vallenae",
    version="0.7.0",
    description="Extract and analyze Acoustic Emission measurement data",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://github.com/vallen-systems/pyVallenAE",
    author="Lukas Berbuer, Daniel Altmann (Vallen Systeme GmbH)",
    author_email="software@vallen.de",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    keywords=[
        "Vallen",
        "Acoustic Emission",
        "AMSY",
        "WaveLine",
        "data acquisition",
        "analysis",
        "timepicker",
        "SQLite",
        "pridb",
        "tradb",
        "trfdb",
    ],
    packages=find_packages("src"),
    package_dir={"": "src"},
    python_requires=">=3.6",
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
    entry_points={
        "pyinstaller40": [
            "hook-dirs = vallenae._pyinstaller:get_hook_dirs",
            "tests     = vallenae._pyinstaller:get_tests",
        ],
    },
    package_data={
        "vallenae": ["io/schema_templates/*.sql"],
    },
    project_urls={
        "Bug Reports": "https://github.com/vallen-systems/pyVallenAE/issues",
        "Source": "https://github.com/vallen-systems/pyVallenAE",
    },
)
