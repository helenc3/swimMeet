from scrapingUtils import openpage_signin, chooseOtherSzn, get_divisions, chooseDivision, clickOneTeam, getRoster, scrapeDataForOneSwimmer
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


openpage_signin(driver)

# choose season
starty, endy, szn = prompt_season()
if season_cutoff_has_passed(endy):
    chooseOtherSzn(driver, szn)

os.makedirs(f"data/{szn}", exist_ok=True)

#choose division
divisions = get_divisions(driver)
div = prompt_division(divisions)
teams = chooseDivision(driver, div)

## if you would like to pop items; pop it here. THIS IS IMPORTANT
##teams.pop('Hightstown')
##teams.pop('Hopewell Valley')
##teams.pop('Princeton')


for team in teams:
    driver.get(teams[team])

    # ensure team directory exists
    os.makedirs(f"data/{szn}/{team}", exist_ok=True)

    # if getRoster returns an iterator/zip, make it reusable
    roster = list(getRoster(driver, team))

    # write roster.csv (no mkdir for a file)
    with open(f"data/{szn}/{team}/roster.csv", "w", encoding="utf-8", newline="") as f:
        f.write("name,link\n")
        for name, link in roster:
            f.write(f'"{name}","{link}"\n')

    # ensure swimmers directory exists
    os.makedirs(f"data/{szn}/{team}/swimmers", exist_ok=True)

    for name, link in roster:
        swimmer_data = scrapeDataForOneSwimmer(driver, link, name)
        # sanitize filename (spaces → _, remove illegal chars)
        safe = re.sub(r'[\\/:"*?<>|]+', "_", name).strip().replace(" ", "_")
        
        # Create folder for each swimmer
        swimmer_dir = f"data/{szn}/{team}/swimmers/{safe}"
        os.makedirs(swimmer_dir, exist_ok=True)
        
        # Write nj.com data to njcom.json
        with open(f"{swimmer_dir}/njcom.json", "w", encoding="utf-8") as f:
            json.dump(swimmer_data, f, ensure_ascii=False, indent=2)
        print(f"Saved nj.com data for {name}")

    print(f"Finished scraping data for team {team}")






