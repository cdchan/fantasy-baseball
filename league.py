"""
Fantasy baseball leagues as classes
"""

import os

import pandas

from config import (
    DATA_DIRECTORY
)


class League(object):
    """
    Represents a fantasy baseball league
    """
    data_directory = DATA_DIRECTORY

    playerid_dtypes = {'mlb_id': 'Int64', 'espn_id': 'Int64', 'yahoo_id': 'Int64'}

    def __init__(self, league_data_directory, projections_name):
        self.league_data_directory = league_data_directory

        self.batters = self.load_player_projections(projections_name, "batters")
        self.pitchers = self.load_player_projections(projections_name, "pitchers")

        self.player_mapping = pandas.read_csv(
            os.path.join(
                self.data_directory,
                "player_mapping.csv"
        ), dtype=self.playerid_dtypes)

        try:
            self.rosters = pandas.read_csv(os.path.join(
                self.league_data_directory,
                "rosters.csv"
            ), dtype=self.playerid_dtypes)
        except pandas.errors.EmptyDataError:
            print("Empty rosters")
        # TODO handle if file doesn't exist

        self._client = None
    
    @property
    def client(self):
        """
        Client for interacting with wherever the league is hosted
        """
        if self._client is None:
            self._client = self.load_client(self.league_data_directory)
        return self._client
    
    def load_player_projections(self, projections_name, player_type):
        """
        Load player projections for batters or pitchers
        """
        projections = pandas.read_csv(
            os.path.join(
                self.data_directory,
                "projections",
                "{projections_name}_{player_type}.csv".format(
                    projections_name=projections_name,
                    player_type=player_type)))
        
        projections.rename(columns={
            'playerid': 'fg_id',
            'Name': 'fg_name',
        }, inplace=True)

        if player_type == 'batters':
            projections.rename(columns={
                '2B': 'D',
                '3B': 'T'
            }, inplace=True)

            projections['XBH'] = projections['D'] + projections['T'] + projections['HR']
        else:
            projections['SV+H'] = projections['SV'] + projections['HLD']
        
        return projections
