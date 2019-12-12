from setuptools import setup, find_packages
from os import path

HERE = path.abspath(path.dirname(__file__))

with open(path.join(HERE, "README.md"), encoding="utf-8") as f:
    LONG_DESCRIPTION = f.read()

INSTALL_REQUIRES = [
    "numpy",
    "scipy",
    "pandas",
    "matplotlib",
    "soundfile",
    "numba",
    "tqdm",
    "typing-extensions",
]

EXTRAS_REQUIRE = {
    "docs": [
        "sphinx",
        "sphinx-autodoc-typehints",
        "sphinx-rtd-theme",
        "sphinx-gallery",
    ],
    "tests": [
        "pytest",
        "pytest-cov",
    ],
}

EXTRAS_REQUIRE["dev"] = EXTRAS_REQUIRE["tests"] + EXTRAS_REQUIRE["docs"]

setup(
    name="vallenae",
    version="0.1",
    description="Extract and analyze Acoustic Emission measurement data",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://github.com/vallen-systems/pyVallenAE",
    author="Daniel Altmann, Lukas Berbuer (Vallen Systeme GmbH)",
    author_email="software@vallen.de",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Customer Service",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        # "Programming Language :: Python :: 3.8",
        "Operating System :: OS Independent",
    ],
    keywords="vallen acoustic-emission amsy sqlite pridb tradb",
    packages=find_packages("src"),
    package_dir={"": "src"},
    python_requires=">=3.5",
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
    package_data={
        "vallenae": ["io/schema_templates/*.sql"],
    },
    project_urls={
        "Bug Reports": "https://github.com/vallen-systems/pyVallenAE/issues",
        "Source": "https://github.com/vallen-systems/pyVallenAE",
    },
)
