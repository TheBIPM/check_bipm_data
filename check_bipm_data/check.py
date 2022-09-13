import argparse
import logging
import os
import re


# Get version from pyproject.toml
from importlib import metadata
__version__ = metadata.version(__package__)
del metadata

# Regexes matching the clock and jump data line formats
# (used for detection)
minimal_clock_regex = r'^\d{5}\s+\d{5}\s+\d{7}\s+[+-]?\d+\.\d+'
jump_regex = r'^\d{5}\s+\d{7}\s+[+-]?\d+\.\d+\s+[+-]?\d+\.\d+\s+\w+\s+\d{5}'


def parse_clockfile(filepath):
    """Parse clock files and display errors and warnings"""
    if not os.path.exists(filepath):
        logging.error("{}: file not found".format(filepath))
        return
    with open(filepath, 'rb') as fp:
        # File will be parsed line by line
        for i, line in enumerate(fp):
            # First we check this is ASCII
            try:
                ascii_line = line.decode('ascii')
            except UnicodeDecodeError:
                logging.warning(
                    'Non-ASCII char in file {} line {}: {}'.format(
                        filepath, i + 1, line))
                # If not ascii : do our best to get what we can
                ascii_line = line.decode('ascii', errors='ignore')
            if re.match(minimal_clock_regex, ascii_line):
                # If this is a clock line, it can contain up to 5 clocks
                try:
                    mjd = int(ascii_line[:5])
                    labcode = int(ascii_line[6:11])
                except ValueError:
                    logging.error(
                        'Cannot read MJD or labcode in '
                        '{} line {}: {}'.format(
                            filepath, i, line))
                # each line can contain up to 5 clocks
                for i in range(5):


                import ipdb;ipdb.set_trace()  # noqa

            if re.match(jump_regex, ascii_line):
                pass



def main():
    parser = argparse.ArgumentParser(description=(
        "Check clock files and perform quickview diagnostics"))
    parser.add_argument(
        "files",
        nargs='+',
        help="File(s) to be checked")
    parser.add_argument("--version", action="version",
                        version="%(prog)s version " + __version__)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig()

    for filename in args.files:
        parse_clockfile(filename)


if __name__ == "__main__":
    main()
