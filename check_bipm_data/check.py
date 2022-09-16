import argparse
import logging
import pandas as pd
import altair as alt
import os
import re


# Get version from pyproject.toml
from importlib import metadata
__version__ = metadata.version(__package__)
del metadata

# Regexes matching the clock and jump data line formats
# (used for detection)
minimal_clock_regex = r'^\d{5}\s+\d{5}\s+\d{7}\s+[+-]?\d+\.\d+'
jump_regex = (r'^\d{5}\.\d+\s+\d{7}\s+[+-]?\d+\.\d+\s+'
              r'[+-]?\d+\.\d+\s+\w+\s+\d{5}')


def parse_clockfile(filepath, diffs, jumps):
    """ Ingest data from provided file, checking its correctness while
    parsing
    """
    if not os.path.exists(filepath):
        logging.error("{}: file not found".format(filepath))
        return
    with open(filepath, 'rb') as fp:
        for i, line in enumerate(fp):
            # First we check this is line is ASCII
            try:
                ascii_line = line.decode('ascii')
            except UnicodeDecodeError:
                logging.warning(
                    'Non-ASCII char in file {} line {}: {}'.format(
                        filepath, i + 1, line))
                # If not ascii : do our best to get what we can
                ascii_line = line.decode('ascii', errors='ignore')
            if re.match(minimal_clock_regex, ascii_line):
                # This is a clock line, it can contain up to 5 clocks
                try:
                    mjd = int(ascii_line[:5])
                    lab_code = int(ascii_line[6:11])
                except ValueError:
                    logging.error(
                        'Cannot read MJD or labcode in '
                        '{} line {}: {}'.format(
                            filepath, i, line))
                # each line can contain up to 5 clocks
                # And this is fixed format
                for i in range(5):
                    start_col = 12 + i * 18
                    if start_col + 18 > len(line):
                        continue
                    try:
                        clock_code = int(ascii_line[
                            start_col:start_col + 7])
                        value = float(ascii_line[
                            start_col + 8: start_col + 17])
                        diffs.append([lab_code, clock_code, mjd, value])
                    except IndexError:
                        continue
                    except ValueError:
                        logging.error(
                            ('Cannot read clock_code {} or value {} in '
                             '{} line {}: {}').format(
                                ascii_line[start_col:start_col + 7],
                                ascii_line[start_col + 8:start_col + 17],
                                 filepath, i, line))
            if re.match(jump_regex, ascii_line):
                # This is a jump line
                try:
                    mjd = float(ascii_line[:8])
                    clock_code = int(ascii_line[9:16])
                    time_step = float(ascii_line[17:26])
                    freq_step = float(ascii_line[27:36])
                    lab_acronym = ascii_line[40:44]
                    lab_code = int(ascii_line[45:50])
                    jumps.append([lab_code, lab_acronym, clock_code,
                                  mjd, time_step, freq_step])
                except (IndexError, ValueError):
                    logging.error(
                        ('Cannot read jump data in '
                         '{} line {}: {}').format(
                             filepath, i, line))

                    if not re.match(r'[A-Z]+', lab_acronym):
                        logging.warning(
                            'Check lab acronym: {}'.format(lab_acronym))


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

    # Data will be collected in python lists (that wille be transformed, in the
    # end, into pandas DataFrame)

    diffs_raw = []
    jumps_raw = []
    for filename in args.files:
        parse_clockfile(filename, diffs_raw, jumps_raw)

    values = pd.DataFrame(diffs_raw, columns=[
        'lab_code', 'clock_code', 'mjd', 'utck-clock'])
    jumps = pd.DataFrame(jumps_raw, columns=[
        'lab_code', 'lab_acronym', 'clock_code', 'mjd', 'time_step',
        'freq_step'])
    clock_list = sorted(list(values['clock_code'].unique()))
    print("Found {} clock(s):".format(len(clock_list)))
    values['1st_diff'] = 0

    for clock_code in clock_list:
        print("{:05d}".format(clock_code))
        this_clock_jumps = jumps.loc[jumps['clock_code'] == clock_code]
        if len(this_clock_jumps) > 0:
            print("    {} jump(s) found for {}".format(
                len(this_clock_jumps), clock_code))
            for idx, jp in this_clock_jumps.iterrows():
                print("     {} {} {}".format(
                    jp['mjd'],
                    jp['time_step'], jp['freq_step']))
        values.loc[values['clock_code'] == clock_code, '1st_diff'] = (
            values.loc[values['clock_code'] == clock_code]['utck-clock'].diff()
        )
    mjdstart = values['mjd'].min()
    mjdstop = values['mjd'].max()
    # Plot data interactively
    clock_dropdown = alt.binding_select(options=clock_list)
    clock_selection = alt.selection_single(fields=['clock_code'],
                                           bind=clock_dropdown,
                                           init={'clock_code': clock_list[0]},
                                           name="clock code")
    chart = alt.Chart(values).mark_point().encode(
        x=alt.X('mjd', scale=alt.Scale(domain=(mjdstart, mjdstop))),
        y='1st_diff',
    ).add_selection(
        clock_selection
    ).transform_filter(
        clock_selection
    )
    chart.save("save.html")


if __name__ == "__main__":
    main()
