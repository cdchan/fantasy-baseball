"""
Batter valuation

"""

import argparse
import datetime

import joblib
import numpy

from config import REMAINING_WEEKS, N_BATTERS, N_TEAMS, BATTER_BUDGET_RATIO, LEAGUE_DATA_DIRECTORY
from utils import load_mapping, load_fangraphs_batter_projections, load_espn_positions, load_keepers, add_espn_auction_values, add_roster_state, load_playing_time

team_PA_per_week = 300  # assume the team gets 300 PA a week

# number of batters needed for each position
batter_positions = [
    {'name': 'C', 'n': 2},
    {'name': '1B', 'n': 1},
    {'name': 'OF', 'n': 5},
    {'name': '2B', 'n': 1},
    {'name': 'SS', 'n': 1},
    {'name': '3B', 'n': 1},
]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", action="store_true", help="prepare for auction draft")
    parser.add_argument("--l14pt", action="store_true", help="use last 14 days of playing time")
    parser.add_argument("--projection", default="rfangraphsdc", help="projection system to use, choices are rfangraphs / steamer600u")
    args = parser.parse_args()

    if args.draft:
        projection_type = "thebatx"
    elif args.l14pt:
        projection_type = "steamer600u"
    else:
        projection_type = args.projection

    # calculate win probability added
    batters = calculate_p_added(projection_type, args.draft, args.l14pt)

    batters = calculate_replacement_score(batters)

    # adjust score for positional scarcity
    batters['adj_p_added_per_week'] = batters['p_added_per_week'] - batters['rep_p_added_per_week']

    batters = batters.sort_values('adj_p_added_per_week', ascending=False)

    batters = add_valuation(batters)

    columns = [
        'fg_name',
        'Team',
        'PA',
    ]

    if args.draft:
        # draft valuations include extra information
        # e.g. what the ESPN auction value is
        batters = add_inflation(batters)

        batters = add_espn_auction_values(batters)

        positions = ['C', 'SS', '2B', 'OF', '1B', '3B']

        batters['all_elig'] = ''
        for position in positions:
            batters['all_elig'] += numpy.where((batters[position] == 1) & (batters['position'] != position), position + ',', '')
        batters['all_elig'] = batters['all_elig'].str[:-1]

        print(batters.columns)

        columns += [
            'valuation_inflation',
            'espn_value',
            'keeper_salary',
            'all_elig',
            'fantasy_team_id',
        ]
    else:
        batters = add_roster_state(batters)

        columns += [
            'valuation_flat',
            'fantasy_team_id',
        ]

    columns += [
        'position',
        'adj_p_added_per_week',
        'p_added_per_week',
        'PA_per_week',
        'l14_G',
        # 'PR15', 'PR2018', 'pct_own',
        'R_p_added_per_week',
        'RBI_p_added_per_week',
        'HR_p_added_per_week',
        'SB_p_added_per_week',
        'TB_p_added_per_week',
        'OBP_p_added_per_week',
        'R_per_week',
        'RBI_per_week',
        'HR_per_week',
        'SB_per_week',
        'TB_per_week',
        'OB_per_week',
        'mOB_per_week',
        'PA',
        'HR',
        'SB',
        'TB',
        'R',
        'RBI',
        'AVG',
        'OBP',
        'SLG',
        'C',
        '1B',
        '2B',
        '3B',
        'SS',
        'OF',
        'MI',
        'CI',
    ]

    batters.sort_values('adj_p_added_per_week', ascending=False, inplace=True)

    output_columns =  [col for col in columns if col in batters.columns]

    batters.to_csv('{}/valuations/batter_{:%Y-%m-%d}.csv'.format(
        LEAGUE_DATA_DIRECTORY,
        datetime.datetime.today()
    ), index=False, columns=output_columns, encoding='utf8', float_format='%.2f')
    batters.to_csv('{}/batter_valuation.csv'.format(
        LEAGUE_DATA_DIRECTORY
    ), index=False, columns=output_columns, encoding='utf8', float_format='%.2f')


