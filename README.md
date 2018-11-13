# fantasy-baseball

Fantasy baseball analysis

## Each season

1. Update configuration file by making a copy of config.py.sample and renaming to config.py.
  * This includes Fangraphs form data and ESPN cookies.

## Each week

Run order:

1. scrape_playing_time.py
1. scrape_steamer.py
1. scrape_eligibilities.py
1. scrape_rosters.py
1. map_players.py

After a scoring period:

1. scrape_scores.py
1. prob_added.py
