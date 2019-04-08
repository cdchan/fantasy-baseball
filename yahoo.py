"""
Yahoo fantasy baseball league
"""
import datetime
import json
import os

from lxml import etree
import pandas

from client import YahooClient
import league


class Yahoo(league.League):
    def __init__(self, league_data_directory, projections_name="rfangraphsdc"):
        super(Yahoo, self).__init__(league_data_directory, projections_name)
        self.projections_name = projections_name

        with open(os.path.join(league_data_directory, "config.json"), 'r') as f:
            config = json.load(f)
        
        self._client_id = config['client_id']
        self._client_secret = config['client_secret']
        self.sport_id = config['sport_id']
        self.league_id = config['league_id']
        self.weekly = config['weekly']
        self.n_weeks = config['total_weeks']
        self.n_teams = config['n_teams']
        self.n_batters = config['n_batters']
        self.n_pitchers = config['n_pitchers']
        self.positions = config['positions']
        self.categories = config['categories']

        self.elig = self.load_elig()  # TODO: make this a class variable?

        # self.load_league_category_values()
        self.median_level = config['median_level']
        self.standings_delta = config['standings_delta']

        self.load_players()
    
    def load_client(self, league_data_directory):
        return YahooClient(
            self._client_id,
            self._client_secret,
            league_data_directory)

    def load_players(self):
        """
        Same as base league, but add QS
        """
        self.add_quality_starts()

        self.add_player_mapping()

        self.add_elig()

        self.calc_batter_value()
        self.batters.sort_values('p_added', ascending=False, inplace=True)

        self.calc_pitcher_value()
        self.pitchers.sort_values('p_added', ascending=False, inplace=True)

        self.add_roster_state()
    
    def add_quality_starts(self):
        """
        Add quality starts projections from Razzball.

        Fangraphs projections do not have quality starts
        """
        if 'QS' not in self.pitchers.columns:
            razzball = pandas.read_csv(os.path.join(
                self.data_directory,
                "projections",
                "razzball_pitchers.csv"
            ))
            
            razzball.rename(columns={
                'Name': 'razzball_name'
            }, inplace=True)
        
            self.pitchers = self.pitchers.merge(razzball[['razzball_name', 'QS']], how='left', left_on='fg_name', right_on='razzball_name')

            self.pitchers['QS'].where(self.pitchers['QS'].notnull(), 0.55 * self.pitchers['GS'], inplace=True)
    
    def output_valuations(self, directory=None):
        """
        Output player valuations to CSVs.
        """
        if not directory:
            directory = os.path.join(
                self.league_data_directory,
                "valuations"
            )

        output_cols = [
            'fg_name', 'Team', 'team_id',
            'position', 'value', 'cost', 'p_added_adj',
            'G', 'PA', 'AB',
            'H', 'HR', 'R', 'RBI', 'SB', 'OPS',
            'p_added', 'p_added_R', 'p_added_H', 'p_added_HR', 'p_added_RBI', 'p_added_SB', 'p_added_OPS',
            'C', '1B', '2B', 'SS', '3B', 'OF', 'Util',
        ]

        self.batters.to_csv(os.path.join(
            self.league_data_directory,
            "batters_valuation.csv"
        ), columns=output_cols, index=False, float_format='%.2f')
        self.batters.to_csv(os.path.join(
            directory,
            "batters_valuation_{:%Y-%m-%d}.csv".format(datetime.date.today())
        ), columns=output_cols, index=False, float_format='%.2f')

        output_cols = [
            'fg_name', 'Team', 'team_id',
            'position', 'value', 'cost', 'p_added_adj',
            'G', 'GS', 'IP',
            'QS', 'SV+H', 'SO', 'ERA', 'WHIP', 'K/9', 'SV', 'HLD',
            'p_added', 'p_added_QS', 'p_added_SV+H', 'p_added_SO', 'p_added_ERA', 'p_added_WHIP', 'p_added_K/9',
            'SP', 'RP'
        ]

        self.pitchers.to_csv(os.path.join(
            self.league_data_directory,
            "pitchers_valuation.csv"
        ), columns=output_cols, index=False, float_format='%.2f')
        self.pitchers.to_csv(os.path.join(
            directory,
            "pitchers_valuation_{:%Y-%m-%d}.csv".format(datetime.date.today())
        ), columns=output_cols, index=False, float_format='%.2f')

    def add_player_mapping(self):
        """
        Join player mapping to projections for player ids.
        """
        self.batters = self.batters.merge(self.player_mapping[['fg_id', 'yahoo_id']], how='left')

        print(self.batters[self.batters['yahoo_id'].isnull()].sort_values('PA', ascending=False).head(10))

        self.pitchers = self.pitchers.merge(self.player_mapping[['fg_id', 'yahoo_id']], how='left')

        print(self.pitchers[self.pitchers['yahoo_id'].isnull()].sort_values('IP', ascending=False).head(10))
    
    def add_elig(self):
        """
        Join player position eligibilities to projections.
        """
        for player_type in ["batters", "pitchers"]:
            setattr(self, player_type, getattr(self, player_type).merge(
                self.elig[self.elig.columns.difference(['name'])],
                how='left',
                on='yahoo_id')
            )

    def load_league_category_values(self):
        """
        How valuable is each category; very league specific
        """
        pass
    
    def calc_batter_value(self):
        """
        Calculate batter value based on how categories are valued in this league
        """
        self.batters['p_added'] = 0

        for category in self.categories['batting']:
            if category in ['PA', 'AB', 'OBP', 'SLG']:
                continue
            elif category == 'OPS':
                difference_OB = (self.batters['OBP'] - self.median_level['batting']['OBP']) * (self.batters['PA'] / self.n_weeks)
                difference_TB = (self.batters['SLG'] - self.median_level['batting']['SLG']) * (self.batters['AB'] / self.n_weeks)
        
                new_team_OBP = self.median_level['batting']['OBP'] + difference_OB / self.median_level['batting']['PA']
                new_team_SLG = self.median_level['batting']['SLG'] + difference_TB / self.median_level['batting']['AB']
        
                new_team_OPS = new_team_OBP + new_team_SLG
        
                self.batters['new_team_OPS'] = new_team_OPS
        
                self.batters['p_added_OPS'] = (new_team_OPS - self.median_level['batting']['OPS']) / self.standings_delta['batting']['OPS'] * (1 / self.n_teams)
            else:
                self.batters['p_added_{}'.format(category)] = (self.batters[category] / self.n_weeks - self.median_level['batting'][category] / self.n_batters) / self.standings_delta['batting'][category] * (1 / self.n_teams)
    
            self.batters['p_added'] += self.batters['p_added_{}'.format(category)]
    
    def calc_pitcher_value(self):
        """
        Calculate pitcher value based on how categories are valued in this league
        """
        self.pitchers['p_added'] = 0

        for category in self.categories['pitching']:
            if category == 'IP':
                continue
            elif category == 'ERA':
                # replace the pitcher's ERA with the median ERA
                # given the pitchers's IP contribution, how much would team ERA be affected?
                
                difference_ER = (self.pitchers['ERA'] - self.median_level['pitching']['ERA']) / 9.0 * (self.pitchers['IP'] / self.n_weeks)
                new_team_ERA =  self.median_level['pitching']['ERA'] + difference_ER / self.median_level['pitching']['IP'] * 9.0
                
                self.pitchers['p_added_ERA'] = (self.median_level['pitching']['ERA'] - new_team_ERA) / self.standings_delta['pitching']['ERA'] * (1 / self.n_teams)
            elif category == 'K/9':
                difference_K_per_week = (self.pitchers['K/9'] - self.median_level['pitching']['K/9']) / 9.0 * (self.pitchers['IP'] / self.n_weeks)
                
                new_team_K9 =self. median_level['pitching']['K/9'] + difference_K_per_week / self.median_level['pitching']['IP'] * 9.0
                
                self.pitchers['p_added_K/9'] = (new_team_K9 - self.median_level['pitching']['K/9']) / self.standings_delta['pitching']['K/9'] * (1 / self.n_teams)
            elif category == 'WHIP':
                # replace the pitcher's WHIP with the median WHIP
                # given the pitchers's IP contribution, how much would team WHIP be affected?
                
                difference_WH = (self.pitchers['WHIP'] - self.median_level['pitching']['WHIP']) * self.pitchers['IP'] / self.n_weeks
                new_team_WHIP =  self.median_level['pitching']['WHIP'] + difference_WH / self.median_level['pitching']['IP']
                
                self.pitchers['p_added_WHIP'] = (self.median_level['pitching']['WHIP'] - new_team_WHIP) / self.standings_delta['pitching']['WHIP'] * (1 / self.n_teams)
            else:
                self.pitchers['p_added_{}'.format(category)] = (self.pitchers[category] / self.n_weeks - self.median_level['pitching'][category] / self.n_pitchers) / self.standings_delta['pitching'][category] * (1 / self.n_teams)
            
            self.pitchers['p_added'] += self.pitchers['p_added_{}'.format(category)]
    
    def add_roster_state(self):
        """
        Join current team rosters to projections
        """
        for player_type in ["batters", "pitchers"]:
            setattr(self, player_type, getattr(self, player_type).merge(self.rosters[['yahoo_id', 'team_id']], how='left'))

    def load_elig(self):
        """
        Load player position eligibilities from CSV.
        """
        elig = pandas.read_csv(os.path.join(
            self.data_directory,
            "yahoo_eligibility.csv"
        ), dtype=self.playerid_dtypes)

        elig['P'] = elig['SP'] | elig['RP']

        elig['Util'] = 1 - elig['P']

        return elig
    
    def refresh_eligibilities(self):
        """
        Query Yahoo API to refresh player position eligibilities.
        """
        # namespace for Yahoo fantasy sports API
        ns = {'f': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}

        base_url = "https://fantasysports.yahooapis.com/fantasy/v2/league/{sport_id}.l.{league_id}/players".format(sport_id=self.sport_id, league_id=self.league_id)
        url = base_url + ";start={}"

        players = []
        start = 0
        more = True

        while more:
            more = False
            r = self.client.session.get(url.format(start))

            root = etree.fromstring(r.content)

            for player_xml in root.xpath("//f:player", namespaces=ns):
                player = {
                    'yahoo_id': player_xml.findtext("f:player_id", namespaces=ns),
                    'yahoo_name': player_xml.findtext("f:name/f:full", namespaces=ns).strip('.'),
                }

                for pos_xml in player_xml.findall("f:eligible_positions/f:position", namespaces=ns):
                    if pos_xml.text in self.positions:
                        player[pos_xml.text] = 1

                players.append(player)

                start += 1
                more = True  # processed at least one player
        
        yahoo_elig = pandas.DataFrame(players)
        yahoo_elig = yahoo_elig[['yahoo_name', 'yahoo_id'] + self.positions]

        yahoo_elig.fillna(0, inplace=True)
        yahoo_elig[self.positions] = yahoo_elig[self.positions].astype(int)

        yahoo_elig.to_csv(os.path.join(
            self.data_directory,
            "yahoo_eligibility.csv"
        ), encoding='utf8', index=False)

        yahoo_elig.to_csv(os.path.join(
            self.data_directory,
            "historical",
            "yahoo_eligibility_{:%Y-%m-%d}.csv".format(datetime.date.today())
        ), encoding='utf8', index=False)

        self.elig = self.load_elig()


    def refresh_rosters(self):
        """
        Query Yahoo API to refresh current team rosters.
        """
        if self.weekly:
            date = "{:%Y-%m-%d}".format(find_closest_monday())
        else:
            date = "{:%Y-%m-%d}".format(datetime.datetime.today())

        ns = {'f': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}

        # https://developer.yahoo.com/fantasysports/guide/#id47

        players = []

        base_url = "https://fantasysports.yahooapis.com/fantasy/v2/team/{sport_id}.l.{league_id}".format(sport_id=self.sport_id, league_id=self.league_id)
        url = base_url + ".t.{team_id}/roster;date={date}"

        for team_id in range(1, self.n_teams + 1):
            r = client.session.get(url.format(team_id=team_id, date=date))

            root = etree.fromstring(r.content)
            # print(r.content)

            for player in root.xpath("//f:player", namespaces=ns):
                players.append({
                    'team_id': team_id,
                    'yahoo_id': player.findtext("f:player_id", namespaces=ns),
                    'yahoo_name': player.findtext("f:name/f:full", namespaces=ns).replace('.', '')
                })

        rosters = pandas.DataFrame(players)

        # fix Shohei Ohtani
        # as batter
        rosters.loc[rosters['yahoo_id'] == '1000001', 'yahoo_id'] = 10835
        # as pitcher
        rosters.loc[rosters['yahoo_id'] == '1000002', 'yahoo_id'] = 10835

        if len(rosters) == 0:
            raise Exception('Failed to retrieve roster')
        else:
            rosters.to_csv(os.path.join(
                self.league_data_directory,
                "rosters.csv"
            ), encoding='utf8', index=False)
            rosters.to_csv(os.path.join(
                self.league_data_directory,
                "historical",
                "rosters_{}.csv".format(date)
            ), encoding='utf8', index=False)
        
        self.rosters = rosters
    
    @staticmethod
    def find_closest_monday():
        """
        Find the closest Monday for an accurate roster. Rosters are set at the beginning of each week for weekly leagues.
        """
        today = datetime.datetime.today()

        days_ahead = 7 - today.weekday()  # Monday = 0

        if days_ahead == 7:
            return today
        else:
            return today + datetime.timedelta(days_ahead)


def main():
    x = Yahoo("yahoo-new", "rfangraphsdc")
    x.refresh_rosters()
    # x.refresh_eligibilities()
    x.load_players()
    x.output_valuations()


if __name__ == '__main__':
    main()
