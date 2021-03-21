"""
Pitcher valuation

"""

import argparse
import datetime

import joblib
import numpy
import pandas

from config import REMAINING_WEEKS, N_PITCHERS, N_TEAMS, BATTER_BUDGET_RATIO, LEAGUE_DATA_DIRECTORY
from utils import load_mapping, load_fangraphs_pitcher_projections, load_espn_positions, load_keepers, add_espn_auction_values, add_roster_state


MIN_IP = 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", action="store_true", help="prepare for auction draft")
    parser.add_argument("-l14pt", action="store_true", help="use last 14 days of playing time")
    parser.add_argument("--projection", default="rfangraphsdc", help="projection system to use, choices are rfangraphs / steamer600u")
    args = parser.parse_args()

    if args.draft:
        projection_type = "fangraphsdc"
    else:
        projection_type = args.projection

    # calculate win probability added
    pitchers = calculate_p_added(projection_type, args.draft, args.l14pt)

    pitchers = calculate_replacement_score(pitchers)

    # adjust win probability for positional scarcity
    pitchers['adj_p_added_per_week'] = pitchers['p_added_per_week'] - pitchers['rep_p_added_per_week']

    pitchers = pitchers.sort_values('adj_p_added_per_week', ascending=False)

    pitchers = add_valuation(pitchers)

    if args.draft:
        pitchers = add_inflation(pitchers)

        pitchers = add_espn_auction_values(pitchers)

        del pitchers['fantasy_team_id']
        pitchers = add_roster_state(pitchers)
        print(pitchers.columns)

        columns = [
            'fg_name',
            'Team',
            'valuation_inflation',
            'espn_value',
            'keeper_salary',
            'fantasy_team_id',
        ]
    else:
        pitchers = add_roster_state(pitchers)

        columns = [
            'fg_name',
            'Team',
            'valuation_flat',
            'fantasy_team_id',
        ]

    columns += [
        'p_added_per_week',
        'ratios_p_added_per_week',
        'IP_per_week',
        'l14_IP_per_week',
        'GS',
        'G',
        'IP',
        'relief_IP',
        'W',
        'SV',
        'ERA',
        'WHIP',
        'K9',
        'IP_p_added_per_week',
        'W_p_added_per_week',
        'SV_p_added_per_week',
        'ER_p_added_per_week',
        'WH_p_added_per_week',
        'K_p_added_per_week',
        'weeks',
        'mW_per_week',
        ]

    pitchers = pitchers.sort_values('p_added_per_week', ascending=False)

    output_columns =  [col for col in columns if col in pitchers.columns]

    pitchers.to_csv('{}/valuations/pitcher_{:%Y-%m-%d}.csv'.format(
        LEAGUE_DATA_DIRECTORY,
        datetime.datetime.today()
    ), index=False, columns=output_columns, encoding='utf8', float_format='%.2f')
    pitchers.to_csv('{}/pitcher_valuation.csv'.format(
        LEAGUE_DATA_DIRECTORY
    ), index=False, columns=output_columns, encoding='utf8', float_format='%.2f')


def adjust_saves(projections):
    """
    Manually adjust saves projections
    """
    return projections
    

