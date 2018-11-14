# fantasy-baseball

## Fantasy baseball analysis

These scripts help value and rank players in an ESPN head to head categories league. League settings are configurable, including the categories.

How each category is valued is based on head to head results from previous weeks / seasons. The model uses a logistic regression to find the probability each additional unit (for example, an RBI) provides towards winning that category.

The category valuations are applied against rest-of-season projections from Fangraphs to calculate a cumulative winning probability added for the players.

## Before each season

1. Update configuration file by making a copy of config.py.sample and renaming to config.py.
    * This includes Fangraphs form data and ESPN cookies.

## Each week / scoring period

Run order:

1. scrape_playing_time.py
    * Scrape the number of PA / IP for each player in the past 14 days.
1. scrape_steamer.py
    * Scrape the rest-of-season / pre-season projections from Fangraphs. The projection system used is configurable.
1. scrape_eligibilities.py
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
