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
        projection_types = ["fangraphsdc"]
    else:
        projection_types = []
        projection_types.append("rfangraphsdc")  # rest of season projections
        projection_types.append("steamer600u")

    for projection_type in projection_types:
        # save projections for current and historical usage
        filenames = [
            'historical/{}_{}_{:%Y%m%d}.csv',
            '{}_{}.csv'
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

            r = requests.post("https://www.fangraphs.com/projections.aspx", params=params, data=fangraphs_form_data)

            write_csvs(r, projection_type, player_type['type'], filenames)


def write_csvs(r, projection_type, player_type, filenames):
    """
    Write the response to CSVs with `filenames`

    """
    for filename in filenames:
        with open(filename.format(projection_type, player_type, datetime.datetime.today()), 'w') as output_file:
            output_file.write(r.text[1:].encode('utf8'))  # remove the first 3 characters which are BOM


if __name__ == '__main__':
    main()
