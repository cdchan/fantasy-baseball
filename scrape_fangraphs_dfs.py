"""
Scrape Fangraphs DFS projections
"""
import datetime
import os
import urllib.parse

import lxml.html
import pandas
import requests

from config import (
    DATA_DIRECTORY,
    fangraphs_dfs_form_data
)

def main():
    params = {
        'pos': 'all',
        'stats': 'bat',
        'type': 'sabersim'
    }

    r = requests.post("https://www.fangraphs.com/dailyprojections.aspx", params=params, data=fangraphs_dfs_form_data)

    root = lxml.html.fromstring(r.content)

    fields = ['Name', 'Team', 'Game', 'Pos', 'PA', 'H', '1B', '2B', '3B', 'HR', 'R', 'RBI', 'SB', 'CS', 'BB', 'SO', 'Yahoo', 'FanDuel', 'DraftKings']

    players = []

    for tr in root.cssselect('div#DFSBoard1_dg1 tbody tr'):
        player = {}

        for field, td in zip(fields, tr.cssselect('td')):
            player[field] = td.text_content()

            if field == 'Name':
                parsed = urllib.parse.urlparse(td.cssselect('a')[0].get('href'))
                player['fg_id'] = urllib.parse.parse_qs(parsed.query)['playerid'][0]

        players.append(player)

    players = pandas.DataFrame(players, columns=(fields + ['fg_id']))

    base_file = "fangraphs_dfs_{:%Y-%m-%d}.csv".format(datetime.date.today())

    archive_file = os.path.join(
        DATA_DIRECTORY,
        "daily",
        base_file
    )

    players.to_csv(archive_file, encoding='utf8', index=False)


if __name__ == '__main__':
    main()
