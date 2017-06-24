"""
Calculate marginal utility of each stat

"""

import os

import numpy
import pandas


from config import DATA_DIRECTORY


YEARS = [2016, 2017]


def calculate_marginal(s, high=0.8, low=0.2):
    """
    The marginal increase in `s` based on a linear extrapolation between the low and high percentiles

    By default, this is calculated by the linear difference between the 20th% and the 80th%

    """
    return (s.quantile(high) - s.quantile(low)) / (high - low)


def load_scores():
    """
    Load data files containing scores

    """
    scores = []

    for year in YEARS:
        scores.append(pandas.read_csv(os.path.join(DATA_DIRECTORY, 'scores_{year}.csv'.format(year=year))))

    return pandas.concat(scores)


def calculate_marginals_batter():
    """
    Calculate weighted marginal values for batter stats

    """
    scores = load_scores()

    marginals = scores[['year', 'R', 'RBI', 'HR', 'SB', 'OBP']].groupby('year', as_index=False).aggregate(calculate_marginal)

    means = scores[['year', 'AB', 'BB', 'R', 'RBI', 'HR', 'SB', 'OBP']].groupby('year', as_index=False).aggregate(numpy.mean)  # OBP could be a weighted average, but each H2H is independent

    marginals['xOB'] = marginals['OBP'] * (means['AB'] + means['BB'])

    weights = 0.5 ** (max(YEARS) - marginals['year'])
    weights = weights / weights.sum()

    weighted_marginals = marginals[['R', 'RBI', 'HR', 'SB', 'OBP', 'xOB']].groupby(lambda _: True, as_index=False).aggregate(lambda x: (x * weights).sum())

    weighted_means = means[['AB', 'BB', 'R', 'RBI', 'HR', 'SB', 'OBP']].groupby(lambda _: True, as_index=False).aggregate(lambda x: (x * weights).sum())

    print weighted_means
    print weighted_marginals

    return weighted_marginals, weighted_means


def calculate_marginals_pitcher():
    """
    Calculate weighted marginal values for pitcher stats

    """
    scores = load_scores()

    # fix IP string format to numbers
    scores['IP'] = scores['IP'].round() + (scores['IP'] - scores['IP'].round()) * 10 / 3

    # K = K/9 / 9 * IP
    scores['K'] = scores['K9'] / 9 * scores['IP']

    marginals = scores[['year', 'IP', 'W', 'SV', 'ERA', 'WHIP', 'K9']].groupby('year', as_index=False).aggregate(calculate_marginal)

    means = scores[['year', 'IP', 'W', 'SV', 'ERA', 'WHIP', 'K9']].groupby('year', as_index=False).aggregate(numpy.mean)

    # our teams approximate 32 IP per week
    # ideally calculate the correct mean IP by team
    marginals['xER'] = marginals['ERA'] * 32 / 9  # ERA = ER / IP * 9 ; ER = ERA * IP / 9
    marginals['xWH'] = marginals['WHIP'] * 32  # WHIP = (walks + hits) / IP
    marginals['xK'] = marginals['K9'] * 32 / 9  # K9 = K / IP * 9

    weights = 0.5 ** (max(YEARS) - marginals['year'])
    weights = weights / weights.sum()

    weighted_marginals = marginals[['IP', 'W', 'SV', 'ERA', 'WHIP', 'K9', 'xER', 'xWH', 'xK']].groupby(lambda _: True, as_index=False).aggregate(lambda x: (x * weights).sum())

    weighted_means = means[['IP', 'W', 'SV', 'ERA', 'WHIP', 'K9']].groupby(lambda _: True, as_index=False).aggregate(lambda x: (x * weights).sum())

    print weighted_means
    print weighted_marginals

    return weighted_marginals, weighted_means
