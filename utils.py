"""
Utility functions

"""

import os

import numpy
import pandas


from config import DATA_DIRECTORY, PROJECTIONS_DIRECTORY, WORKING_DIRECTORY


def load_mapping():
    """
    Load player id mappings

    """
    location = os.path.join(DATA_DIRECTORY, 'player_mapping.csv')

    mapping = pandas.read_csv(location, dtype={
        'mlb_id': object,
        'fg_id': object,
        'espn_id': object
    }, encoding='utf-8')

    # TODO: sort out Fangraphs player ids
    # mapping['playerid'] = mapping['bis_id'].combine_first(mapping['stats_id'])  # use BIS id if available, otherwise STATS id

    print(u"location of player mapping file: {}".format(location))

    return mapping


def load_fangraphs_pitcher_projections(projection_type):
    """
    Load Fangraphs pitcher projections
    """
    filename = '{}_pitchers.csv'.format(projection_type)

    projections = pandas.read_csv(os.path.join(PROJECTIONS_DIRECTORY, filename), encoding="utf-8-sig")

    projections.rename(columns={
        '"Name"': "fg_name",
        'Name': "fg_name",
        'playerid': "fg_id",
        'K/9': "K9",
        'SO': "K"
    }, inplace=True)

    projections.sort_values('IP', ascending=False, inplace=True)
    projections.drop_duplicates(subset=['fg_id'], keep='last', inplace=True)

    projections = convert_fangraphs_playerid(projections)

    return projections


def load_fangraphs_batter_projections(projection_type):
    """
    Load Fangraphs batter projections
    """
    filename = '{}_batters.csv'.format(projection_type)

    projections = pandas.read_csv(os.path.join(PROJECTIONS_DIRECTORY, filename), encoding="utf-8-sig", error_bad_lines=False)

    projections.rename(columns={
        '"Name"': "fg_name",
        'Name': "fg_name",
        'playerid': "fg_id",
        '2B': "D",
        '3B': "T"
    }, inplace=True)  # columns can't begin with numbers

    projections.sort_values('PA', ascending=False, inplace=True)
    projections.drop_duplicates(subset=['fg_id'], keep='last', inplace=True)

    projections = convert_fangraphs_playerid(projections)

    return projections


def convert_fangraphs_playerid(projections):
    """
    Convert Fangraphs playerid to BIS id and STATS id

    """
    # BIS ids are numbers, if a playerid is not a number, set to NaN
    projections['bis_id'] = numpy.where(projections['fg_id'].str.isnumeric(), projections['fg_id'], numpy.nan)

    # if playerid is not a number, it's a STATS id
    projections['stats_id'] = numpy.where(~projections['fg_id'].str.isnumeric(), projections['fg_id'], numpy.nan)  # use None because this is an object array

    return projections


def load_espn_positions():
    """
    Load player positional eligibilities from ESPN
    """
    positions = pandas.read_csv(os.path.join(DATA_DIRECTORY, 'espn_eligibilities.csv'), na_values='NA', dtype={'espn_id': object}, encoding='utf-8')

    positions['OF'] = (positions['LF'] | positions['CF'] | positions['RF']).astype(int)
    positions['MI'] = (positions['2B'] | positions['SS']).astype(int)
    positions['CI'] = (positions['1B'] | positions['3B']).astype(int)

    positions['P'] = (positions['SP'] | positions['RP']).astype(int)

    positions['UTIL'] = 1 - positions['P']

    return positions


def load_pitcher_positions(old=False):
    """
    TODO: outdated

    Load pitcher teams and positional eligibilities from ESPN

    """
    positions = pandas.read_csv(os.path.join(WORKING_DIRECTORY, 'pitcher_eligibilities.csv'), na_values='NA', dtype={'espn_id': object}, encoding='utf-8')

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
    TODO: outdated

    Load batter teams and positional eligibilities from ESPN

    """
    positions = pandas.read_csv(os.path.join(WORKING_DIRECTORY, 'batter_eligibilities.csv'), na_values='NA', dtype={'espn_id': object}, encoding='utf-8')

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
