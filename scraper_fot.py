#!/usr/bin/env python3
"""
FotMob Unified Scraper - Coordinator Script
Fetches data once from FotMob and runs all scrapers
"""

import requests
import json
from bs4 import BeautifulSoup as bs
import pandas as pd
import os
import time
from datetime import datetime
from pathlib import Path
import re


# ============================================================================
# MODIFIED SCORER FUNCTIONS (from scorer.py)
# ============================================================================

def process_scorer_data(json_data, soup, url, team_type='home'):
    """Modified version of fetch_match_data that uses pre-fetched data"""
    try:
        # Navigate to team goals based on team_type
        if team_type == 'home':
            goals_data = json_data['props']['pageProps']['header']['events']['homeTeamGoals']
        else:  # away
            goals_data = json_data['props']['pageProps']['header']['events']['awayTeamGoals']

        goal_scorers = list(goals_data.keys())
        print(f"{team_type.capitalize()} team goals found: {goal_scorers}")
        return goal_scorers

    except KeyError as e:
        print(f"Could not find {team_type} team goals data. Key error: {e}")
        print(f"This might be a 0-0 game or the data structure is different for {team_type} team")
        return []
    except Exception as e:
        print(f"Unexpected error for {team_type} team: {e}")
        return []


def save_goals_to_csv(goal_scorers, match_url, csv_filename, team_type):
    """Save goal scorers to CSV file with match information"""
    if not goal_scorers:
        print(f"No goals to save for {team_type} team in this match")
        goal_scorers = ['No goals']

    current_match_data = []
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for scorer in goal_scorers:
        current_match_data.append({
            'timestamp': timestamp,
            'match_url': match_url,
            'goal_scorer': scorer,
        })

    df_current = pd.DataFrame(current_match_data)
    df_current.to_csv(csv_filename, index=False)
    print(f"{team_type.capitalize()} team goals saved to {csv_filename}")
    return df_current


def process_goal_scorers_from_data(json_data, url, team_type='home'):
    """Process goal scorer details using pre-fetched data"""
    try:
        match_round = json_data['props']['pageProps']['general']['matchRound']

        if team_type == 'home':
            team_id = json_data['props']['pageProps']['general']['homeTeam']['id']
            team_goals = json_data['props']['pageProps']['header']['events']['homeTeamGoals']
        else:  # away
            team_id = json_data['props']['pageProps']['general']['awayTeam']['id']
            team_goals = json_data['props']['pageProps']['header']['events']['awayTeamGoals']

        all_dataframes = []

        for scorer in team_goals.keys():
            scorer_data = team_goals[scorer]

            if isinstance(scorer_data, dict):
                scorer_df = pd.DataFrame([scorer_data])
            elif isinstance(scorer_data, list):
                scorer_df = pd.DataFrame(scorer_data)
            else:
                scorer_df = pd.DataFrame({'value': [scorer_data]})

            scorer_df['goal_scorer'] = scorer
            scorer_df['matchRound'] = match_round

            if team_type == 'home':
                scorer_df['HomeTeamId'] = team_id
            else:
                scorer_df['AwayTeamId'] = team_id

            all_dataframes.append(scorer_df)

        if all_dataframes:
            final_df = pd.concat(all_dataframes, ignore_index=True)
            return final_df
        return None

    except Exception as e:
        print(f"Error processing goal scorers for {team_type} team: {str(e)}")
        return None


