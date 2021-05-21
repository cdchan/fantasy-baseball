"""
Utility functions

"""

import os

import numpy
import pandas


from config import (
    CURRENT_YEAR,
    DATA_DIRECTORY,
    LEAGUE_DATA_DIRECTORY,
    PROJECTIONS_DIRECTORY,
    WORKING_DIRECTORY
)


fangraphs_column_mapping = {
    '"Name"': "fg_name",
    'Name': "fg_name",
    'playerid': "fg_id",
    'K/9': "K9",
    'SO': "K",
    '2B': "D",
    '3B': "T",
}


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

    projections.rename(columns=fangraphs_column_mapping, inplace=True)

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

    projections.rename(columns=fangraphs_column_mapping, inplace=True)  # columns can't begin with numbers

    projections.sort_values('PA', ascending=False, inplace=True)
    projections.drop_duplicates(subset=['fg_id'], keep='last', inplace=True)

    projections = convert_fangraphs_playerid(projections)

    return projections


def load_playing_time(player_type):
    """
    Load playing time from the past 14 days
    """
    filename = os.path.join(
        'data',
        '{}_playing_time.csv'.format(player_type))

    playing_time = pandas.read_csv(filename, encoding="utf-8-sig", error_bad_lines=False, dtype={'playerid': object})

    playing_time.rename(columns=fangraphs_column_mapping, inplace=True)

    return playing_time


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
    positions = pandas.read_csv(os.path.join(LEAGUE_DATA_DIRECTORY, 'espn_eligibilities.csv'), na_values='NA', dtype={'espn_id': object}, encoding='utf-8')

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
    keepers = pandas.read_csv(os.path.join(LEAGUE_DATA_DIRECTORY, 'keepers.csv'), na_values='NA', dtype={'mlb_id': object}, comment='#')

    del keepers['name']

    return keepers


def load_previous_prices():
    """
    Load auction prices from last year
    """
    auction = pandas.read_csv(os.path.join(DATA_DIRECTORY, 'historical/auction_{}.csv'.format(CURRENT_YEAR - 1)), na_values='NA', dtype={'playerid': object})

    auction.rename(columns={'playerid': 'espn_fantasy_id'}, inplace=True)

    return auction[['espn_fantasy_id', 'price', 'teamid']]


def load_espn_auction_values():
    """
    Load ESPN auction values

    """
    espn_values = pandas.read_csv(os.path.join(DATA_DIRECTORY, 'espn_values.csv'), na_values='NA', dtype={'espn_id': object})

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
    rosters = pandas.read_csv(os.path.join(LEAGUE_DATA_DIRECTORY, 'rosters.csv'), na_values='NA', dtype={'espn_id': object})

    return rosters


def add_roster_state(players):
    """
    Merge ESPN rosters into player valuations

    """
    rosters = load_rosters()

    players = players.merge(rosters, how='left', on='espn_id')

    return players
