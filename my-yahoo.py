"""
EXAMPLE: My personal Yahoo league
"""
import argparse

from yahoo import Yahoo

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--roster", action="store_true", help="refresh rosters")
    parser.add_argument("--elig", action="store_true", help="refresh eligibilities")
    parser.add_argument("--scores", help="refresh matchup scores")
    args = parser.parse_args()

    x = Yahoo("yahoo-new", "rfangraphsdc")

    if args.roster:
        x.refresh_rosters()
    
    if args.elig:
        x.refresh_eligibilities()
    
    if args.scores:
        x.refresh_scores(args.scores)

    x.load_players()
    x.output_valuations()


if __name__ == '__main__':
    main()