def run_scorer_scraper(json_data, soup, url):
    """Run the scorer scraper logic using pre-fetched data"""
    print("\n" + "=" * 60)
    print("RUNNING SCORER SCRAPER")
    print("=" * 60)

    for team_type in ['home', 'away']:
        print(f"\n=== PROCESSING {team_type.upper()} TEAM ===")
        print("-" * 50)

        # Define file paths
        if team_type == 'home':
            list_players_csv = r'C:\Users\Public\Documents\Axel\wcup26\goals\csv\listHomePlayers.csv'
            scorers_csv = r'C:\Users\Public\Documents\Axel\wcup26\goals\csv\homeScorers.csv'
        else:            
            list_players_csv = r'C:\Users\Public\Documents\Axel\wcup26\goals\csv\listAwayPlayers.csv'
            scorers_csv = r'C:\Users\Public\Documents\Axel\wcup26\goals\csv\awayScorers.csv'

        # Process goal scorers
        goal_scorers = process_scorer_data(json_data, soup, url, team_type)

        if goal_scorers:
            save_goals_to_csv(goal_scorers, url, list_players_csv, team_type)

            # Process detailed scorer data
            scorer_df = process_goal_scorers_from_data(json_data, url, team_type)
            if scorer_df is not None:
                # Save to CSV
                if os.path.exists(scorers_csv):
                    scorer_df.to_csv(scorers_csv, mode='a', header=False, index=False)
                    print(f"{team_type.capitalize()} team data appended to {scorers_csv}")
                else:
                    scorer_df.to_csv(scorers_csv, index=False)
                    print(f"New file created: {scorers_csv}")


# ============================================================================
# MODIFIED MATCH STATS FUNCTIONS (from match_stats.py)
# ============================================================================

