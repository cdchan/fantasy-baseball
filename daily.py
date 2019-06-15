"""
Best hitters to start today for daily lineups for Yahoo leagues
"""
import datetime

import pandas

from config import (
    DATA_DIRECTORY
)
from yahoo import Yahoo


def main():
    yahoo_league_directory = "yahoo-new"

    date = datetime.date.today()

    dfs = pandas.read_csv("{}/daily/fangraphs_dfs_{:%Y-%m-%d}.csv".format(DATA_DIRECTORY, date), dtype={'fg_id': 'object'})

    league = Yahoo("yahoo-new", "rfangraphsdc")

    dfs = dfs.merge(league.player_mapping[['fg_id', 'yahoo_id']], how='left')
    dfs = dfs.merge(league.rosters[['yahoo_id', 'team_id']], how='left')

    dfs[(dfs['team_id'] == league.my_team_id) | (dfs['team_id'].isnull())].to_csv("{}/today.csv".format(yahoo_league_directory), index=False, encoding='utf8')


if __name__ == '__main__':
    main()