def calculate_p_added(projection_type, draft=False, l14pt=False):
    """
    Calculate probability added for batters from projected stats

    Use the marginal win probability over mean of each stat

    """
    mapping = load_mapping()

    projections = load_fangraphs_batter_projections(projection_type)
    projections = projections.query('PA > 20').copy()  # only consider batters projected for more than 20 PA
    projections = projections[projections['Team'].notnull()]  # remove batters with no team

    positions = load_espn_positions()
    positions = correct_batter_positions(positions)  # account for any upcoming player position changes

    batters = projections.merge(mapping[['mlb_id', 'fg_id', 'espn_id']], how='left', on='fg_id')
    batters = batters.merge(positions, how='left', on='espn_id')

    batter_categories_info = joblib.load('{}/batters.pickle'.format(
        LEAGUE_DATA_DIRECTORY
    ))  # load results of the logistic regression
    # TODO fix path to pickle

    if l14pt:
        batters = add_playing_time(batters)  # add in the latest playing time for batters
    else:
        batters['PA_per_week'] = batters['PA'] / REMAINING_WEEKS

    batters['OB'] = batters['OBP'] * batters['PA']
    batters['TB'] = batters['SLG'] * batters['AB']

    # calculate projected stats per week
    batters['R_per_week'] = batters['R'] / batters['PA'] * batters['PA_per_week']
    batters['RBI_per_week'] = batters['RBI'] / batters['PA'] * batters['PA_per_week']
    batters['HR_per_week'] = batters['HR'] / batters['PA'] * batters['PA_per_week']
    batters['SB_per_week'] = batters['SB'] / batters['PA'] * batters['PA_per_week']
    batters['TB_per_week'] = batters['TB'] / batters['PA'] * batters['PA_per_week']
    batters['OB_per_week'] = batters['OB'] / batters['PA'] * batters['PA_per_week']

    batter_categories_info['rep_level'] = {}
    manual_replacement_levels = {}  # replacement level defaults to 50% probability of winning, but can manually override here

    for cat, lm in batter_categories_info['models'].items():
        if cat in manual_replacement_levels:
            rep_level = (numpy.log(-manual_replacement_levels[cat] / (manual_replacement_levels[cat] - 1)) - lm.intercept_[0]) / lm.coef_[0][0]
        else:
            rep_level = (numpy.log(-0.5 / (0.5 - 1)) - lm.intercept_[0]) / lm.coef_[0][0]

        batter_categories_info['rep_level'][cat] = rep_level

    # no historical TB information yet
    batter_categories_info['rep_level']['TB'] = batter_categories_info['rep_level']['HR'] * 12.0

    batter_categories_info['rep_level']['OBP'] = batter_categories_info['rep_level']['OBP_big'] / 1000.0  # need to convert out of percentage points to avoid numerical issues

    print(batter_categories_info['rep_level'])
    batter_categories_info['p_added'] = {}

    for cat, _ in batter_categories_info['models'].items():
        print(cat)

        if cat == 'OBP_big':
            x_0 = batter_categories_info['rep_level'][cat]
            x_1 = (x_0  / 1000.0 * team_PA_per_week + 1) / team_PA_per_week * 1000.0
        else:
            x_0 = batter_categories_info['rep_level'][cat]
            x_1 = x_0 + 1

        # what is the 50% of winning for each category, and what is 1 additional of that unit?
        print(x_0, x_1)

        # using logistic regression, what is the win probability added for 1 additional unit of each category
        x = batter_categories_info['models'][cat].predict_proba(numpy.array([x_0, x_1]).reshape(-1, 1))[:, 1]
        batter_categories_info['p_added'][cat] = x[1] - x[0]

    batter_categories_info['p_added']['TB'] = batter_categories_info['p_added']['HR'] / 12.0

    # print out the win probability added
    print(batter_categories_info['p_added'])

    # calculate the marginal units per week over the "average" player
    batters['mR_per_week'] = batters['R_per_week'] - batter_categories_info['rep_level']['R'] / N_BATTERS
    batters['mRBI_per_week'] = batters['RBI_per_week'] - batter_categories_info['rep_level']['RBI'] / N_BATTERS
    batters['mHR_per_week'] = batters['HR_per_week'] - batter_categories_info['rep_level']['HR'] / N_BATTERS
    batters['mSB_per_week'] = batters['SB_per_week'] - batter_categories_info['rep_level']['SB'] / N_BATTERS
    batters['mTB_per_week'] = batters['TB_per_week'] - batter_categories_info['rep_level']['TB'] / N_BATTERS
    batters['mOB_per_week'] = batters['OB_per_week'] - (batter_categories_info['rep_level']['OBP'] * batters['PA_per_week'])

    # convert the marginal units per week to win probability
    probability_key = 'p_added'
    batters['R_p_added_per_week'] = batters['mR_per_week'] * batter_categories_info[probability_key]['R']
    batters['RBI_p_added_per_week'] = batters['mRBI_per_week'] * batter_categories_info[probability_key]['RBI']
    batters['HR_p_added_per_week'] = batters['mHR_per_week'] * batter_categories_info[probability_key]['HR']
    batters['SB_p_added_per_week'] = batters['mSB_per_week'] * batter_categories_info[probability_key]['SB']
    batters['TB_p_added_per_week'] = batters['mTB_per_week'] * batter_categories_info[probability_key]['TB']
    batters['OBP_p_added_per_week'] = batters['mOB_per_week'] *  batter_categories_info[probability_key]['OBP_big']

    # overall win probability added
    batters['p_added_per_week'] = batters['R_p_added_per_week'] + batters['RBI_p_added_per_week'] + batters['HR_p_added_per_week'] + batters['SB_p_added_per_week'] + batters['TB_p_added_per_week'] + batters['OBP_p_added_per_week']

    batters = batters.sort_values('p_added_per_week', ascending=False)
    batters = batters.reset_index(drop=True)

    return batters


