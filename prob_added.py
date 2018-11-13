"""
Calculate marginal utility of each stat

This uses an exponential decay to weight previous years scores. The current year has a weight of 1, the previous year has a weight of 0.25, and the year before that has a weight of 0.0625.

Since each year has 25 scoring weeks, that means that 4 weeks into the current season, the weights are:

* current season = 1 * 4 weeks
* previous season = 0.25 * 25 weeks
* 2 years seasons ago = 0.25 * 0.25 * 25 weeks
= ~ 11.8 total weight

Therefore the current season would have an influence of about 34%. Halfway through the current season (12 weeks) would have an influence of 61%.
"""

import os

import numpy
import pandas


from sklearn.linear_model import LogisticRegression
from sklearn.externals import joblib


from config import CURRENT_YEAR, DATA_DIRECTORY


YEARS = [2016, 2017, 2018]


def main():
    calculate_probability_added_batting()

    calculate_probability_added_pitching()


def calculate_probability_added_batting():
    """
    Calculate the winning probability added for each category when an additional unit is added

    """
    scores = load_scores(YEARS)

    scores['ePA'] = scores['AB'] + scores['BB']
    scores['OBP_big'] = scores['OBP'] * 1000

    batting_categories = ['ePA', 'R', 'RBI', 'HR', 'SB', 'OBP_big']
    batter_categories_info = {
        'models': {},
        'p_added': {},
    }

    for category in batting_categories:
        train = scores[['year', 'year_weight', 'matchup_id', category]].copy()

        train['winner'] = train.groupby('matchup_id')[category].transform(lambda x: numpy.where(x == x.max(), 1, 0))

        lm = LogisticRegression()
        lm.fit(train[[category]], train['winner'], sample_weight=train['year_weight'])
        batter_categories_info['models'][category] = lm

    joblib.dump(batter_categories_info, 'batters.pkl')

    return True


def calculate_probability_added_pitching():
    """
    Calculate the winning probability added for each category when an additional unit is added

    """
    scores = load_scores(YEARS)

    pitcher_categories = ['IP', 'W', 'SV', 'ERA', 'WHIP', 'K9']
    pitcher_categories_info = {
        'models': {},
        'p_added': {},
    }

    for category in pitcher_categories:
        train = scores[['year', 'year_weight', 'matchup_id', category]].copy()

        train['winner'] = train.groupby('matchup_id')[category].transform(lambda x: numpy.where(x == x.max(), 1, 0))

        lm = LogisticRegression()
        lm.fit(train[[category]], train['winner'], sample_weight=train['year_weight'])
        pitcher_categories_info['models'][category] = lm

    joblib.dump(pitcher_categories_info, 'pitchers.pkl')

    return True


def load_scores(years):
    """
    Load data files containing scores

    """
    scores = []

    for year in years:
        scores.append(pandas.read_csv(os.path.join(DATA_DIRECTORY, 'scores_{year}.csv'.format(year=year))))

    scores = pandas.concat(scores)

    # create unique matchup is by concating year, matchup period, team id 1, team id 2
    scores['matchup_id'] = scores['year'].astype(str).str.cat(
        [
            scores['matchup_period'].astype(str),
            scores[['team_id', 'opponent_team_id']].max(axis=1).astype(str),
            scores[['team_id', 'opponent_team_id']].min(axis=1).astype(str),
        ],
        sep='_'
    )

    scores['year_weight'] = 0.25 ** (CURRENT_YEAR - scores['year'])

    scores = scores[scores['team_id'] != 6]

    return scores


if __name__ == '__main__':
    main()
