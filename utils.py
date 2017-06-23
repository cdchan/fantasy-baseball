"""
Utility functions

"""

import os

import numpy
import pandas


from config import WORKING_DIRECTORY


def load_mapping():
    """
    Load player id mappings

    """
    mapping = pandas.read_csv(os.path.join(WORKING_DIRECTORY, 'player_mapping.csv'), dtype={'mlbam_id': object, 'bis_id': object, 'espn_id': object})

    mapping['playerid'] = mapping['bis_id'].combine_first(mapping['stats_id'])  # use BIS id if available, otherwise STATS id

    print u"location of player mapping file: {}".format(os.path.join(WORKING_DIRECTORY, 'player_mapping.csv'))

    return mapping


def load_fangraphs_pitcher_projections():
    """
    Load Fangraphs Depth Charts pitcher projections

    """
    projections = pandas.read_csv(os.path.join(WORKING_DIRECTORY, 'depthcharts_pitchers.csv'), encoding="utf-8-sig")

    projections.rename(columns={'"Name"': "name", 'Name': "name", 'K/9': "K9", 'SO': "K"}, inplace=True)

    projections = convert_fangraphs_playerid(projections)

    return projections


def load_fangraphs_batter_projections():
    """
    Load Fangraphs Depth Charts batter projections

    """
    projections = pandas.read_csv(os.path.join(WORKING_DIRECTORY, 'depthcharts_batters.csv'), encoding="utf-8-sig", error_bad_lines=False)

    projections.rename(columns={'"Name"': "name", 'Name': "name", '2B': "D", '3B': "T"}, inplace=True)  # columns can't begin with numbers

    projections = convert_fangraphs_playerid(projections)

    return projections


def convert_fangraphs_playerid(projections):
    """
    Convert Fangraphs playerid to BIS id and STATS id

    """
    # BIS ids are numbers, if a playerid is not a number, set to NaN
    projections['bis_id'] = numpy.where(projections['playerid'].str.isnumeric(), projections['playerid'], numpy.nan)

    # if playerid is not a number, it's a STATS id
    projections['stats_id'] = numpy.where(~projections['playerid'].str.isnumeric(), projections['playerid'], numpy.nan)  # use None because this is an object array

    return projections


def load_pitcher_positions(old=False):
    """
    Load pitcher teams and positional eligibilities from ESPN

    """
    positions = pandas.read_csv(os.path.join(WORKING_DIRECTORY, 'pitcher_eligibilities.csv'), na_values='NA', dtype={'espn_id': object})

    rename_columns = {
        'name': 'name_espn',
    }

    if old:
        rename_columns['team_id'] = 'previous_team_id'

    positions.rename(columns=rename_columns, inplace=True)

    positions['P'] = 1

    return positions


def load_batter_positions(old=False):
    """
    Load batter teams and positional eligibilities from ESPN

    """
    positions = pandas.read_csv(os.path.join(WORKING_DIRECTORY, 'batter_eligibilities.csv'), na_values='NA', dtype={'espn_id': object})

    # manual_correction_batter_eligibility(positions)

    rename_columns = {
        'name': 'name_espn',
        '1B': 'B1',
        '2B': 'B2',
        '3B': 'B3'
    }

    if old:
        rename_columns['team_id'] = 'previous_team_id'

    positions.rename(columns=rename_columns, inplace=True)

    positions['OF'] = (positions['LF'] | positions['CF'] | positions['RF']).astype(int)
    positions['MI'] = (positions['B2'] | positions['SS']).astype(int)
    positions['CI'] = (positions['B1'] | positions['B3']).astype(int)
    positions['UTIL'] = 1

    return positions


def load_keepers():
    """
    Load keeper salaries

    """
    keepers = pandas.read_csv(os.path.join(WORKING_DIRECTORY, 'keepers.csv'), na_values='NA', dtype={'mlbam_id': object})

    del keepers['name']

    return keepers


def load_espn_auction_values():
    """
    Load ESPN auction values

    """
    espn_values = pandas.read_csv(os.path.join(WORKING_DIRECTORY, 'espn_values.csv'), na_values='NA', dtype={'espn_id': object})

    return espn_values


def add_espn_auction_values(players):
    """
    Merge ESPN auction values into player valuations

    """
    espn_values = load_espn_auction_values()

    players = players.merge(espn_values, how='left', on='espn_id')

    return players


def load_rosters():
    """
    Load ESPN rosters

    """
    rosters = pandas.read_csv(os.path.join(WORKING_DIRECTORY, 'rosters.csv'), na_values='NA', dtype={'espn_id': object})

    return rosters


def add_roster_state(players):
    """
    Merge ESPN rosters into player valuations

    """
    rosters = load_rosters()

    players = players.merge(rosters, how='left', on='espn_id')

    return players
