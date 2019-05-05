"""
EXAMPLE: My personal ESPN league
"""
import argparse

from espn import Espn

def main():
    x = Espn("espn-old")
    x.scrape_player_info()


if __name__ == '__main__':
    main()
