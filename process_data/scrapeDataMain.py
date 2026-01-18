from scrapingUtils import openpage_signin, chooseOtherSzn, get_divisions, chooseDivision, clickOneTeam, getRoster, scrapeDataForOneSwimmer
from mongodb_helper import connect_to_mongodb, save_swimmer_to_mongodb
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import date
import json
import os
import re

def prompt_season() -> tuple[int, int]:
    """
    Prompt until user enters a season like '2024-2025' (hyphen or en dash OK),
    with the end year exactly start year + 1. Returns (start_year, end_year).
    """
    pattern = re.compile(r'^\s*(\d{4})\s*[-–—]\s*(\d{4})\s*$')
    while True:
        s = input('Enter season (e.g. "2024-2025"): ')
        m = pattern.match(s or "")
        if not m:
            print("Please use format YYYY-YYYY (e.g., 2024-2025).")
            continue
        start_y, end_y = int(m.group(1)), int(m.group(2))
        if end_y != start_y + 1:
            print("End year must be exactly start year + 1 (e.g., 2024-2025).")
            continue
        return start_y, end_y, s
    
def season_cutoff_has_passed(end_year: int) -> bool:
    """Return True iff June 1 of end_year is <= today."""
    return date(end_year, 6, 1) <= date.today()

def prompt_division(divisions):
    while True:
        div = input('Enter Division (e.g. "CVC"): ')
        if div.strip() not in divisions:
            print("Please enter a valid division from the list:", divisions)
            continue
        return div

def prompt_teams(available_teams):
    """
    Prompt user for which teams to scrape.
    Returns a set of team names to scrape.
    If user enters "*", returns None (meaning all teams).
    Otherwise, parses comma-separated team names.
    """
    while True:
        print(f"\nAvailable teams: {', '.join(sorted(available_teams.keys()))}")
        response = input('Enter teams to scrape (use "*" for all, or comma-separated list like "Hightstown, Princeton"): ').strip()
        
        if response == "*":
            return None  # None means scrape all teams
        
        # Parse comma-separated list
        selected_teams = [team.strip() for team in response.split(',')]
        selected_teams = [team for team in selected_teams if team]  # Remove empty strings
        
        if not selected_teams:
            print("Please enter at least one team name or '*' for all teams.")
            continue
        
        # Validate team names
        invalid_teams = [team for team in selected_teams if team not in available_teams]
        if invalid_teams:
            print(f"Invalid team names: {', '.join(invalid_teams)}")
            print(f"Available teams: {', '.join(sorted(available_teams.keys()))}")
            continue
        
        return set(selected_teams)


###################____________________________________________________________

# Optimized Chrome options for faster scraping
chrome_options = Options()

# Disable images - HUGE speed boost (you only extract text, not images)
prefs = {
    "profile.managed_default_content_settings.images": 2,  # Block images
}
chrome_options.add_experimental_option("prefs", prefs)

# Performance optimizations
chrome_options.add_argument("--disable-images")  # Don't load images
chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration
chrome_options.add_argument("--no-sandbox")  # Faster startup
chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
chrome_options.add_argument("--disable-extensions")  # Disable extensions
chrome_options.add_argument("--disable-plugins")  # Disable plugins
chrome_options.add_argument("--disable-logging")  # Disable verbose logging
chrome_options.add_argument("--log-level=3")  # Only show errors (0=info, 3=errors only)
chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Less overhead

# Page load strategy - don't wait for all resources to load
chrome_options.page_load_strategy = "eager"  # Loads when DOM is ready, not all resources

# Note: We keep JavaScript ENABLED because you need it for dropdowns/buttons
# Note: We keep CSS ENABLED because some sites use CSS to show/hide elements

# Uncomment this line to run headless (faster, but you won't see the browser)
# Only do this AFTER manual login, or comment it out during login
# chrome_options.add_argument("--headless")

driver = webdriver.Chrome(options=chrome_options)

# Connect to MongoDB
print("Connecting to MongoDB...")
client, db = connect_to_mongodb()
if not client:
    print("Failed to connect to MongoDB. Exiting.")
    exit(1)
print("✓ Connected to MongoDB!")

openpage_signin(driver)

# choose season
starty, endy, szn = prompt_season()
if season_cutoff_has_passed(endy):
    chooseOtherSzn(driver, szn)

os.makedirs(f"data/njcom/{szn}", exist_ok=True)

#choose division
divisions = get_divisions(driver)
div = prompt_division(divisions)
teams = chooseDivision(driver, div)

# Ask which teams to scrape
selected_teams = prompt_teams(teams)

# Filter teams if specific ones were selected
if selected_teams is not None:
    teams = {team: teams[team] for team in selected_teams if team in teams}
    print(f"\nScraping {len(teams)} team(s): {', '.join(sorted(teams.keys()))}")
else:
    print(f"\nScraping all {len(teams)} teams")

for team in teams:
    driver.get(teams[team])

    # ensure team directory exists
    os.makedirs(f"data/njcom/{szn}/{team}", exist_ok=True)

    # if getRoster returns an iterator/zip, make it reusable
    roster = list(getRoster(driver, team))

    # write roster.csv (no mkdir for a file)
    with open(f"data/njcom/{szn}/{team}/roster.csv", "w", encoding="utf-8", newline="") as f:
        f.write("name,link\n")
        for name, link in roster:
            f.write(f'"{name}","{link}"\n')

    # ensure swimmers directory exists (for roster.csv backup)
    os.makedirs(f"data/njcom/{szn}/{team}/swimmers", exist_ok=True)

    for name, link in roster:
        swimmer_data = scrapeDataForOneSwimmer(driver, link, name)
        
        # Save to MongoDB (merges with existing data, avoids duplicates)
        result = save_swimmer_to_mongodb(db, swimmer_data, year=szn, team=team, source='njcom')
        
        # Also save JSON backup (optional - you can remove this later)
        safe = re.sub(r'[\\/:"*?<>|]+', "_", name).strip().replace(" ", "_")
        with open(f"data/njcom/{szn}/{team}/swimmers/{safe}.json", "w", encoding="utf-8") as f:
            json.dump(swimmer_data, f, ensure_ascii=False, indent=2)
        
        # Print status
        if result['inserted']:
            print(f"✓ Inserted {name} ({result['new_times_count']} times)")
        elif result['new_times_count'] > 0:
            print(f"✓ Updated {name} (added {result['new_times_count']} new times)")
        else:
            print(f"○ Skipped {name} (no new times)")

    print(f"Finished scraping data for team {team}")






