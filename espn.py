"""
ESPN league wrapper

# TODO - handle draft auction values

"""

import datetime
import json
import os

import espn_api.baseball
import pandas


class Espn(espn_api.baseball.League):
    def __init__(self, league_data_directory):
        self.league_data_directory = league_data_directory

        with open(os.path.join(self.league_data_directory, "config.json"), 'r') as f:
            config = json.load(f)

        super().__init__(**config)

        self.possible_positions = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH", "SP", "RP"]
    
    def save_eligibilities(self):
        """Get all player positional eligibilities and save to CSV"""
        data_date = datetime.date.today()

        self.save_rosters(data_date)
        self._process_free_agents(data_date)

        columns = ['espn_name', 'espn_id', 'pro_team', 'espn_injury_status'] + self.possible_positions
        players = pandas.concat([
            self.rostered_players[columns],
            self.free_agent_players[columns]
        ])

        players.to_csv(os.path.join(
            self.league_data_directory,
            "espn_eligibilities.csv"
        ), columns=columns, encoding='utf8', index=False)
            
        players.to_csv(os.path.join(
            self.league_data_directory,
            "historical",
            f"espn_eligibilities_{data_date:%Y-%m-%d}.csv"
        ), columns=columns, encoding='utf8', index=False)

    def save_rosters(self, data_date=datetime.date.today()):
        """Get all rostered players and save rosters to CSV"""
        rostered_players = []
        
        for team in self.teams:
            for x in team.roster:
                player = self._process_player(x, self.possible_positions)
                player['fantasy_team_id'] = team.team_id

                rostered_players.append(player)
        
        self.rostered_players = pandas.DataFrame(rostered_players)

        self.rostered_players.to_csv(os.path.join(
            self.league_data_directory,
            "rosters.csv"
        ), encoding='utf8', index=False)

        self.rostered_players.to_csv(os.path.join(
            self.league_data_directory,
            "historical",
            f"rosters_{data_date:%Y-%m-%d}.csv"
        ), encoding='utf8', index=False)
        
    def _process_free_agents(self, data_date=datetime.date.today(), size=500):
        """Get all free agents"""
        free_agent_players = []

        for x in self.free_agents(size):
            player = self._process_player(x, self.possible_positions)

            free_agent_players.append(player)
        
        self.free_agent_players = pandas.DataFrame(free_agent_players)
    
    @staticmethod
    def _process_player(player, possible_positions):
        """Convert from player class to player dict"""
        player_dict = {
            'espn_id': player.playerId,
            'espn_name': player.name,
            # 'espn_value': player_json['draftAuctionValue'],
            'pro_team': player.proTeam,
            'espn_injury_status': player.injuryStatus
        }

        for pos in possible_positions:
            if pos in player.eligibleSlots:
                player_dict[pos] = 1
            else:
                player_dict[pos] = 0
        
        return player_dict
    
    def save_scores(self):
        """
        Saves all boxscores for current season
        
        This is based on my code in https://github.com/cwendt94/espn-api/blob/19613d73c6476a78b3ccffd4e0e045c6e457cb62/espn_api/baseball/box_score.py
        """
        scores = []

        for i in range(1, self.currentMatchupPeriod):
            weekly_box_scores = self.box_scores(i)

            for box_score in weekly_box_scores:
                if box_score.away_team:
                    # we only want competitive matchups, not byes
                    for as_home in (True, False):
                        scores.append(self._process_box_score(
                            box_score,
                            self.year,
                            i,
                            as_home=as_home)
                        )

        scores = pandas.DataFrame(scores)
        scores.to_csv(os.path.join(
            self.league_data_directory,
            "scores",
            f"scores_{self.year}.csv"
        ), encoding='utf8', index=False)

    @staticmethod
    def _process_box_score(box_score, year, week, as_home=True):
        """Retrieve box scores and convert to dict"""
        stats_mapping = [
            ('AB', 'AB'),
            ('H', 'H'),
            ('R', 'R'),
            ('HR', 'HR'),
            ('TB', 'TB'),
            ('RBI', 'RBI'),
            ('BB', 'B_BB'),
            ('SB', 'SB'),
            ('OBP', 'OBP'),
            ('IP', 'OUTS'),
            ('pH', 'P_H'),
            ('ER', 'ER'),
            ('pBB', 'P_BB'),
            ('W', 'W'),
            ('SV', 'SV'),
            ('ERA', 'ERA'),
            ('WHIP', 'WHIP'),
            ('K9', 'K/9')
        ]

        if as_home:
            row = {
                'team_id': box_score.home_team.team_id,
                'opponent_team_id': box_score.away_team.team_id
            }
            stats = box_score.home_stats
        else:
            row = {
                'team_id': box_score.away_team.team_id,
                'opponent_team_id': box_score.home_team.team_id
            }
            stats = box_score.home_stats
        
        row['year'] = year
        row['matchup_period'] = week

        for stat in stats_mapping:
            row[stat[0]] = stats[stat[1]]['value']

        row['IP'] = str(int(row['IP'] / 3)) + '.' + str(int(row['IP'] % 3))

        return row
