"""
Batter valuation

"""

import argparse
import datetime

import numpy
import pandas


from marginals import calculate_marginals_batter
from utils import load_mapping, load_fangraphs_batter_projections, load_batter_positions, load_keepers, add_espn_auction_values, add_roster_state

from config import REMAINING_WEEKS, N_BATTERS, N_TEAMS, BATTER_BUDGET_RATIO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", action="store_true", help="prepare for auction draft")
    args = parser.parse_args()

    # calculate raw score
    batters = calculate_raw_score()

    batters = calculate_replacement_score(batters)

    # adjust score for positional scarcity
    batters['adj_score'] = batters['raw_score'] - batters['rep_score']

    batters = batters.sort_values('adj_score', ascending=False)

    batters = add_valuation(batters)

    if args.draft:
        # draft valuations include extra information
        # e.g. what the ESPN auction value is
        batters = add_inflation(batters)

        batters = add_espn_auction_values(batters)

        columns = [
            'name',
            'Team',
            'valuation_inflation',
            'espn_value',
            'valuation_flat',
            'keeper_salary',
        ]
    else:
        batters = add_roster_state(batters)

        columns = [
            'name',
            'Team',
            'valuation_flat',
            'fantasy_team_id',
        ]

    columns += [
        'position',
        'raw_per_score',
        # 'team_abbr',
        'PA',
        'HR',
        'SB',
        'R',
        'RBI',
        'AVG',
        'OBP',
        'SLG',
        'C',
        'B1',
        'B2',
        'B3',
        'SS',
        'OF',
        'MI',
        'CI',
        'raw_score',
        'rep_score',
        'mR_per',
        'R_per_score',
        'mRBI_per',
        'RBI_per_score',
        'SB_per_score',
        'HR_per_score',
    ]

    batters.sort_values('raw_per_score', ascending=False, inplace=True)

    batters.to_csv('batter_{:%Y%m%d}.csv'.format(datetime.datetime.today()), index=False, columns=columns, encoding='utf8')


def calculate_raw_score():
    """
    Calculate batter raw score from projected stats

    Use the marginal win probability over mean of each stat

    """
    mapping = load_mapping()

    projections = load_fangraphs_batter_projections()
    projections = projections.query('PA > 20').copy()

    positions = load_batter_positions()
    positions = correct_batter_positions(positions)  # account for any upcoming player position changes

    batters = projections.merge(mapping[['mlbam_id', 'playerid', 'espn_id']], how='left', on='playerid')
    batters = batters.merge(positions, how='left', on='espn_id')

    marginals, means = calculate_marginals_batter()

    contribution_ratio = 1.0 / N_BATTERS * REMAINING_WEEKS  # weekly score * number of weeks left in season / number of batters per team is each batter's expected contribution
    per_PA = 650 / 25 * REMAINING_WEEKS

    batters['mR'] = batters['R'] - (means['R'][0] * contribution_ratio)  # extra R over the mean batter for a season
    batters['mRBI'] = batters['RBI'] - (means['RBI'][0] * contribution_ratio)  # extra R over the mean batter
    batters['mSB'] = batters['SB'] - (means['SB'][0] * contribution_ratio)  # extra SB over the mean batter
    batters['mHR'] = batters['HR'] - (means['HR'][0] * contribution_ratio)  # extra HR over the mean batter
    batters['xOB'] = (batters['OBP'] * batters['PA']) - (means['OBP'][0] * batters['PA'])  # extra OB over the mean batter

    batters['mR_per'] = (batters['R'] / batters['PA']) * per_PA - (means['R'][0] * contribution_ratio)  # extra R over the mean batter on a per PA basis
    batters['mRBI_per'] = (batters['RBI'] / batters['PA']) * per_PA - (means['RBI'][0] * contribution_ratio)  # extra R over the mean batter on a per PA basis
    batters['mSB_per'] = (batters['SB'] / batters['PA']) * per_PA - (means['SB'][0] * contribution_ratio)  # extra SB over the mean batter
    batters['mHR_per'] = (batters['HR'] / batters['PA']) * per_PA - (means['HR'][0] * contribution_ratio)  # extra HR over the mean batter
    batters['xOB_per'] = (batters['OBP'] * per_PA) - (means['OBP'][0] * per_PA)  # extra OB over the mean batter

    # divide seasonal stats by the remaining weeks left in the season
    # the marginals are by week
    batters['R_score'] = batters['mR']  / REMAINING_WEEKS / marginals['R'][0]
    batters['RBI_score'] = batters['mRBI'] / REMAINING_WEEKS / marginals['RBI'][0]
    batters['SB_score'] = batters['mSB'] / REMAINING_WEEKS / marginals['SB'][0]
    batters['xOB_score'] = batters['xOB'] / REMAINING_WEEKS / marginals['xOB'][0]
    batters['HR_score'] = batters['mHR'] / REMAINING_WEEKS/ marginals['HR'][0]

    batters['R_per_score'] = batters['mR_per']  / REMAINING_WEEKS / marginals['R'][0]
    batters['RBI_per_score'] = batters['mRBI_per'] / REMAINING_WEEKS / marginals['RBI'][0]
    batters['SB_per_score'] = batters['mSB_per'] / REMAINING_WEEKS / marginals['SB'][0]
    batters['xOB_per_score'] = batters['xOB_per'] / REMAINING_WEEKS / marginals['xOB'][0]
    batters['HR_per_score'] = batters['mHR_per'] / REMAINING_WEEKS/ marginals['HR'][0]

    batters['raw_score'] = batters['R_score'] + batters['RBI_score'] + batters['xOB_score'] + batters['HR_score'] + batters['SB_score']

    batters['raw_per_score'] = batters['R_per_score'] + batters['RBI_per_score'] + batters['xOB_per_score'] + batters['HR_per_score'] + batters['SB_per_score']

    batters = batters.sort_values('raw_score', ascending=False)
    batters = batters.reset_index(drop=True)

    return batters


