# Vallen AE Python Tools
Python tools to extract and analyze data from Vallen Systeme database files, e.g. files like sample.pridb or sample.tradb.

## Playing around
Setup a virutal invironment, install the dependencies and run some
samples like this:

    python -m venv env
    .\env\scripts\activate.bat  # an *.sh file under linux of course
    pip install -r requirements.txt
    python examples\read_and_plot.py

## Running the tests
Simply type this in the root directory:

    pytest