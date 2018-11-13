"""
Scrape historical scores for calculating current scoring environment

"""

import argparse
import os
import time
import random
import urlparse

import lxml.html
import pandas
import requests

from config import DATA_DIRECTORY, LEAGUE_ID, ESPN_COOKIE

STATS_BATTING = ['AB', 'H', 'R', 'HR', 'RBI', 'BB', 'SB', 'OBP']

STATS_PITCHING = ['IP', 'pH', 'ER', 'pBB', 'W', 'SV', 'ERA', 'WHIP', 'K9']
STATS_PITCHING_OLD = ['IP', 'W', 'SV', 'ERA', 'WHIP', 'K9']  # before 2017, the reported stats for pitching were different

BASE_URL = 'http://games.espn.com'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", action="store", default=2018, help="year to scrape scores for")
    args = parser.parse_args()

    year = args.year

    matchups = collect_urls(year, ESPN_COOKIE)

    output = pandas.DataFrame(matchups)

    columns = [
        'year',
        'matchup_period',
        'team_id',
        'opponent_team_id',
    ]
    columns += STATS_BATTING

    if int(args.year) >= 2017:
        columns += STATS_PITCHING
    else:
        columns += STATS_PITCHING_OLD

    output.to_csv('{}/scores_{}.csv'.format(DATA_DIRECTORY, year), columns=columns, encoding='utf8', index=False)


def collect_urls(year, cookie):
    """
    Collect links to all of the box scores

    """
    # retrieve the full schedule to examine
    params = {
        'leagueId': LEAGUE_ID,
        'seasonId': year,
    }

    r = requests.get("http://games.espn.com/flb/schedule", params=params, headers={'cookie': cookie})

    root = lxml.html.fromstring(r.text)

    links = root.cssselect('a')  # extract all links

    matchups = []

    for link in links:
        if 'boxscorefull' in link.get('href', ''):  # indicates a link to a box score
            if link.text != 'Box':  # ignore matchups that haven't happened yet, which are labelled as "Box"
                print BASE_URL + link.get('href')
                team_a, team_b = extract_boxscore(BASE_URL + link.get('href'), cookie)

                matchups.append(team_a)
                matchups.append(team_b)

                time.sleep(1 * random.random())  # don't want to get rate limited

    return matchups


def extract_boxscore(url, cookie):
    """
    Retrieves box score and extracts category scores

    """
    r = requests.get(url, headers={
        'cookie': cookie
    })

    params = urlparse.parse_qs(urlparse.urlparse(url).query)

    year = int(params['seasonId'][0])
    matchup_period = params['scoringPeriodId'][0]

    teams = team_stats(r.text, year)

    for team in teams:
        team['year'] = year
        team['matchup_period'] = matchup_period

    if teams[1]['team_id'] == '6':
        print 'hi'
        true_team_1_id = teams[1]['opponent_team_id']

        teams[0]['opponent_team_id'] = true_team_1_id
        teams[0]['team_id'] = '6'

        teams[1]['opponent_team_id'] = '6'
        teams[1]['team_id'] = true_team_1_id

    return teams[0], teams[1]


def team_stats(text, year):
    """
    Extract category scores

    """
    root = lxml.html.fromstring(text)

    teams = [{}, {}]

    team_id_rows = root.cssselect('td.teamName')
    score_rows = root.cssselect('tr.playerTableBgRowTotals')

    for i in xrange(2):
        teams[i]['team_id'] = extract_team_id(team_id_rows[i].cssselect('a')[0].get('href'))

        teams[i].update(extract_stats(score_rows[0 + i * 2], 'batting'))
        teams[i].update(extract_stats(score_rows[1 + i * 2], 'pitching', year))

    teams[0]['opponent_team_id'] = teams[1]['team_id']
    teams[1]['opponent_team_id'] = teams[0]['team_id']

    return teams


def extract_team_id(url):
    """
    Return team_id from url

    """
    return urlparse.parse_qs(urlparse.urlparse(url).query)['teamId'][0]


def extract_stats(row, kind, year=2017):
    """
    Extract the numbers from each row of the box score.

    """
    if kind == 'batting':
        stats = STATS_BATTING
    elif kind == 'pitching':
        if year >= 2017:
            stats = STATS_PITCHING
        else:
            stats = STATS_PITCHING_OLD

    scores = {}

    cells = row.cssselect('td')

    # the scores are at the end of the row
    for cell, stat in zip(cells[-len(stats):], stats):
        scores[stat] = cell.text_content()

    return scores


if __name__ == '__main__':
    main()
