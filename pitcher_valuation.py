"""
Pitcher valuation

"""

import argparse
import datetime

import numpy
import pandas


from marginals import calculate_marginals_pitcher
from utils import load_mapping, load_fangraphs_pitcher_projections, load_pitcher_positions, load_keepers, add_espn_auction_values, add_roster_state

from config import REMAINING_WEEKS, N_PITCHERS, N_TEAMS, BATTER_BUDGET_RATIO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", action="store_true", help="prepare for auction draft")
    args = parser.parse_args()

    # calculate raw score
    pitchers = calculate_raw_score()

    pitchers = calculate_replacement_score(pitchers)

    pitchers['adj_score'] = pitchers['raw_score'] - pitchers['rep_score']

    pitchers = pitchers.sort_values('adj_score', ascending=False)

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
        # 'position',
        'adj_score',
        'ratios_score',
        # 'team_abbr',
        'IP',
        'G',
        'GS',
        'W',
        'SV',
        'ERA',
        'WHIP',
        'K9',
        'SP',
        'RP',
        'raw_score',
        'rep_score',
        'xER_score_per_week',
        'xWH_score_per_week',
        'xK_score_per_week',
        'IP_per_week',
        'weeks',
    ]

    remaining_columns = [c for c in pitchers.columns if c not in columns]

    columns += remaining_columns

    pitchers = pitchers.sort_values('ratios_score', ascending=False)

    pitchers.to_csv('pitcher_{:%Y%m%d}.csv'.format(datetime.datetime.today()), index=False, columns=columns)


def calculate_raw_score():
    """
    Calculate pitcher raw score from projected stats

    Use the marginal win probability over mean of each stat

    """
    mapping = load_mapping()

    projections = load_fangraphs_pitcher_projections()
    projections = projections.query('IP > 1').copy()
    projections = projections[projections['Team'].notnull()]

    positions = load_pitcher_positions()
    # positions = correct_pitcher_positions(positions)

    pitchers = projections.merge(mapping[['mlbam_id', 'playerid', 'espn_id']], how='left', on='playerid')
    pitchers = pitchers.merge(positions, how='left', on='espn_id')

    marginals, means = calculate_marginals_pitcher()

    contribution_ratio = 1.0 / N_PITCHERS * REMAINING_WEEKS  # weekly score * number of weeks left in season / number of pitchers per team is each pitchers's expected contribution for the rest of the season

    pitchers['as_SP'] = (pitchers['GS'] > 1)

    pitchers['mW'] = pitchers['W'] - (means['W'][0] * contribution_ratio)  # extra W over the mean pitcher
    pitchers['mIP'] = pitchers['IP'] - (means['IP'][0] * contribution_ratio)  # extra W over the mean pitcher
    pitchers['mSV'] = pitchers['SV'] - (means['SV'][0] * contribution_ratio)  # extra W over the mean pitcher

    pitchers['IP_per_GS'] = (pitchers['IP'] - pitchers['G'] + pitchers['GS']) / pitchers['GS']
    pitchers['IP_per_week'] = 65.0 / 25  # default for relievers is 65 IP per season, 25 weeks

    # use a SP's workload if not a RP
    # default is 32 starts per season, 25 weeks, so multiply IP per GS by 32 / 25 for IP per week
    pitchers['IP_per_week'] = pitchers['IP_per_week'].where(~pitchers['as_SP'], pitchers['IP_per_GS'] * 32.0 / 25)
    pitchers['weeks'] = numpy.where(~pitchers['as_SP'], pitchers['IP'] / (65.0 / 25), pitchers['GS'] / (32.0 / 25))

    # we don't use contribution ratio or REMAINING_WEEKS here because that is already built in into the pitcher's projected IP
    pitchers['xER_per_week'] = (pitchers['ERA'] - means['ERA'][0]) / 9 * pitchers['IP_per_week']  # use ERA over ER for more accuracy when IP is small
    pitchers['xWH_per_week'] = (pitchers['WHIP'] - means['WHIP'][0]) * pitchers['IP_per_week']  # use WHIP over BB and H for more accuracy when IP is small
    pitchers['xK_per_week'] = (pitchers['K9'] - means['K9'][0]) / 9 * pitchers['IP_per_week']

    pitchers['xER'] = pitchers['xER_per_week'] * pitchers['weeks']
    pitchers['xWH'] = pitchers['xWH_per_week'] * pitchers['weeks']
    pitchers['xK'] = pitchers['xK_per_week'] * pitchers['weeks']

    # divide seasonal stats by the remaining weeks left in the season
    # the marginals are by week
    pitchers['IP_score'] = pitchers['mIP'] / REMAINING_WEEKS / marginals['IP'][0]
    pitchers['W_score'] = pitchers['mW'] / REMAINING_WEEKS / marginals['W'][0]
    pitchers['SV_score'] = pitchers['mSV'] / REMAINING_WEEKS / marginals['SV'][0]
    pitchers['xER_score'] = - pitchers['xER'] / REMAINING_WEEKS / marginals['xER'][0]  # fewer ER is good
    pitchers['xWH_score'] = - pitchers['xWH'] / REMAINING_WEEKS / marginals['xWH'][0]  # few WH is good
    pitchers['xK_score'] = pitchers['xK'] / REMAINING_WEEKS / marginals['xK'][0]

    pitchers['xER_score_per_week'] = - pitchers['xER_per_week'] / marginals['xER'][0]  # fewer ER is good
    pitchers['xWH_score_per_week'] = - pitchers['xWH_per_week'] / marginals['xWH'][0]  # few WH is good
    pitchers['xK_score_per_week'] = pitchers['xK_per_week'] / marginals['xK'][0]

    pitchers['raw_score'] = pitchers['IP_score'] + pitchers['W_score'] + pitchers['SV_score'] + pitchers['xER_score'] + pitchers['xWH_score'] + pitchers['xK_score']
    pitchers['ratios_score'] = pitchers['xER_score_per_week'] + pitchers['xWH_score_per_week'] + pitchers['xK_score_per_week']

    pitchers = pitchers.sort_values('raw_score', ascending=False)
    pitchers = pitchers.reset_index(drop=True)

    return pitchers


