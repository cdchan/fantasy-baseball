"""
Scrape player eligibilities from ESPN.

"""

import random
import time

import lxml.html
import pandas
import requests


# ESPN positions
POSSIBLE_POSITIONS = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH", "SP", "RP"]


def main():
    player_types = [
        {'type': "batter", 'group': 1},
        {'type': "pitcher", 'group': 2},
    ]

    for player_type in player_types:
        output = scrape_player_type(player_type['group'])

        columns = ['name', 'espn_id'] + POSSIBLE_POSITIONS

        output.to_csv('{}_eligibilities.csv'.format(player_type['type']), columns=columns, encoding='utf8', index=False)


def scrape_player_type(group):
    """
    Scrape batters or pitchers

    """
    params = {
        'slotCategoryGroup': group,
        'startIndex': 0,
    }

    players = []

    while True:
        r = requests.get("http://games.espn.com/flb/tools/eligibility", params=params)
        print r.encoding  # need to figure out accents in names

        print u"working on player {}".format(params['startIndex'])

        if r.status_code == 200:
            root = lxml.html.fromstring(r.text.encode('utf-8'))  # parse into HTML tree

            for row in root.cssselect('tr.pncPlayerRow'):  # loop over players
                player = process_row(row)

                players.append(player)

            # check for pagination
            if 'NEXT' in root.cssselect('div.paginationNav')[0].text_content():
                # increment to the next page of players
                params['startIndex'] += 50

                time.sleep(5 * random.random())  # don't want to get rate limited
            else:
                break
        else:  # if status code is bad, stop
            break

    output = pandas.DataFrame(players)

    return output


def process_row(row):
    """
    Parse player table row to return player eligibilities

    """
    player = {}

    player['name'] = row.cssselect('td.playertablePlayerName')[0].cssselect('a')[0].text

    player['espn_id'] = row.cssselect('td.playertablePlayerName')[0].cssselect('a')[0].get('playerid')

    position_cells = row.cssselect('td[id^="eligibility"]')

    for position, cell in zip(POSSIBLE_POSITIONS, position_cells):
        if cell.text_content() in ('PP', 'X'):  # this means the player has eligibility for this position
            player[position] = 1
        else:
            player[position] = 0

    return player


if __name__ == '__main__':
    main()
