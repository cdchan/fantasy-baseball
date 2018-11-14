"""
Pitcher valuation

"""

import argparse
import datetime

import numpy
import pandas

from sklearn.externals import joblib


from utils import load_mapping, load_fangraphs_pitcher_projections, load_pitcher_positions, load_keepers, add_espn_auction_values, add_roster_state

from config import REMAINING_WEEKS, N_PITCHERS, N_TEAMS, BATTER_BUDGET_RATIO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", action="store_true", help="prepare for auction draft")
    args = parser.parse_args()

    # calculate win probability added
    pitchers = calculate_p_added()

    pitchers = calculate_replacement_score(pitchers)

    # adjust win probability for positional scarcity
    pitchers['adj_p_added_per_week'] = pitchers['p_added_per_week'] - pitchers['rep_p_added_per_week']

    pitchers = pitchers.sort_values('adj_p_added_per_week', ascending=False)

    pitchers = add_valuation(pitchers)

    if args.draft:
        pitchers = add_inflation(pitchers)

        pitchers = add_espn_auction_values(pitchers)

        columns = [
            'name',
            'Team',
            'valuation_inflation',
            'espn_value',
            'valuation_flat',
            'keeper_salary',
        ]
    else:
        pitchers = add_roster_state(pitchers)

        columns = [
            'name',
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

    remaining_columns = [c for c in pitchers.columns if c not in columns]

    columns += remaining_columns

    pitchers = pitchers.sort_values('p_added_per_week', ascending=False)

    pitchers.to_csv('pitcher_{:%Y%m%d}.csv'.format(datetime.datetime.today()), index=False, columns=columns)


def calculate_p_added():
    """
    Calculate probability added for pitchers from projected stats

    Use the marginal win probability over mean of each stat

    """
    mapping = load_mapping()

    projections = load_fangraphs_pitcher_projections('steamer600u')
    projections = projections.query('IP > 1').copy()  # only consider pitchers projected for more than 1 IP
    projections = projections[projections['Team'].notnull()]  # remove pitchers with no team

    positions = load_pitcher_positions()
    # positions = correct_pitcher_positions(positions)

    pitchers = projections.merge(mapping[['mlbam_id', 'playerid', 'espn_id']], how='left', on='playerid')
    pitchers = pitchers.merge(positions, how='left', on='espn_id')

    pitchers = add_playing_time(pitchers)  # add in the latest playing time for pitchers

    pitcher_categories_info = joblib.load('pitchers.pkl')  # load results of the logistic regression

    base_team_probabilities = {
        'SV': 0.5,
        'ERA': 0.5,
        'WHIP': 0.5,
        'K9': 0.5,
        'W': 0.5,
        'IP': 0.5,
    }

    pitcher_categories_info['base_level'] = {}

    for cat, lm in pitcher_categories_info['models'].iteritems():
        base_level = (numpy.log(-base_team_probabilities[cat] / (base_team_probabilities[cat] - 1)) - lm.intercept_[0]) / lm.coef_[0][0]

        pitcher_categories_info['base_level'][cat] = base_level

    pitcher_categories_info['p_added_new'] = {}

    team_IP_per_week = 21

    for cat, _ in pitcher_categories_info['models'].iteritems():
        print cat

        x_0 = pitcher_categories_info['base_level'][cat]

        if cat in ['ERA', 'K9']:
            x_1 = (x_0 / 9 * team_IP_per_week + 1) / team_IP_per_week * 9
        elif cat in ['WHIP']:
            x_1 = (x_0 * team_IP_per_week + 1) / team_IP_per_week
        else:
            x_1 = x_0 + 1

        print x_0, x_1

        x = pitcher_categories_info['models'][cat].predict_proba(numpy.array([x_0, x_1]).reshape(-1, 1))[:, 1]
        pitcher_categories_info['p_added'][cat] = x[1] - x[0]

    print pitcher_categories_info['p_added']

    pitchers['W_per_week'] = pitchers['W'] / pitchers['weeks']
    pitchers['SV_per_week'] = pitchers['SV'] / pitchers['weeks']
    pitchers['ER_per_week'] = pitchers['ERA'] / 9 * pitchers['IP_per_week']
    pitchers['WH_per_week'] = pitchers['WHIP'] * pitchers['IP_per_week']
    pitchers['K_per_week'] = pitchers['K9'] / 9 * pitchers['IP_per_week']

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

    pitchers['p_added_per_week'] = pitchers['IP_p_added_per_week'] + pitchers['W_p_added_per_week'] + pitchers['SV_p_added_per_week'] + pitchers['ER_p_added_per_week'] + pitchers['WH_p_added_per_week'] + pitchers['K_p_added_per_week']
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

    replacement_level['P'] = numpy.mean(pitchers.ix[rostered:(rostered + 2)]['p_added_per_week'])

    pitchers['rep_p_added_per_week'] = replacement_level['P']

    return pitchers


def add_valuation(pitchers):
    """
    Given the adjusted win probability, calculate the dollar value using a fixed batter / pitcher ratio

    """
    pitcher_budget = 260 * N_TEAMS * (1 - BATTER_BUDGET_RATIO)

    dollars_per_adj_p_added_flat = pitcher_budget / numpy.sum(pitchers.iloc[0:(N_PITCHERS * N_TEAMS)]['adj_p_added_per_week'])
    print u"total pitcher value: {}".format(numpy.sum(pitchers.iloc[0:(N_PITCHERS * N_TEAMS)]['adj_p_added_per_week']))

    print u"$ per win probability (flat): {}".format(dollars_per_adj_p_added_flat)

    pitchers['valuation_flat'] = pitchers['adj_p_added_per_week'] * dollars_per_adj_p_added_flat

    return pitchers


def add_inflation(pitchers):
    """
    Adjust valuation to account for keepers causing inflation

    Keepers tend to have a lot of surplus value, which means the remaining pool of players will cost more for less value

    """
    keepers = load_keepers()

    pitchers = pitchers.merge(keepers, how='left', on='mlbam_id')

    pitcher_budget = 260 * N_TEAMS * (1 - BATTER_BUDGET_RATIO)
    keepers_salaries = pitchers['keeper_salary'].sum()

    inflation_pitcher_budget = pitcher_budget - keepers_salaries
    print u"remaining pitcher budget: {}".format(inflation_pitcher_budget)

    free_agents = pitchers.iloc[0:(N_PITCHERS * N_TEAMS)]
    free_agents = free_agents[free_agents['keeper_salary'].isnull()]

    dollars_per_adj_p_added_inflation = inflation_pitcher_budget / numpy.sum(free_agents['adj_p_added_per_week'])
    print u"$ per win probability with inflation: {}".format(dollars_per_adj_p_added_inflation)
    print u"remaining batter value: {}".format(numpy.sum(free_agents['adj_p_added_per_week']))

    pitchers['valuation_inflation'] = pitchers['adj_p_added_per_week'] * dollars_per_adj_p_added_inflation

    return pitchers


if __name__ == '__main__':
    main()
