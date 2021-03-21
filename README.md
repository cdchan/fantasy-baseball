# fantasy-baseball

# Fantasy baseball analysis

These scripts help value and rank players in ESPN and Yahoo fantasy baseball head to head categories league. League settings are configurable, including the categories.

See the [introduction](INTRO.md) for details on the valuation model.

The category valuations are applied against rest-of-season projections from Fangraphs to calculate a cumulative winning probability added for the players.

## Before each season

### Fangraphs

Fangraphs has changed their form data in the past. Verify that the existing form data works for the current season.

* Fangraphs form data should be saved as `config/projections.viewstate` and `config/leaderboard.viewstate`.
* Note: if updating this form data is too time-consuming, just save response data into the projections directory.

### Yahoo

1. Update `config.json` in Yahoo league data directory.

### ESPN

1. Update configuration file by making a copy of `config.py.sample`, renaming to `config.py`, and filling out the configuration.
    * Update:
        * `CURRENT_YEAR`
        * `season_final_day`
        * `BATTER_BUDGET_RATIO`
            * Traditionally, this is set to around 0.66 (i.e. 33% to pitchers)
            * In 2018, the actual ratio was 0.68

## Preparing for a draft

1. `scrape_fangraphs.py --draft`
    * Scrape the pre-season projections from Fangraphs. The projection system used is configurable.
1. Update player information in each league.
    * ESPN: `scrape_player_info`.
1. `map_players.py`
    * TODO: update this script

### Yahoo

### ESPN

1. Update keepers list under `data/keepers.csv`.
1. `python batter_valuation.py --draft`
1. `python pitcher_valuation.py --draft`

## Each week / scoring period

To gather fresh data:

1. `scrape_playing_time.py`
    * Scrape the number of PA / IP for each player in the past 14 days.
1. `scrape_fangraphs.py`
    * Scrape the rest-of-season projections from Fangraphs. The projection system used is configurable.
1. `map_players.py`
    * Each data source uses different names and ids for players. This creates a mapping table that translates between different ids from different systems.

In general, we want to update league specific information and valuations next.
1. Update rosters.
    * We want to have current rosters for each team, and positional eligiblities to make positional adjustments for players. This is different for each league, so we store this in a league-specific data directory.
1. Scrape the most recent scores.
    * After each scoring period, we'll have additional information on the relative value of each category. (For example, if SB have been low this season, the value of an individual SB will likely increase.)
1. Update the category valuations.
1. Update player valuations.

### Yahoo

1. For Yahoo leagues, to update positional eligibility and team rosters:
    ```python
    yahoo = Yahoo("example_league_data_directory")
    yahoo.refresh_rosters()
    yahoo.refresh_eligibilities()
    ```
1. Call `refresh_scores` with the week number you want scores for.
    ```python
    yahoo.refresh_scores(week_number)
    ```
1. Update category valuations.
    * TODO: Implement this.
1. Update player valuations.
    ```python
    yahoo.load_players()
    yahoo.output_valuations()
    ```

### ESPN

1. For ESPN leagues, to update positional eligibility and team rosters:
    ```python
    espn = league.Espn("example_league_data_directory")
    espn.scrape_player_info()
    ```
1. TODO: ESPN changed their interface, so this won't work anymore. `scrape_scores.py`
    * Update head to head results from the latest week.
1. `prob_added.py`
    * Update the logistic regression.
1. Update player valuations.
    * `batter_valuation.py`
    * `pitcher_valuation.py`