def run_match_stats_scraper(json_data, soup, url):
    """Run the match stats scraper logic using pre-fetched data"""
    print("\n" + "=" * 60)
    print("RUNNING MATCH STATS SCRAPER")
    print("=" * 60)

    try:
        # Extract all the data
        match_data = {
            'matchId': json_data['props']['pageProps']['general']['matchId'],
            'matchRound': json_data['props']['pageProps']['general']['matchRound'],
            'homeTeamName': json_data['props']['pageProps']['general']['homeTeam']['name'],
            'homeTeamid': json_data['props']['pageProps']['general']['homeTeam']['id'],
            'awayTeamName': json_data['props']['pageProps']['general']['awayTeam']['name'],
            'awayTeamid': json_data['props']['pageProps']['general']['awayTeam']['id'],
            'home_goals': json_data['props']['pageProps']['header']['teams'][0]['score'],
            'away_goals': json_data['props']['pageProps']['header']['teams'][1]['score']
        }

        # Extract detailed stats
        stats = json_data['props']['pageProps']['content']['stats']['Periods']['All']['stats']

        # Safe extraction helper
        def safe_extract(path_indices):
            try:
                result = stats
                for idx in path_indices:
                    result = result[idx]
                return result
            except (KeyError, IndexError, TypeError):
                return None

        # Extract all stats with safe fallbacks
        match_data.update({
            'ball_possession_home': safe_extract([0, 'stats', 0, 'stats', 0]),
            'ball_possession_away': safe_extract([0, 'stats', 0, 'stats', 1]),
            'big_chances_home': safe_extract([0, 'stats', 4, 'stats', 0]),
            'big_chances_away': safe_extract([0, 'stats', 4, 'stats', 1]),
            'big_chances_missed_home': safe_extract([0, 'stats', 5, 'stats', 0]),
            'big_chances_missed_away': safe_extract([0, 'stats', 5, 'stats', 1]),
            'fouls_home': safe_extract([0, 'stats', 7, 'stats', 0]),
            'fouls_away': safe_extract([0, 'stats', 7, 'stats', 1]),
            'corners_home': safe_extract([0, 'stats', 8, 'stats', 0]),
            'corners_away': safe_extract([0, 'stats', 8, 'stats', 1]),
            'total_shots_home': safe_extract([1, 'stats', 1, 'stats', 0]),
            'total_shots_away': safe_extract([1, 'stats', 1, 'stats', 1]),
            'shots_off_target_home': safe_extract([1, 'stats', 2, 'stats', 0]),
            'shots_off_target_away': safe_extract([1, 'stats', 2, 'stats', 1]),
            'shots_on_target_home': safe_extract([1, 'stats', 3, 'stats', 0]),
            'shots_on_target_away': safe_extract([1, 'stats', 3, 'stats', 1]),
            'blocked_shots_home': safe_extract([1, 'stats', 4, 'stats', 0]),
            'blocked_shots_away': safe_extract([1, 'stats', 4, 'stats', 1]),
            'hit_woodwork_home': safe_extract([1, 'stats', 5, 'stats', 0]),
            'hit_woodwork_away': safe_extract([1, 'stats', 5, 'stats', 1]),
            'shots_inside_box_home': safe_extract([1, 'stats', 6, 'stats', 0]),
            'shots_inside_box_away': safe_extract([1, 'stats', 6, 'stats', 1]),
            'shots_outside_box_home': safe_extract([1, 'stats', 7, 'stats', 0]),
            'shots_outside_box_away': safe_extract([1, 'stats', 7, 'stats', 1]),
            'xG_home': safe_extract([2, 'stats', 1, 'stats', 0]),
            'xG_away': safe_extract([2, 'stats', 1, 'stats', 1]),
            'xG_open_play_home': safe_extract([2, 'stats', 2, 'stats', 0]),
            'xG_open_play_away': safe_extract([2, 'stats', 2, 'stats', 1]),
            'xG_set_play_home': safe_extract([2, 'stats', 3, 'stats', 0]),
            'xG_set_play_away': safe_extract([2, 'stats', 3, 'stats', 1]),
            'xG_non_penalty_home': safe_extract([2, 'stats', 4, 'stats', 0]),
            'xG_non_penalty_away': safe_extract([2, 'stats', 4, 'stats', 1]),
            'xGOT_home': safe_extract([2, 'stats', 5, 'stats', 0]),
            'xGOT_away': safe_extract([2, 'stats', 5, 'stats', 1]),
            'passes_home': safe_extract([3, 'stats', 1, 'stats', 0]),
            'passes_away': safe_extract([3, 'stats', 1, 'stats', 1]),
            'accurate_passes_home': safe_extract([3, 'stats', 2, 'stats', 0]),
            'accurate_passes_away': safe_extract([3, 'stats', 2, 'stats', 1]),
            'own_half_passes_home': safe_extract([3, 'stats', 3, 'stats', 0]),
            'own_half_passes_away': safe_extract([3, 'stats', 3, 'stats', 1]),
            'opposition_half_passes_home': safe_extract([3, 'stats', 4, 'stats', 0]),
            'opposition_half_passes_away': safe_extract([3, 'stats', 4, 'stats', 1]),
            'accurate_long_passes_home': safe_extract([3, 'stats', 5, 'stats', 0]),
            'accurate_long_passes_away': safe_extract([3, 'stats', 5, 'stats', 1]),
            'accurate_crosses_home': safe_extract([3, 'stats', 6, 'stats', 0]),
            'accurate_crosses_away': safe_extract([3, 'stats', 6, 'stats', 1]),
            'throws_home': safe_extract([3, 'stats', 7, 'stats', 0]),
            'throws_away': safe_extract([3, 'stats', 7, 'stats', 1]),
            'touches_opp_box_home': safe_extract([3, 'stats', 8, 'stats', 0]),
            'touches_opp_box_away': safe_extract([3, 'stats', 8, 'stats', 1]),
            'offsides_home': safe_extract([3, 'stats', 9, 'stats', 0]),
            'offsides_away': safe_extract([3, 'stats', 9, 'stats', 1]),
            'tackles_won_home': safe_extract([4, 'stats', 1, 'stats', 0]),
            'tackles_won_away': safe_extract([4, 'stats', 1, 'stats', 1]),
            'interceptions_home': safe_extract([4, 'stats', 2, 'stats', 0]),
            'interceptions_away': safe_extract([4, 'stats', 2, 'stats', 1]),
            'blocks_home': safe_extract([4, 'stats', 3, 'stats', 0]),
            'blocks_away': safe_extract([4, 'stats', 3, 'stats', 1]),
            'clearances_home': safe_extract([4, 'stats', 4, 'stats', 0]),
            'clearances_away': safe_extract([4, 'stats', 4, 'stats', 1]),
            'keeper_saves_home': safe_extract([4, 'stats', 5, 'stats', 0]),
            'keeper_saves_away': safe_extract([4, 'stats', 5, 'stats', 1]),
            'duel_won_home': safe_extract([5, 'stats', 1, 'stats', 0]),
            'duel_won_away': safe_extract([5, 'stats', 1, 'stats', 1]),
            'ground_duels_won_home': safe_extract([5, 'stats', 2, 'stats', 0]),
            'ground_duels_won_away': safe_extract([5, 'stats', 2, 'stats', 1]),
            'aerial_won_home': safe_extract([5, 'stats', 3, 'stats', 0]),
            'aerial_won_away': safe_extract([5, 'stats', 3, 'stats', 1]),
            'dribbles_succeeded_home': safe_extract([5, 'stats', 4, 'stats', 0]),
            'dribbles_succeeded_away': safe_extract([5, 'stats', 4, 'stats', 1]),
            'yellow_cards_home': safe_extract([6, 'stats', 1, 'stats', 0]),
            'yellow_cards_away': safe_extract([6, 'stats', 1, 'stats', 1]),
            'red_cards_home': safe_extract([6, 'stats', 2, 'stats', 0]),
            'red_cards_away': safe_extract([6, 'stats', 2, 'stats', 1])
        })

        # Create DataFrame
        df = pd.DataFrame([match_data])

        # Save to CSV
        csv_filename = r'C:\Users\Public\Documents\Axel\wcup26\matchStats\csv\fotmob_match_stats.csv'

        if os.path.exists(csv_filename):
            df.to_csv(csv_filename, mode='a', header=False, index=False)
            print(f"Data appended to existing file: {csv_filename}")
        else:
            df.to_csv(csv_filename, mode='w', header=True, index=False)
            print(f"New file created: {csv_filename}")

        print(f"Match data for {match_data['homeTeamName']} vs {match_data['awayTeamName']} saved successfully!")

    except Exception as e:
        print(f"Error in match stats scraper: {e}")


