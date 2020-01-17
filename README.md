# Vallen AE Python Tools

[![Build Status](https://travis-ci.org/vallen-systems/pyVallenAE.svg?branch=master)](https://travis-ci.org/vallen-systems/pyVallenAE)

Python tools to extract and analyze data from Vallen Systeme database files, e.g. files like sample.pridb or sample.tradb.

## Playing around
Setup a virutal invironment, install the dependencies and run some
samples like this:

    # install venv
    python -m venv env # use python3 if python is mapped to python2
    
    # activate env
    # linux
    source env/bin/activate
    # windows cmd
    .\env\scripts\activate.bat
    # windows powershell
    .\venv\Scripts\Activate.ps1
    
    # install dependencies
    pip install -r requirements.txt
    
    # execute random example
    python examples\read_and_plot.py

## Running the tests
Simply type this in the root directory:

    pytest
