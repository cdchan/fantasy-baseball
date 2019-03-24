# fantasy-baseball

## Fantasy baseball analysis

These scripts help value and rank players in an ESPN head to head categories league. League settings are configurable, including the categories.

See the [introduction](INTRO.md) for details on the valuation model.

The category valuations are applied against rest-of-season projections from Fangraphs to calculate a cumulative winning probability added for the players.

## Before each season

1. Update configuration file by making a copy of config.py.sample, renaming to config.py, and filling out the configuration.
    * Update:
        * `CURRENT_YEAR`
        * `season_final_day`
        * `BATTER_BUDGET_RATIO`
            * Traditionally, this is set to around 0.66 (i.e. 33% to pitchers)
            * In 2018, the actual ratio was 0.68
    * This includes Fangraphs form data and ESPN cookies.
    * Fangraphs form data should be saved as `config/viewstate.data` and `config/viewstate-leaderboard.data`.
        * Note: if this is too time-consuming, just save response data into the projections directory.

## Preparing for a draft

1. `scrape_fangraphs.py --draft`
    * Scrape the pre-season projections from Fangraphs. The projection system used is configurable.
1. `scrape_espn_eligibilities.py --draft`
    * Scrape positional eligibilities for players from ESPN. This is needed for positional adjustments.
1. `map_players.py`
    * TODO: update this script
1. `python batter_valuation.py --draft`
1. `python pitcher_valuation.py --draft`


## Each week / scoring period

To gather fresh data:

1. scrape_playing_time.py
    * Scrape the number of PA / IP for each player in the past 14 days.
1. `scrape_fangraphs.py`
    * Scrape the rest-of-season projections from Fangraphs. The projection system used is configurable.
1. `scrape_eligibilities.py`
    * TODO: out of date, needs to be fixed
    * Scrape positional eligibilities for players from ESPN. This is needed for positional adjustments.
1. scrape_rosters.py
    * Scrape the current rosters for each team from ESPN.
1. map_players.py
    * Each data source uses different names and ids for players. This creates a mapping table that translates between different ids from different systems.

After a scoring period:

1. scrape_scores.py
    * Update head to head results from the latest week.
1. prob_added.py
    * Update the logistic regression.

To value players:

1. batter_valuation.py
1. pitcher_valuation.py