# ============================================================================
# MODIFIED PLAYER STATS FUNCTIONS (from player_stats.py)
# ============================================================================

def extract_stat_value_by_category(stats_list, category_index, stat_key, sub_key='value'):
    """Extract a specific stat value from a specific category in the nested stats structure"""
    if not stats_list or not isinstance(stats_list, list):
        return None
    if category_index >= len(stats_list):
        return None
    category = stats_list[category_index]
    if isinstance(category, dict) and 'stats' in category:
        if stat_key in category['stats']:
            stat_info = category['stats'][stat_key].get('stat', {})
            return stat_info.get(sub_key, None)
    return None


def extract_match_name_from_url(url):
    """Extract match name from FotMob URL"""
    pattern = r'/matches/([^/]+)/'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    else:
        parts = url.split('/')
        for part in parts:
            if 'vs' in part or '-' in part:
                return part.split('#')[0]
    return "match_data"


def get_unique_filename(directory, base_filename):
    """Generate a unique filename by adding a number suffix if the file already exists"""
    name, ext = os.path.splitext(base_filename)
    full_path = os.path.join(directory, base_filename)
    if not os.path.exists(full_path):
        return base_filename

    counter = 1
    while True:
        new_filename = f"{name}-{counter}{ext}"
        new_full_path = os.path.join(directory, new_filename)
        if not os.path.exists(new_full_path):
            return new_filename
        counter += 1


