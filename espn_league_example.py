"""
EXAMPLE: My personal ESPN league
"""
from espn import Espn

def main():
    x = Espn("my_espn_league_directory")
    x.save_eligibilities()


if __name__ == '__main__':
    main()
