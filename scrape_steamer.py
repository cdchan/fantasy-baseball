"""
Scrape Fangraphs Depth Charts projections

"""

import argparse
import datetime

import requests

from config import fangraphs_form_data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", action="store_true", help="prepare for auction draft")
    args = parser.parse_args()

    if args.draft:
        projection_type = "fangraphsdc"
    else:
        projection_type = "rfangraphsdc"  # rest of season projections

    # save projections for current and historical usage
    filenames = [
        'historical/depthcharts_{}_{:%Y%m%d}.csv',
        'depthcharts_{}.csv'
    ]

    params = {
        'pos': 'all',
        'type': projection_type,
    }

    player_types = [
        {'type': 'batters', 'stats': 'bat'},
        {'type': 'pitchers', 'stats': 'pit'}
    ]

    for player_type in player_types:
        params['stats'] = player_type['stats']

        r = requests.post("http://www.fangraphs.com/projections.aspx", params=params, data=fangraphs_form_data)

        write_csvs(r, player_type['type'], filenames)


def write_csvs(r, player_type, filenames):
    """
    Write the response to CSVs with `filenames`

    """
    for filename in filenames:
        with open(filename.format(player_type, datetime.datetime.today()), 'w') as output_file:
            output_file.write(r.text[1:].encode('utf8'))  # remove the first 3 characters which are BOM


if __name__ == '__main__':
    main()