def run_player_stats_scraper(json_data, soup, url):
    """Run the player stats scraper logic using pre-fetched data"""
    print("\n" + "=" * 60)
    print("RUNNING PLAYER STATS SCRAPER")
    print("=" * 60)

    try:
        # Extract match information
        match_info = {
            'matchId': json_data['props']['pageProps']['general']['matchId'],
            'matchRound': json_data['props']['pageProps']['general']['matchRound'],
            'homeTeamName': json_data['props']['pageProps']['general']['homeTeam']['name'],
            'homeTeamid': json_data['props']['pageProps']['general']['homeTeam']['id'],
            'awayTeamName': json_data['props']['pageProps']['general']['awayTeam']['name'],
            'awayTeamid': json_data['props']['pageProps']['general']['awayTeam']['id'],
            'matchDate': json_data['props']['pageProps']['general']['matchTimeUTCDate'],
            'home_goals': json_data['props']['pageProps']['header']['teams'][0]['score'],
            'away_goals': json_data['props']['pageProps']['header']['teams'][1]['score']
        }

        # Create DataFrame
        df_players = pd.DataFrame(json_data['props']['pageProps']['content']['playerStats'])
        df_players_T = df_players.T
        df_players_T.reset_index(drop=True, inplace=True)
        df_players_T = df_players_T.drop(['shotmap', 'funFacts', 'isPotm'], axis=1, errors='ignore')

        # Add match information columns
        for key, value in match_info.items():
            df_players_T[key] = value

        # Define all stats to extract
        existing_stats = [
            ('FotMob rating', 'FotMob_rating', 'value'),
            ('Minutes played', 'Minutes_played', 'value'),
            ('Goals', 'Goals', 'value'),
            ('Assists', 'Assists', 'value'),
            ('Total shots', 'Total_shots', 'value'),
            ('Accurate passes', 'Accurate_passes_value', 'value'),
            ('Accurate passes', 'Accurate_passes_total', 'total'),
            ('Chances created', 'Chances_created', 'value'),
            ('Expected assists (xA)', 'Expected_assists_xA', 'value'),
            ('xG + xA', 'xG_plus_xA', 'value'),
            ('Fantasy points', 'Fantasy_points', 'value'),
            ('Defensive actions', 'Defensive_actions', 'value')
        ]

        new_stats = [
            (1, 'Touches', 'touches', 'value'),
            (1, 'Touches in opposition box', 'touches_opp_box', 'value'),
            (1, 'Passes into final third', 'passes_into_final_third', 'value'),
            (1, 'Accurate crosses', 'accurate_crosses_value', 'value'),
            (1, 'Accurate crosses', 'accurate_crosses_total', 'total'),
            (1, 'Accurate long balls', 'long_balls_accurate_value', 'value'),
            (1, 'Accurate long balls', 'long_balls_accurate_total', 'total'),
            (1, 'Dispossessed', 'dispossessed', 'value'),
            (2, 'Tackles won', 'tackles_succeeded_value', 'value'),
            (2, 'Tackles won', 'tackles_succeeded_total', 'total'),
            (2, 'Blocks', 'shot_blocks', 'value'),
            (2, 'Clearances', 'clearances', 'value'),
            (2, 'Headed clearance', 'headed_clearance', 'value'),
            (2, 'Interceptions', 'interceptions', 'value'),
            (2, 'Recoveries', 'recoveries', 'value'),
            (2, 'Dribbled past', 'dribbled_past', 'value'),
            (3, 'Duels won', 'duel_won', 'value'),
            (3, 'Duels lost', 'duel_lost', 'value'),
            (3, 'Ground duels won', 'ground_duels_won_value', 'value'),
            (3, 'Ground duels won', 'ground_duels_won_total', 'total'),
            (3, 'Aerial duels won', 'aerials_won_value', 'value'),
            (3, 'Aerial duels won', 'aerials_won_total', 'total'),
            (3, 'Was fouled', 'fouls_received', 'value'),
            (3, 'Fouls committed', 'fouls_committed', 'value')
        ]

        # Extract stats
        for stat_key, column_name, sub_key in existing_stats:
            df_players_T[column_name] = df_players_T['stats'].apply(
                lambda x: extract_stat_value_by_category(x, 0, stat_key, sub_key)
            )

        for category_index, stat_key, column_name, sub_key in new_stats:
            df_players_T[column_name] = df_players_T['stats'].apply(
                lambda x: extract_stat_value_by_category(x, category_index, stat_key, sub_key)
            )

        # Save to CSV
        match_name = extract_match_name_from_url(url)
        base_csv_filename = f"{match_name}.csv"
        csv_directory = r'C:\Users\Public\Documents\Axel\wcup26\playerStats\csv\\'
        os.makedirs(csv_directory, exist_ok=True)

        unique_csv_filename = get_unique_filename(csv_directory, base_csv_filename)
        csv_path = os.path.join(csv_directory, unique_csv_filename)

        df_players_T.to_csv(csv_path, index=False)
        print(f"Player stats saved to: {csv_path}")
        print(f"Shape of saved DataFrame: {df_players_T.shape}")

    except Exception as e:
        print(f"Error in player stats scraper: {e}")


# ============================================================================
# MODIFIED SHOTS FUNCTIONS (from shots.py)
# ============================================================================