def correct_batter_positions(positions):
    """
    Manually correct batter positional eligibilities

    """
    positions.loc[positions['espn_id'] == '6203', 'SS'] = 1  # Trea Turner
    positions.loc[positions['espn_id'] == '6205', 'C'] = 0  # Kyle Schwarber
    positions.loc[positions['espn_id'] == '3123', 'B1'] = 1  # Eric Thames

    return positions


def calculate_replacement_score(batters):
    """
    Calculate the replacement level by position

    Assign positions in this order specified by `batter_positions`

    B1 appears very thin for 2017

    """
    batters = batters.sort_values('raw_score', ascending=False)

    batter_positions = [
        {'name': 'C', 'n': 2},
        {'name': 'B3', 'n': 1},
        {'name': 'SS', 'n': 1},
        {'name': 'B1', 'n': 1},
        {'name': 'B2', 'n': 1},
        {'name': 'OF', 'n': 5},
    ]

    batters['position'] = None
    for position in batter_positions:
        batters.loc[batters[
            batters['position'].isnull() &
            (batters[position['name']] == 1)
        ].index[0:(N_TEAMS * position['n'])], 'position'] = position['name']

    # set MI
    batters.loc[batters[batters['position'].isnull() & ((batters['B2'] == 1) | (batters['SS'] == 1))].index[0:12], 'position'] = 'MI'
    # set CI
    batters.loc[batters[batters['position'].isnull() & ((batters['B1'] == 1) | (batters['B3'] == 1))].index[0:12], 'position'] = 'CI'
    # set UTIL
    batters.loc[batters[batters['position'].isnull()].index[0:12], 'position'] = 'UTIL'

    # use the mean of the next two positionally eligible batters as the replacement level
    replacement_level = {}

    # UTIL applies to every batter
    replacement_level['UTIL'] = numpy.mean(batters.loc[batters[batters['position'].isnull()].index[0:2], 'raw_score'])
    batters['rep_score'] = replacement_level['UTIL']

    for position in batter_positions[::-1]:
        replacement_level[position['name']] = numpy.mean(batters.loc[batters[
            batters['position'].isnull() &
            (batters[position['name']] == 1)
        ].index[0:2], 'raw_score'])

        batters.loc[batters[position['name']] == 1, 'rep_score'] = replacement_level[position['name']]

    # set replacement level on MI and CI separately from 1B/3B and 2B/SS

    # batters.loc[batters['position'] == 'MI', 'rep_score'] = numpy.mean(batters.loc[batters[
    #     batters['position'].isnull() &
    #     ((batters['B2'] == 1) | (batters['SS'] == 1))
    # ].index[0:2], 'raw_score'])
    #
    # batters.loc[batters['position'] == 'CI', 'rep_score'] = numpy.mean(batters.loc[batters[
    #     batters['position'].isnull() &
    #     ((batters['B1'] == 1) | (batters['B3'] == 1))
    # ].index[0:2], 'raw_score'])

    for k, v in sorted(replacement_level.iteritems(), key=lambda (k, v): v):
        print k, v

    return batters


def add_valuation(batters):
    """
    Given the adjusted score, calculate the dollar value using a fixed batter / pitcher ratio

    """
    batter_budget = 260 * N_TEAMS * BATTER_BUDGET_RATIO

    dollars_per_adj_score_flat = batter_budget / numpy.sum(batters.iloc[0:(N_BATTERS * N_TEAMS)]['adj_score'])
    print u"total batter value: {}".format(numpy.sum(batters.iloc[0:(N_BATTERS * N_TEAMS)]['adj_score']))

    print u"$ per score (flat): {}".format(dollars_per_adj_score_flat)

    batters['valuation_flat'] = batters['adj_score'] * dollars_per_adj_score_flat

    return batters


def add_inflation(batters):
    """
    Adjust valuation to account for keepers causing inflation

    Keepers tend to have a lot of surplus value, which means the remaining pool of players will cost more for less value

    """
    keepers = load_keepers()

    batters = batters.merge(keepers, how='left', on='mlbam_id')

    batter_budget = 260 * N_TEAMS * BATTER_BUDGET_RATIO
    keepers_salaries = batters['keeper_salary'].sum()

    inflation_batter_budget = batter_budget - keepers_salaries
    print u"remaining batter budget: {}".format(inflation_batter_budget)

    free_agents = batters.iloc[0:(N_BATTERS * N_TEAMS)]
    free_agents = free_agents[free_agents['keeper_salary'].isnull()]

    dollars_per_adj_score_inflation = inflation_batter_budget / numpy.sum(free_agents['adj_score'])
    print u"$ per score with inflation: {}".format(dollars_per_adj_score_inflation)
    print u"remaining batter value: {}".format(numpy.sum(free_agents['adj_score']))

    batters['valuation_inflation'] = batters['adj_score'] * dollars_per_adj_score_inflation

    return batters


if __name__ == '__main__':
    main()