def calculate_replacement_score(pitchers):
    """
    Calculate the replacement level by position

    Should RP count separately from SP?

    """
    replacement_level = {}
    rostered = N_PITCHERS * N_TEAMS

    replacement_level['P'] = numpy.mean(pitchers.ix[rostered:(rostered + 2)]['raw_score'])

    pitchers['rep_score'] = replacement_level['P']

    return pitchers


def add_valuation(pitchers):
    """
    Given the adjusted score, calculate the dollar value using a fixed batter / pitcher ratio

    """
    pitcher_budget = 260 * N_TEAMS * (1 - BATTER_BUDGET_RATIO)

    dollars_per_adj_score_flat = pitcher_budget / numpy.sum(pitchers.iloc[0:(N_PITCHERS * N_TEAMS)]['adj_score'])
    print u"total pitcher value: {}".format(numpy.sum(pitchers.iloc[0:(N_PITCHERS * N_TEAMS)]['adj_score']))

    print u"$ per score (flat): {}".format(dollars_per_adj_score_flat)

    pitchers['valuation_flat'] = pitchers['adj_score'] * dollars_per_adj_score_flat

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
    print u"remaining batter budget: {}".format(inflation_pitcher_budget)

    free_agents = pitchers.iloc[0:(N_PITCHERS * N_TEAMS)]
    free_agents = free_agents[free_agents['keeper_salary'].isnull()]

    dollars_per_adj_score_inflation = inflation_pitcher_budget / numpy.sum(free_agents['adj_score'])
    print u"$ per score with inflation: {}".format(dollars_per_adj_score_inflation)
    print u"remaining batter value: {}".format(numpy.sum(free_agents['adj_score']))

    pitchers['valuation_inflation'] = pitchers['adj_score'] * dollars_per_adj_score_inflation

    return pitchers


if __name__ == '__main__':
    main()
