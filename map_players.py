"""
Rewrite of player mapping script

1. Load existing mapping
2. Map any fantasy relevant players to espn_ids

"""
import argparse
import os

import pandas

from config import DATA_DIRECTORY
from utils import (
    load_espn_positions,
    load_fangraphs_batter_projections,
    load_fangraphs_pitcher_projections,
    load_mapping,
)


MIN_PA = 100
MIN_IP = 10


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--projection", default="rfangraphsdc", help="projection system to use, choices are rfangraphs / steamer600u")
    # TODO add flag for which league ids need to be mapped (ESPN, Yahoo)
    parser.add_argument("--pa", default=100, help="minimum PA projected to merit mapping")
    parser.add_argument("--ip", default=10, help="minimum IP projected to merit mapping")
    args = parser.parse_args()

    mapping = load_mapping()

    projections = load_fangraphs_batter_projections(args.projection)
    projections = projections[projections['PA'] >= args.pa]  # only batters projected for more than min PA
    players = projections.merge(mapping[['mlb_id', 'fg_id', 'espn_id', 'yahoo_id']], how='left', on='fg_id')

    mapping = add_espn_id(mapping, players)

    projections = load_fangraphs_pitcher_projections(args.projection)
    projections = projections[projections['IP'] >= args.ip]  # only pitchers projected for more than min IP
    players = projections.merge(mapping[['mlb_id', 'fg_id', 'espn_id', 'yahoo_id']], how='left', on='fg_id')

    mapping = add_espn_id(mapping, players)

    mapping.sort_values(['fg_name', 'mlb_name'], inplace=True)

    mapping.to_csv('data/player_mapping.csv', index=False, columns=['mlb_id', 'mlb_name', 'fg_id', 'fg_name', 'espn_id', 'yahoo_id'])


def add_espn_id(mapping, players):
    """
    Add ESPN id to players without ESPN id

    TODO: how to handle players without a perfect match
    """
    # keep only players without ESPN id
    players_to_map = players[players['espn_id'].isnull()].copy()
    # (name, team) is not necessarily unique, so drop any players with the same name and team
    players_to_map.drop_duplicates(subset=['fg_name', 'Team'], keep=False, inplace=True)
    del players_to_map['espn_id']  # clear out column of nulls
    
    # ESPN position eligibilities have ESPN name and id
    espn_positions = load_espn_positions()
    # (name, team) is not necessarily unique, so drop any players with the same name and team
    espn_positions.drop_duplicates(subset=['espn_name', 'pro_team'], keep=False, inplace=True)

    espn_pro_teams = pandas.read_csv(os.path.join(DATA_DIRECTORY, 'espn_pro_team_mapping.csv'))

    espn_positions = espn_positions.merge(espn_pro_teams[['pro_team', 'team_abbr']])

    # look for exact matches between Fangraphs name and ESPN name
    matches = players_to_map.merge(espn_positions[['espn_name', 'team_abbr','espn_id']], left_on=['fg_name', 'Team'], right_on=['espn_name', 'team_abbr'], how='left')

    # pull out the perfect matches
    update_list = matches[matches['espn_id'].notnull()][['fg_name', 'fg_id', 'espn_id']].to_dict(orient='records')

    append_to_mapping = []
    for player_update in update_list:
        # if player exists in mapping already, update id
        if player_update['fg_id'] in mapping['fg_id'].values:
            mapping.loc[mapping['fg_id'] == player_update['fg_id'], 'espn_id'] = player_update['espn_id']
            print(player_update)
        # else add new player to mapping
        else:
            append_to_mapping.append(player_update)

    mapping = mapping.append(pandas.DataFrame(append_to_mapping), ignore_index=True, sort=False)

    # print out players without matches
    if 'PA' in matches.columns:
        print(matches[matches['espn_id'].isnull()][['fg_name', 'bis_id', 'stats_id', 'Team', 'PA']])
    else:
        print(matches[matches['espn_id'].isnull()][['fg_name','bis_id', 'stats_id', 'Team', 'IP']])

    return mapping


if __name__ == '__main__':
    main()