def correct_batter_positions(positions):
    """
    Manually correct batter positional eligibilities

    """
    # example
    # positions.loc[positions['espn_id'] == '6203', 'SS'] = 1  # Trea Turner

    return positions


def add_playing_time(batters):
    """
    Add batters' PA from the past 14 days

    """
    playing_time = load_playing_time('batter')

    # how many games has the team had overall?
    playing_time['team_G'] = playing_time.groupby('Team')['G'].transform(lambda x: x.max())

    playing_time['l14_PA_per_week'] = 1.0 * playing_time['PA'] / playing_time['team_G'] * 6  # prorate PA so that each player gets 6 games in a week
    playing_time['l14_G'] = playing_time['G'] / playing_time['team_G']  # % of possible games played by batter

    # what is the overall average number of PA per week?
    avg_PA_per_week = 1.0 * playing_time['PA'].iloc[:12*14].sum() / playing_time['G'].iloc[:12*14].sum() * 6

    batters = batters.merge(playing_time[['fg_id', 'l14_PA_per_week', 'l14_G']], how='left', on='fg_id')

    batters['l14_PA_per_week'] = batters['l14_PA_per_week'].fillna(0)  # if the batter hasn't played in the past 14 days, set their PA to 0

    # if a batter is a full time player, regress their playing time projection to the mean
    batters['PA_per_week'] = numpy.where(
        batters['l14_G'] >= 0.75,  # assume a player is full time if he plays in 75+% of games
        (batters['l14_PA_per_week'] + avg_PA_per_week) / 2.0,  # regress the playing time projection to the mean
        batters['l14_PA_per_week']  # otherwise use the prorated PA
    )

    return batters


