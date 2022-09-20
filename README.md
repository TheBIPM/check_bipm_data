# check\_bipm\_data




## About

This software is an example of how one can write validating scripts for UTC-participating clocks files.

It aims at checking compliance to [the clock data format](https://webtai.bipm.org/database/documents/clock-data_format.pdf) and also performs basic diagnostics.

*It is not meant to be exhaustive, nor mandatory: this is just an example*.

## Installation

Written in python 3.10, not tested with older versions.

Download the package then run `pip install .` in the directory. 

To develop and/or run in a separated environment, one can use https://python-poetry.org/

In the current state you can also simply download the "check.py" script, install the packages listes as dependencies in the `pyproject.toml` file, and directly run it through `python check.py`

## Usage

Call the `check_bipm_data` command with a space-separated list of clock files.

The script will gather all clock and steps data in the collection of files and display diagnostics on the console, and write the graphical output on disk in `save.html`. 







