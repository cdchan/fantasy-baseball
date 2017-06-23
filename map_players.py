"""
Create player mapping

1. Load existing mapping
2. Map any fantasy relevant players with only stats_ids to mlbam_ids
3. Map any fantasy relevant players with only bis_ids to mlbam_ids
4. Map any fantasy relevant players to espn_ids

"""

import os

import pandas
from fuzzywuzzy import process

import utils
from utils import load_fangraphs_batter_projections, load_batter_positions, load_fangraphs_pitcher_projections, load_pitcher_positions, load_mapping, WORKING_DIRECTORY


INTERACTIVE = True


def main():
    mapping = load_mapping()

    print u"mapping batters"

    # load player projections to filter for only fantasy relevant players
    projections = load_fangraphs_batter_projections()
    projections = projections.query('PA > 20')  # only batters projected for more than 20 PA
    mapping = map_projections(projections, 'stats_id', mapping)
    mapping = map_projections(projections, 'bis_id', mapping)

    positions = load_batter_positions()  # these have the ESPN ids for batters
    mapping = map_espn(projections, positions, mapping)

    print u"mapping pitchers"

    projections = load_fangraphs_pitcher_projections()
    projections = projections.query('IP > 20')  # only pitchers projected for more than 20 IP
    mapping = map_projections(projections, 'stats_id', mapping)
    mapping = map_projections(projections, 'bis_id', mapping)

    positions = load_pitcher_positions()  # these have the ESPN ids for pitchers
    mapping = map_espn(projections, positions, mapping)

    mapping = mapping.sort_values('name')

    mapping.to_csv(os.path.join(WORKING_DIRECTORY, 'player_mapping.csv'), index=False, index_label=False, columns=['mlbam_id', 'name', 'bis_id', 'stats_id', 'espn_id'])


def load_bp_mapping():
    """
    Baseball Prospectus has a very comprehensive player mapping

    http://www.baseballprospectus.com/sortable/playerid_list.php

    """
    bp = pandas.read_csv("bp_mapping.csv")
    bp['fullname'] = bp['FIRSTNAME'].str.cat(bp['LASTNAME'], sep=' ')

    return bp[bp['MLBCODE'].notnull()]  # only want players with MLBAM id


def map_projections(projections, id_name, mapping):
    """
    Fill in player mapping of players with only `id_name` ids

    """
    # filter to only projections with a STATS id, BIS id, etc
    players = projections[projections[id_name].notnull()]

    # filter to only players without unknown MLBAM ids
    players = players.merge(mapping[['mlbam_id', id_name]], how='left', on=id_name)
    players_to_map = players[players['mlbam_id'].isnull()]

    return map_to_mlbam(players_to_map, id_name, mapping)


def map_to_mlbam(players, id_name, mapping):
    """
    Given dataframe of players, find their MLBAM ids

    id_name: enum('stats_id', 'bis_id')

    """
    # Baseball Prospectus list has many MLBAM ids
    bp_mapping = load_bp_mapping()

    # need these dicts of name -> MLBAM id for fuzzywuzzy matching
    mapping_choices = dict(zip(mapping['mlbam_id'], mapping['name']))
    bp_choices = dict(zip(bp_mapping['MLBCODE'].astype(int), bp_mapping['fullname']))

    for player in players.itertuples():
        print u"attempting to match {} {} ({})".format(id_name, getattr(player, id_name), player.name)
        # two cases:
        # a) we have the MLBAM id, but not mapped to given `id_name`
        # b) we don't have the MLBAM id

        print u"trying current mapping"
        try:
            mlbam_id = match_name(player.name, mapping_choices)
        except LookupError as exc:
            new_mapping = {
                'name': [player.name],
                id_name: [getattr(player, id_name)],
            }

            print u"trying BP mapping"
            try:
                mlbam_id = match_name(player.name, bp_choices)
            except LookupError as exc:
                print u"unable to match {} {} ({})".format(id_name, getattr(player, id_name), player.name)
                mlbam_id = [0]

                if INTERACTIVE:  # gives user a prompt to select the right player
                    mlbam_id = [interactive(exc.args[1])]
            finally:
                new_mapping['mlbam_id'] = mlbam_id

                mapping = mapping.append(pandas.DataFrame(new_mapping), ignore_index=True)
        else:
            mapping.set_value(
                mapping['mlbam_id'] == mlbam_id,  # row
                id_name,  # column
                getattr(player, id_name)  # new value
            )

    return mapping


def match_name(name, choices):
    """
    Given a name and a set of choices, use the `fuzzywuzzy` library to pick the best match

    """
    if name:
        matches = process.extract(name, choices)

        # best match = matches[0]
        # next best match = matches[1]
        # check if the best match is a 100% match and that there is only a single 100% match
        if matches[0][1] == 100 and matches[1][1] < 100:
            return matches[0][2]

    raise LookupError('Unable to match', matches)


def map_espn(projections, positions, mapping):
    """
    Map projection to ESPN id

    """
    mapping['playerid'] = mapping['bis_id'].combine_first(mapping['stats_id'])

    projections = projections.merge(mapping[['mlbam_id', 'playerid', 'espn_id']], how='left', on='playerid')

    players_to_map = projections[projections['espn_id'].isnull()]

    # positions['C_str'] = numpy.where(positions['C'], 'C', '')
    # need these dicts of name -> ESPN id for fuzzywuzzy matching
    espn_choices = dict(zip(positions['espn_id'], positions['name_espn']))

    for player in players_to_map.itertuples():
        print u"attempting to match {name} to ESPN id".format(name=player.name)

        try:
            espn_id = match_name(player.name, espn_choices)
        except LookupError as exc:
            print u"unable to match {name} / Fangraphs id:  {fangraphs_id}".format(name=player.name, fangraphs_id=player.playerid)
            espn_id = None

            if INTERACTIVE:
                espn_id = interactive(exc.args[1])
        finally:
            mapping.set_value(
                mapping['mlbam_id'] == player.mlbam_id,  # row
                'espn_id',  # column
                espn_id  # new value
            )

    return mapping


def interactive(matches):
    """
    Interactive input of matching

    """
    for i, match in enumerate(matches, 1):
        print u"{i} {name} {id}".format(i=i, name=match[0], id=match[2])

    match_index = input("Which match? (0 for none) ")

    if match_index:
        return matches[match_index + 1][2]
    else:
        return None


if __name__ == '__main__':
    main()