def calculate_p_added(projection_type, draft=False, l14pt=False):
    """
    Calculate probability added for pitchers from projected stats

    Use the marginal win probability over mean of each stat

    """
    mapping = load_mapping()

    projections = load_fangraphs_pitcher_projections(projection_type)
    projections = projections[projections['IP'] > MIN_IP].copy()  # only consider pitchers projected for more than MIN_IP IP
    # projections = projections[projections['Team'].notnull()]  # remove pitchers with no team

    positions = load_espn_positions()
    # positions = correct_pitcher_positions(positions)

    projections = adjust_saves(projections)

    pitchers = projections.merge(mapping[['mlb_id', 'fg_id', 'espn_id']], how='left', on='fg_id')
    pitchers = pitchers.merge(positions, how='left', on='espn_id')

    if l14pt:
        pitchers = add_playing_time(pitchers)  # add in the latest playing time for pitchers
    else:
        pitchers['IP_per_week'] = pitchers['IP'] / REMAINING_WEEKS
        pitchers['weeks'] = REMAINING_WEEKS

    pitcher_categories_info = joblib.load('{}/pitchers.pickle'.format(LEAGUE_DATA_DIRECTORY))  # load results of the logistic regression

    base_team_probabilities = {
        'SV': 0.5,
        'ERA': 0.5,
        'WHIP': 0.5,
        'K9': 0.5,
        'W': 0.5,
        'IP': 0.5,
    }

    # calculate what team stats are needed to have a 50% chance of winning the category (or whatever % is set in base_team_probabilities)
    pitcher_categories_info['base_level'] = {}

    for cat, lm in pitcher_categories_info['models'].items():
        base_level = (numpy.log(-base_team_probabilities[cat] / (base_team_probabilities[cat] - 1)) - lm.intercept_[0]) / lm.coef_[0][0]

        pitcher_categories_info['base_level'][cat] = base_level

    pitcher_categories_info['p_added_new'] = {}

    team_IP_per_week = pitcher_categories_info['base_level']['IP']  # adjust if team strategy is different

    # calculate how much win probability is added for an additional unit for each category
    for cat, _ in pitcher_categories_info['models'].items():
        print(cat)

        x_0 = pitcher_categories_info['base_level'][cat]

        if cat in ['ERA', 'K9']:
            x_1 = (x_0 / 9 * team_IP_per_week + 1) / team_IP_per_week * 9
        elif cat in ['WHIP']:
            x_1 = (x_0 * team_IP_per_week + 1) / team_IP_per_week
        else:
            x_1 = x_0 + 1

        print(x_0, x_1)

        x = pitcher_categories_info['models'][cat].predict_proba(numpy.array([x_0, x_1]).reshape(-1, 1))[:, 1]
        pitcher_categories_info['p_added'][cat] = x[1] - x[0]

    print(pitcher_categories_info['p_added'])

    # normalize pitcher production to a weekly basis
    pitchers['W_per_week'] = pitchers['W'] / pitchers['weeks']
    pitchers['SV_per_week'] = pitchers['SV'] / pitchers['weeks']
    pitchers['ER_per_week'] = pitchers['ERA'] / 9 * pitchers['IP_per_week']
    pitchers['WH_per_week'] = pitchers['WHIP'] * pitchers['IP_per_week']
    pitchers['K_per_week'] = pitchers['K9'] / 9 * pitchers['IP_per_week']

    # calculate the marginal pitcher production over the base level
    pitchers['mIP_per_week'] = pitchers['IP_per_week'] - (pitcher_categories_info['base_level']['IP'] / N_PITCHERS)
    pitchers['mW_per_week'] = pitchers['W_per_week'] - (pitcher_categories_info['base_level']['W'] / N_PITCHERS)
    pitchers['mSV_per_week'] = pitchers['SV_per_week'] - (pitcher_categories_info['base_level']['SV'] / N_PITCHERS)

    pitchers['mER_per_week'] = (pitchers['ERA'] - pitcher_categories_info['base_level']['ERA']) / 9 * pitchers['IP_per_week']  # use ERA over ER for more accuracy when IP is small
    pitchers['mWH_per_week'] = (pitchers['WHIP'] - pitcher_categories_info['base_level']['WHIP']) * pitchers['IP_per_week']  # use WHIP over BB and H for more accuracy when IP is small
    pitchers['mK_per_week'] = (pitchers['K9'] - pitcher_categories_info['base_level']['K9']) / 9 * pitchers['IP_per_week']

    probability_key = 'p_added'

    pitchers['IP_p_added_per_week'] = pitchers['mIP_per_week'] * pitcher_categories_info[probability_key]['IP']
    pitchers['W_p_added_per_week'] = pitchers['mW_per_week'] * pitcher_categories_info[probability_key]['W']
    pitchers['SV_p_added_per_week'] = pitchers['mSV_per_week'] * pitcher_categories_info[probability_key]['SV']
    pitchers['ER_p_added_per_week'] = -1.0 * pitchers['mER_per_week'] * pitcher_categories_info[probability_key]['ERA']
    pitchers['WH_p_added_per_week'] = -1.0 * pitchers['mWH_per_week'] * pitcher_categories_info[probability_key]['WHIP']
    pitchers['K_p_added_per_week'] = pitchers['mK_per_week'] * pitcher_categories_info[probability_key]['K9']

    # cumulative win probability added across all categories
    pitchers['p_added_per_week'] = pitchers['IP_p_added_per_week'] + pitchers['W_p_added_per_week'] + pitchers['SV_p_added_per_week'] + pitchers['ER_p_added_per_week'] + pitchers['WH_p_added_per_week'] + pitchers['K_p_added_per_week']
    # win probability added for only the ratio categories
    pitchers['ratios_p_added_per_week'] = pitchers['ER_p_added_per_week'] + pitchers['WH_p_added_per_week'] + pitchers['K_p_added_per_week']

    pitchers = pitchers.sort_values('p_added_per_week', ascending=False)
    pitchers = pitchers.reset_index(drop=True)

    return pitchers


