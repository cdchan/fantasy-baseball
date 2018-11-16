# Introduction to fantasy baseball

In fantasy baseball, the goal is to assemble a team of MLB players that will accumulate more statistics than other teams in your group ("league"). See [Wikiepdia](https://en.wikipedia.org/wiki/Fantasy_baseball) for a comprehensive overview of fantasy baseball.

# Head to head categories

I play in a specific version of fantasy baseball where the contests between teams is a weekly matchup ("head to head"). The "score" of each matchup is determined by which team had the better statistics in each of a set number of categories. For example, there may be 5 categories related to batting:

* AVG (batting average)
* R (runs)
* RBI (runs batted in)
* HR (home runs)
* SB (stolen bases)

After a matchup is complete, the team totals are calculated. Whichever team has the highest accumulated statistic of a category wins that category. Let's say the following was the result of a matchup between team A and team B:

* AVG: team A = .300; team B = .245
* R: team A = 45; team B = 50
* RBI: team A = 50; team B = 55
* HR: team A = 25; team B = 20
* SB: team A = 10; team B = 5

Therefore, team A wins AVG, HR, and SB, while team B wins R, and RBI.

# My project

The goal of this project is to rank and value players by how well they contribute to the goal of winning a matchup. The approach I've taken is to gather historical data from my league over the past few years about how teams have won matchups and the stats needed to win.

## Logistic regression

Each matchup and category can be thought of as a win or a loss (1 or 0). This can be modeled with a logistic regression.

For each category, I fit a logistic regression, and determine what the base level is for each category so that a team would be expected to win 50% of their matchups. Then I perturb that base level by adding an additional unit and use the logistic regression to determine the new win probability. The new win probability minus the base win probability is the win probability added for an additional unit of that category.

For example, let's say that if a team has 40 runs, they have a 50% chance of winning runs that week. I then add an additional run so that the total is now 41 runs. If the win probability from the logistic regression is now 52%, then the additional run added 2% of win probability.

With this win probability added for each category, I apply these weights to each player's individual statistics to calculate how much win probability they individually added.

## Projections

Each player is projected to produce a certain stats line. For example, a player might be projected to have a .285 AVG, 80 R, 85 RBI, 15 HR, and 10 SB. With the win probability added weights for each category, I sum up the player's expected total win probability.

Every player is ranked by their total win probability to come up with an ordered list of how valuable each player is. This helps assemble the best players for my team.

# Data sources

For this project, data from ESPN and Fangraphs are integrated. This is why there are so many scripts that scrape data.
