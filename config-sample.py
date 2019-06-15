"""
Configuration file

Variables to update:
* WORKING_DIRECTORY
* DATA_DIRECTORY
* CURRENT_YEAR
* season_final_day
* fangraphs_form_data
"""

import datetime
import os
import requests


WORKING_DIRECTORY = ''
DATA_DIRECTORY = os.path.join(WORKING_DIRECTORY, 'data')  # subdirectory under WORKING_DIRECTORY
PROJECTIONS_DIRECTORY = os.path.join(WORKING_DIRECTORY, 'data', 'projections')  # subdirectory under DATA_DIRECTORY
LEAGUE_DATA_DIRECTORY = os.path.join(WORKING_DIRECTORY, 'example_league_data_directory')


CURRENT_YEAR = 2019


#####
# team settings

season_final_day = datetime.datetime(2019, 9, 29)
REMAINING_WEEKS = (season_final_day - datetime.datetime.today()).days / 7 - 1  # at run time, how many weeks remaining in the season

if REMAINING_WEEKS > 25:
    REMAINING_WEEKS = 25  # this is for pre-season calculations; capping weeks at 25

N_TEAMS = 12  # number of teams
N_BATTERS = 14  # number of batters
N_PITCHERS = 9  # number of pitchers

BATTER_BUDGET_RATIO = 0.65  # how much to spend on batters vs pitchers


TEAM_PA_PER_WEEK = 287  # estimated number of PA per team per week


#####
# Fangraphs settings

# to download CSVs for Fangraphs projections
fangraphs_form_data = {
}


fangraphs_leaderboard_form_data = {
}


fangraphs_dfs_form_data = {
}