def add_playing_time(pitchers):
    """
    Add pitchers' IP from the past 14 days

    """
    # start by calculating the number of games the team has played from the batter playing time data
    batter_playing_time = pandas.read_csv('batter_playing_time.csv', encoding="utf-8-sig", error_bad_lines=False, dtype={'playerid': object})

    batter_playing_time.rename(columns={'"Name"': "name", 'Name': "name", '2B': "D", '3B': "T"}, inplace=True)  # columns can't begin with numbers

    team_games = batter_playing_time.groupby('Team', as_index=False).aggregate({'G': 'max'})
    team_games.rename(columns={'G': 'team_G'}, inplace=True)

    # load pitcher playing time
    playing_time = pandas.read_csv('pitcher_playing_time.csv', encoding="utf-8-sig", error_bad_lines=False, dtype={'playerid': object})

    playing_time.rename(columns={'"Name"': "name", 'Name': "name", 'K/9': "K9", 'SO': "K"}, inplace=True)

    playing_time = playing_time.merge(team_games, on='Team')

    # any pitcher that started a game counts as a SP
    playing_time['SP'] = playing_time['GS'] > 0

    # if SP, IP per week is based on IP per start, assuming 1 start a week
    # if RP, IP per week is based on IP per team game, assuming 6 games a week
    playing_time['l14_IP_per_week'] = (playing_time['IP'] / playing_time['GS']).where(playing_time['SP'], playing_time['IP'] / playing_time['team_G'] * 6)

    pitchers = pitchers.merge(playing_time[['playerid', 'l14_IP_per_week']], how='left', on='playerid')
    pitchers['l14_IP_per_week'] = pitchers['l14_IP_per_week'].fillna(0)

    pitchers['is_RP'] = (pitchers['GS'] < 1)

    pitchers['relief_IP'] = pitchers['G'] - pitchers['GS']  # assume relief appearances are for 1 IP

    pitchers['IP_per_GS'] = (pitchers['IP'] - pitchers['relief_IP']) / pitchers['GS']

    # default for relievers is 65 IP per season, 25 weeks
    default_relief_workload = 65.0 / 25

    # default for starters is 32 GS per season, 25 weeks
    default_start_workload = 32.0 / 25

    # number of weeks a pitcher is projected to pitch
    pitchers['weeks'] = pitchers['relief_IP'] / default_relief_workload + pitchers['GS'] / default_start_workload

    pitchers['IP_per_week'] = pitchers['l14_IP_per_week']

    return pitchers


def calculate_replacement_score(pitchers):
    """
    Calculate the replacement level by position

    Should RP count separately from SP?

    """
    replacement_level = {}
    rostered = N_PITCHERS * N_TEAMS

    replacement_level['P'] = numpy.mean(pitchers.iloc[rostered:(rostered + 2)]['p_added_per_week'])

    pitchers['rep_p_added_per_week'] = replacement_level['P']

    return pitchers


def add_valuation(pitchers):
    """
    Given the adjusted win probability, calculate the dollar value using a fixed batter / pitcher ratio

    """
    pitcher_budget = 260 * N_TEAMS * (1 - BATTER_BUDGET_RATIO)

    dollars_per_adj_p_added_flat = pitcher_budget / numpy.sum(pitchers.iloc[0:(N_PITCHERS * N_TEAMS)]['adj_p_added_per_week'])
    print(u"total pitcher value: {}".format(numpy.sum(pitchers.iloc[0:(N_PITCHERS * N_TEAMS)]['adj_p_added_per_week'])))

    print(u"$ per win probability (flat): {}".format(dollars_per_adj_p_added_flat))

    pitchers['valuation_flat'] = pitchers['adj_p_added_per_week'] * dollars_per_adj_p_added_flat

    return pitchers


def add_inflation(pitchers):
    """
    Adjust valuation to account for keepers causing inflation

    Keepers tend to have a lot of surplus value, which means the remaining pool of players will cost more for less value

    """
    keepers = load_keepers()

    pitchers = pitchers.merge(keepers, how='left', on='mlb_id')

    pitcher_budget = 260 * N_TEAMS * (1 - BATTER_BUDGET_RATIO)
    keepers_salaries = pitchers['keeper_salary'].sum()

    inflation_pitcher_budget = pitcher_budget - keepers_salaries
    print(u"remaining pitcher budget: {}".format(inflation_pitcher_budget))

    free_agents = pitchers.iloc[0:(N_PITCHERS * N_TEAMS)]
    free_agents = free_agents[free_agents['keeper_salary'].isnull()]

    dollars_per_adj_p_added_inflation = inflation_pitcher_budget / numpy.sum(free_agents['adj_p_added_per_week'])
    print(u"$ per win probability with inflation: {}".format(dollars_per_adj_p_added_inflation))
    print(u"remaining pitcher value: {}".format(numpy.sum(free_agents['adj_p_added_per_week'])))

    pitchers['valuation_inflation'] = pitchers['adj_p_added_per_week'] * dollars_per_adj_p_added_inflation

    return pitchers


if __name__ == '__main__':
    main()
