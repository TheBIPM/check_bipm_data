import argparse
import logging
import pandas as pd
import numpy as np
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

    # Data will be collected in python lists (that will be transformed, in the
    # end, into pandas DataFrame)

    diffs_raw = []
    jumps_raw = []
    for filename in args.files:
        parse_clockfile(filename, diffs_raw, jumps_raw)

    values = pd.DataFrame(diffs_raw, columns=[
        'lab_code', 'clock_code', 'mjd', 'val'])
    steps = pd.DataFrame(jumps_raw, columns=[
        'lab_code', 'lab_acronym', 'clock_code', 'mjd', 'time_step',
        'freq_step'])
    clock_list = sorted(list(values['clock_code'].unique()))
    mjds = sorted(list(values['mjd'].unique()))
    print("Found {} clock(s):".format(len(clock_list)))
    values['type'] = 'utck-clock'
    # Then we will store values in "val" and 'type" will be one of:
    # 1diff, 2diff
    values['corrected'] = False

    to_be_concatenated = [values]
    for clock_code in clock_list:
        print("{:05d}".format(clock_code))
        this_clock_values = (
            values.loc[values['clock_code'] == clock_code].sort_values('mjd'))
        this_clock_steps = (
            steps.loc[steps['clock_code'] == clock_code].sort_values('mjd'))
        mjds = this_clock_values['mjd'].to_numpy()

        # Handle steps
        steps_corr_time = np.zeros(len(mjds))
        steps_corr_freq = np.zeros(len(mjds))
        if len(this_clock_steps) > 0:
            print("    {} step(s) found for {}".format(
                len(this_clock_steps), clock_code))
            for idx, jp in this_clock_steps.iterrows():
                print("     {} {} {}".format(
                    jp['mjd'],
                    jp['time_step'], jp['freq_step']))
                # Accumulate time correction in corresponding columns
                jp_mjd = float(jp['mjd'])
                jp_time = float(jp['time_step'])
                jp_freq = float(jp['freq_step'])
                steps_corr_time[mjds < jp_mjd] -= jp_time
                steps_corr_freq[mjds < jp_mjd] -= (jp_freq * (
                    mjds - jp_mjd)[mjds < jp_mjd])
        corrected_clock_values = this_clock_values.copy()
        corrected_clock_values['val'] += (steps_corr_time + steps_corr_freq)
        corrected_clock_values['corrected'] = True
        to_be_concatenated.append(corrected_clock_values)
        diff1 = this_clock_values.copy()
        diff1['val'] = this_clock_values['val'].diff().copy()
        diff1['type'] = '1diff'
        to_be_concatenated.append(diff1)
        diff2 = diff1.copy()
        diff2['val'] = diff1['val'].diff().copy()
        diff2['type'] = '2diff'
        to_be_concatenated.append(diff2)
        diff1_corr = corrected_clock_values.copy()
        diff1_corr['val'] = corrected_clock_values['val'].diff().copy()
        diff1_corr['type'] = '1diff'
        to_be_concatenated.append(diff1_corr)
        diff2_corr = diff1_corr.copy()
        diff2_corr['val'] = diff1_corr['val'].diff().copy()
        diff2_corr['type'] = '2diff'
        to_be_concatenated.append(diff2_corr)

    full_result = pd.concat(to_be_concatenated)

    mjdstart = values['mjd'].min()
    mjdstop = values['mjd'].max()
    # Plot data interactively
    # Filter on clock code
    clock_dropdown = alt.binding_select(options=clock_list,
                                        name="Clock code: ")
    clock_selection = alt.selection_single(fields=['clock_code'],
                                           bind=clock_dropdown,
                                           init={'clock_code': clock_list[0]},
                                           name="clock code")
    # Select between values / 1st diff / 2nd diff for display
    types = list(['utck-clock', '1diff', '2diff'])
    types_radio = alt.binding_radio(options=types, name="Value: ")
    types_selection = alt.selection_single(
        fields=['type'], bind=types_radio, init={'type': '1diff'})

    corrected = list([True, False])
    corrected_radio = alt.binding_radio(options=corrected,
                                        name="Correct for steps: ")
    corrected_selection = alt.selection_single(
        fields=['corrected'], bind=corrected_radio,
        init={'corrected': True})
    chart = alt.Chart(
        full_result,
        title=",".join([x.split('/')[-1] for x in args.files])
    ).mark_line(
        point=True
    ).encode(
        x=alt.X('mjd',
                axis=alt.Axis(format='d'),
                scale=alt.Scale(domain=(mjdstart, mjdstop))),
        y=alt.Y('val:Q',
                axis=alt.Axis(format='f'),
                scale=alt.Scale(zero=False)),
    ).add_selection(
        clock_selection
    ).transform_filter(
        clock_selection
    ).transform_filter(
        types_selection
    ).add_selection(
        types_selection
    ).transform_filter(
        corrected_selection
    ).add_selection(
        corrected_selection
    )

    chart.save("save.html")


if __name__ == "__main__":
    main()
