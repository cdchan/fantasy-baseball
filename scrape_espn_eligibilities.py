"""
Scrape ESPN position eligibilities

ESPN has their own mapping between numbers and positions. We only care about a subset of the positions:

0 = C
1 = B1
2 = B2
3 = B3
4 = SS
5 = OF
6 = MI
7 = CI
8 = LF
9 = CF
10 = RF
11 = DH
12 = UTIL
13 = P
14 = SP
15 = RP
16 = bench
17 = DL
18 = invalid
19 = infielder
21 = batter
22 = pitcher
23 = misc

TODO: fix ESPN json dependency
"""

import argparse
import datetime
import json

import pandas


# ESPN positions
POSSIBLE_POSITIONS = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH", "SP", "RP"]
POSITION_IDS = [0, 1, 2, 3, 4, 8, 9, 10, 11, 14, 15]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", action="store_true", help="prepare for auction draft")
    args = parser.parse_args()

    data_date = datetime.datetime(2019, 3, 10)  # datetime.datetime.today()

    position_mapping = {k: v for k, v in zip(POSSIBLE_POSITIONS, POSITION_IDS)}

    with open("data/espn_players_{:%Y-%m-%d}.json".format(date_date)) as f:
        players_json = json.load(f)

    players = []

    for player_json in players_json['players']:
        player = {
            'espn_id': player_json['id'],
            'espn_name': player_json['player']['fullName'],
            'espn_value': player_json['draftAuctionValue'],
        }

        for pos, espn_pos_id in position_mapping.items():
            if espn_pos_id in player_json['player']['eligibleSlots']:
                player[pos] = 1
            else:
                player[pos] = 0
        
        players.append(player)
    
    output = pandas.DataFrame(players)

    columns = ['espn_name', 'espn_id'] + POSSIBLE_POSITIONS

    output.to_csv('data/historical/espn_eligibilities_{:%Y-%m-%d}.csv'.format(data_date), columns=columns, encoding='utf8', index=False)

    output.to_csv('data/espn_eligibilities.csv', columns=columns, encoding='utf8', index=False)

    if args.draft:
        columns = ['espn_name', 'espn_id', 'espn_value']

        output[output['espn_value'] > 0].to_csv('data/espn_values.csv', columns=columns, encoding='utf8', index=False)


if __name__ == "__main__":
    main()