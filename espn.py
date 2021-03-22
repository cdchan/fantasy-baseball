"""
Update ESPN league information
"""

import datetime
import gzip
import json
import os

import pandas
import requests

from config import (
    CURRENT_YEAR, DATA_DIRECTORY
)
import league


class Espn(league.League):
    players_info_filename_base = os.path.join(
        DATA_DIRECTORY,
        "historical",
        "espn_players_{:%Y-%m-%d}.json.gz")

    def __init__(self, league_data_directory, projections_name="rfangraphsdc"):
        super(Espn, self).__init__(league_data_directory, projections_name)

        with open(os.path.join(league_data_directory, "config.json"), 'r') as f:
            config = json.load(f)

        self.league_id = config['league_id']

        self.players_info_filename = None

    @staticmethod
    def load_client(league_data_directory):
        return EspnClient(league_data_directory)

    def scrape_player_info(self):
        """
        Scrape ESPN player data (rosters, positional eligibility).

        A single JSON contains both positional eligibility and roster state
        """
        data_date = datetime.date.today()

        headers = {'x-fantasy-filter': json.dumps({
            'players': {
                'limit': 1000,  # TODO switch to paging
                "sortPercOwned": {"sortPriority":2, "sortAsc": False}
            }
        })}

        response = self.client.session.get(f"http://fantasy.espn.com/apis/v3/games/flb/seasons/{CURRENT_YEAR}/segments/0/leagues/{self.league_id}?view=kona_player_info", headers=headers)
        self.players_info_filename = self.players_info_filename_base.format(data_date)
        
        # these jsons are large, so compress them
        with gzip.GzipFile(self.players_info_filename, 'w') as f:
            f.write(response.text.encode('utf-8'))
        
        self.rosters = self.scrape_rosters(response.json(), data_date)
        self.elig = self.scrape_elig(response.json(), data_date)
    
    def scrape_rosters(self, espn_players_json=None, data_date=None):
        """
        Convert JSON from ESPN into CSV of team rosters
        """
        if not espn_players_json:
            with gzip.GzipFile(self.players_info_filename, 'r') as f:
                espn_players_json = json.loads(f.read().decode('utf-8'))
        
        players = []

        for player_json in espn_players_json['players']:
            player = {
                'espn_id': player_json['id'],
                'fantasy_team_id': player_json['onTeamId'],
            }

            if player['fantasy_team_id'] != 0:
                players.append(player)

        players = pandas.DataFrame(players)#, dtype=self.playerid_dtypes)
        print(players.dtypes)

        players.to_csv(os.path.join(
            self.league_data_directory,
            "rosters.csv"
        ), encoding='utf8', index=False)

        players.to_csv(os.path.join(
            self.league_data_directory,
            "historical",
            "rosters_{:%Y-%m-%d}.csv".format(data_date)
        ), encoding='utf8', index=False)

        return players
    
    def scrape_elig(self, espn_players_json=None, data_date=None, draft=False):
        """
        Convert JSON from ESPN into a CSV of positional eligiblities for players
        """
        POSSIBLE_POSITIONS = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH", "SP", "RP"]
        POSITION_IDS = [0, 1, 2, 3, 4, 8, 9, 10, 11, 14, 15]
        position_mapping = {k: v for k, v in zip(POSSIBLE_POSITIONS, POSITION_IDS)}

        if not espn_players_json:
            with gzip.GzipFile(self.players_info_filename, 'r') as f:
                espn_players_json = json.loads(f.read().decode('utf-8'))
        
        players = []

        for player_json in espn_players_json['players']:
            player = {
                'espn_id': player_json['id'],
                'espn_name': player_json['player']['fullName'],
                'espn_value': player_json['draftAuctionValue'],
                'espn_team_id': player_json['player']['proTeamId']
            }

            for pos, espn_pos_id in position_mapping.items():
                if espn_pos_id in player_json['player']['eligibleSlots']:
                    player[pos] = 1
                else:
                    player[pos] = 0
            
            players.append(player)
        
        players = pandas.DataFrame(players)
        print(players.dtypes)

        # TODO probably should load this in a utility function
        espn_team_mapping = pandas.read_csv(os.path.join(
            DATA_DIRECTORY,
            "espn_real_team_mapping.csv"
        ))

        players = players.merge(espn_team_mapping, on='espn_team_id', how='left')

        columns = ['espn_name', 'espn_id', 'team_abbr'] + POSSIBLE_POSITIONS

        players.to_csv(os.path.join(
            DATA_DIRECTORY,
            "espn_eligibilities.csv"
        ), columns=columns, encoding='utf8', index=False)
            
        players.to_csv(os.path.join(
            DATA_DIRECTORY,
            "historical",
            "espn_eligibilities_{:%Y-%m-%d}.csv".format(data_date)
        ), columns=columns, encoding='utf8', index=False)

        if draft:
            columns = ['espn_name', 'espn_id', 'espn_value']

            players[players['espn_value'] > 0].to_csv(os.path.join(
                DATA_DIRECTORY,
                "espn_values.csv"
            ), columns=columns, encoding='utf8', index=False)
        
        return players


class EspnClient(object):
    """
    Client that sets up cookies for authentication.
    """
    def __init__(self, league_directory):
        with open(os.path.join(league_directory, "cookie.txt"), 'r') as f:
            cookie_string = f.read()
        
        cookie = {}

        for x in cookie_string.split(';'):
            k, v = x.strip().split('=', maxsplit=1)
            cookie[k] = v
        
        self.session = requests.Session()
        # session.cookies = requests.cookies.cookiejar_from_dict(cookie_dict)
        self.session.headers.update({'Cookie': cookie_string})