def run_shots_scraper(json_data, soup, url):
    """Run the shots scraper logic using pre-fetched data"""
    print("\n" + "=" * 60)
    print("RUNNING SHOTS SCRAPER")
    print("=" * 60)

    try:
        # Extract match metadata
        general = json_data['props']['pageProps']['general']
        header = json_data['props']['pageProps']['header']
        content = json_data['props']['pageProps']['content']

        match_data = {
            'matchId': general['matchId'],
            'matchRound': general['matchRound'],
            'homeTeamName': general['homeTeam']['name'],
            'homeTeamId': general['homeTeam']['id'],
            'awayTeamName': general['awayTeam']['name'],
            'awayTeamId': general['awayTeam']['id'],
            'matchDate': general['matchTimeUTCDate'],
            'home_goals': header['teams'][0]['score'],
            'away_goals': header['teams'][1]['score']
        }

        # Create DataFrame from shots data
        df_shots = pd.DataFrame(content['shotmap']['shots'])

        # Add match metadata to each row
        for key, value in match_data.items():
            df_shots[key] = value

        # Reorder columns
        metadata_cols = list(match_data.keys())
        shot_cols = [col for col in df_shots.columns if col not in metadata_cols]
        df_shots = df_shots[metadata_cols + shot_cols]

        # Save to CSV
        match_name = extract_match_name_from_url(url)
        csv_directory = r'C:\Users\Public\Documents\Axel\wcup26\shots\csv\\'
        os.makedirs(csv_directory, exist_ok=True)

        base_filename = f"{match_name}.csv"
        unique_filename = get_unique_filename(csv_directory, base_filename)
        output_path = os.path.join(csv_directory, unique_filename)

        df_shots.to_csv(output_path, index=False)
        print(f"Shots data saved to: {output_path}")
        print(f"Total shots recorded: {len(df_shots)}")

    except Exception as e:
        print(f"Error in shots scraper: {e}")


# ============================================================================
# MAIN COORDINATOR FUNCTION
# ============================================================================

def main():
    """
    Main coordinator function that fetches data once and runs all scrapers
    """
    print("=" * 60)
    print("FOTMOB UNIFIED SCRAPER")
    print("=" * 60)

    # Get URL input
    url_input = input('\nEnter FotMob match URL: ').strip()

    if not url_input:
        print("Please enter a valid URL")
        return

    print(f"\nFetching data from: {url_input}")
    print("=" * 60)

    try:
        # FETCH DATA ONCE
        print("\nFetching match data from FotMob...")
        r = requests.get(url_input)
        r.raise_for_status()

        # Parse HTML
        soup = bs(r.content, 'html.parser')

        # Extract JSON data
        json_script = soup.find('script', attrs={'id': '__NEXT_DATA__'})
        if not json_script:
            raise ValueError("Could not find __NEXT_DATA__ script in the page")

        json_data = json.loads(json_script.contents[0])
        print("Data fetched successfully!")

        # Display match info
        match_info = json_data['props']['pageProps']['general']
        print(f"\nMatch: {match_info['homeTeam']['name']} vs {match_info['awayTeam']['name']}")
        print(f"Round: {match_info['matchRound']}")
        print(f"Date: {match_info['matchTimeUTCDate']}")

        # RUN ALL SCRAPERS WITH THE SAME DATA

        # 1. Run Scorer Scraper
        run_scorer_scraper(json_data, soup, url_input)
        time.sleep(0.5)  # Small delay between scrapers

        # 2. Run Match Stats Scraper
        run_match_stats_scraper(json_data, soup, url_input)
        time.sleep(0.5)

        # 3. Run Player Stats Scraper
        run_player_stats_scraper(json_data, soup, url_input)
        time.sleep(0.5)

        # 4. Run Shots Scraper
        run_shots_scraper(json_data, soup, url_input)

        print("\n" + "=" * 60)
        print("ALL SCRAPERS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nFiles created/updated:")
        print("- Goal scorers: listHomePlayers.csv, listAwayPlayers.csv")
        print("- Scorer details: homeScorers.csv, awayScorers.csv")
        print("- Match stats: fotmob_match_stats.csv")
        print("- Player stats: [match-name].csv")
        print("- Shots data: [match-name].csv")

    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON data: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()