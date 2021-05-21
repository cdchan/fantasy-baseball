"""
Scrape Fangraphs playing time in the past 14 days

"""

import datetime
import os

import requests

from config import (
    CURRENT_YEAR,
    DATA_DIRECTORY,
    fangraphs_leaderboard_form_data
)


def main():
    player_types = [
        {'type': 'batter', 'stats': 'bat', 'month': 2},  # month = 2 = past 2 weeks
        {'type': 'pitcher', 'stats': 'pit', 'month': 2},  # month = 0 = full season
    ]

    params = {
        'pos': 'all',
        'lg': 'all',
        'qual': 0,
        'type': 8,
        'season': CURRENT_YEAR,
        'season1': CURRENT_YEAR,
        'ind': 0,
        'team': '',
        'rost': '',
        'age': 0,
        'filter': '',
        'players': '',
    }

    for player_type in player_types:
        # save projections for current and historical usage
        filenames = [
            os.path.join(DATA_DIRECTORY, 'historical', "{}_playing_time_{:%Y-%m-%d}.csv".format(player_type['type'], datetime.datetime.today())),
            os.path.join(DATA_DIRECTORY, '{}_playing_time.csv'.format(player_type['type']))
        ]

        params['stats'] = player_type['stats']
        params['month'] = player_type['month']

        r = requests.post("https://www.fangraphs.com/leaders.aspx", params=params, data=fangraphs_leaderboard_form_data)

        write_csvs(r, filenames)


def write_csvs(r, filenames):
    """
    Write the response to CSVs with `filenames`

    """
    for filename in filenames:
        with open(filename, 'wb') as output_file:
            output_file.write(r.text[1:].encode('utf8'))  # remove the first 3 characters which are BOM


if __name__ == '__main__':
    main()