def calculate_replacement_score(batters):
    """
    Calculate the replacement level by position

    Assign positions in this order specified by `batter_positions`

    """
    batters = batters.sort_values('p_added_per_week', ascending=False)

    batters['position'] = None
    for position in batter_positions:
        batters.loc[batters[
            batters['position'].isnull() &
            (batters[position['name']] == 1)
        ].index[0:(N_TEAMS * position['n'])], 'position'] = position['name']

    # set MI
    batters.loc[batters[batters['position'].isnull() & (batters['MI'] == 1)].index[0:12], 'position'] = 'MI'
    # set CI
    batters.loc[batters[batters['position'].isnull() & (batters['CI'] == 1)].index[0:12], 'position'] = 'CI'
    # set UTIL
    batters.loc[batters[batters['position'].isnull()].index[0:12], 'position'] = 'UTIL'

    # use the mean of the next two positionally eligible batters as the replacement level
    replacement_level = {}

    # UTIL applies to every batter
    replacement_level['UTIL'] = numpy.mean(batters.loc[batters[batters['position'].isnull()].index[0:2], 'p_added_per_week'])
    batters['rep_p_added_per_week'] = replacement_level['UTIL']

    for position in batter_positions[::-1]:
        replacement_level[position['name']] = numpy.mean(batters.loc[batters[
            batters['position'].isnull() &
            (batters[position['name']] == 1)
        ].index[0:2], 'p_added_per_week'])

        batters.loc[batters[position['name']] == 1, 'rep_p_added_per_week'] = replacement_level[position['name']]

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

    # print replacement level win probability for each position
    for position, rep_level in [(k, replacement_level[k]) for k in sorted(replacement_level, key=replacement_level.get)]:
        print(position, rep_level)

    return batters


def add_valuation(batters):
    """
    Given the adjusted win probability added, calculate the dollar value using a fixed batter / pitcher ratio

    """
    batter_budget = 260 * N_TEAMS * BATTER_BUDGET_RATIO

    dollars_per_adj_p_added_flat = batter_budget / numpy.sum(batters.iloc[0:(N_BATTERS * N_TEAMS)]['adj_p_added_per_week'])
    print(u"total batter value: {}".format(numpy.sum(batters.iloc[0:(N_BATTERS * N_TEAMS)]['adj_p_added_per_week'])))

    print(u"$ per 10% win probability added (flat): {}".format(dollars_per_adj_p_added_flat / 10.0))

    batters['valuation_flat'] = batters['adj_p_added_per_week'] * dollars_per_adj_p_added_flat

    return batters


def add_inflation(batters):
    """
    Adjust valuation to account for keepers causing inflation

    Keepers tend to have a lot of surplus value, which means the remaining pool of players will cost more for less value

    """
    keepers = load_keepers()
    # last_year_auction = load_previous_prices()

    batters = batters.merge(keepers, how='left', on='mlb_id')
    # batters = batters.merge(last_year_auction, how='left', on='espn_id')

    batter_budget = 260 * N_TEAMS * BATTER_BUDGET_RATIO
    keepers_salaries = batters['keeper_salary'].sum()

    inflation_batter_budget = batter_budget - keepers_salaries
    print(u"remaining batter budget: {}".format(inflation_batter_budget))

    free_agents = batters.iloc[0:(N_BATTERS * N_TEAMS)]
    free_agents = free_agents[free_agents['keeper_salary'].isnull()]

    dollars_per_adj_score_inflation = inflation_batter_budget / numpy.sum(free_agents['adj_p_added_per_week'])
    print(u"$ per score with inflation: {}".format(dollars_per_adj_score_inflation))
    print(u"remaining batter value: {}".format(numpy.sum(free_agents['adj_p_added_per_week'])))

    batters['valuation_inflation'] = batters['adj_p_added_per_week'] * dollars_per_adj_score_inflation

    return batters


if __name__ == '__main__':
    main()
