"""
Scrape ESPN rosters

"""

import datetime
import random
import time

import lxml.html
import pandas
import requests

from config import ESPN_COOKIES, LEAGUE_ID


def main():
    params = {
        'leagueId': LEAGUE_ID,
    }

    r = requests.get("http://games.espn.com/flb/leaguerosters", params=params, cookies=ESPN_COOKIES)

    root = lxml.html.fromstring(r.text)

    teams = root.cssselect('table.playerTableTable')  # locate the roster table for each team

    players = []

    # CSS selectors come from examining the table in a browser
    for team in teams:
        team_id = team.cssselect('th > a')[0].attrib['href'].split('=')[-1]

        for player_link in team.cssselect('td.playertablePlayerName > a:nth-child(1)'):
            players.append({
                'fantasy_team_id': team_id,
                'espn_id': player_link.attrib['playerid'],
            })

    output = pandas.DataFrame(players)

    output.to_csv('rosters.csv', encoding='utf8', index=False)
    output.to_csv('historical/rosters_{:%Y%m%d}.csv'.format(datetime.datetime.today()), encoding='utf8', index=False)


if __name__ == '__main__':
    main()
