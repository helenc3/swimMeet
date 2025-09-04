from scrapingUtils import openpage_signin, chooseOtherSzn, get_divisions, chooseDivision, clickOneTeam, getRoster, scrapeDataForOneSwimmer
from selenium import webdriver
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


driver = webdriver.Chrome()

openpage_signin(driver)

# choose season
starty, endy, szn = prompt_season()
if season_cutoff_has_passed(endy):
    chooseOtherSzn(driver, szn)

#choose division
divisions = get_divisions(driver)
div = prompt_division(divisions)
teams = chooseDivision(driver, div)


#### TODO: run this 
teams.pop("West Windsor-Plainsboro South")  # doesn't have roster link
teams.pop("West Windsor-Plainsboro North")  # doesn't have roster link
teams.pop("Princeton")  # THESE ARE ALL TEMPORARY -- PLEASE DELETE LATER


for team in teams:
    driver.get(teams[team])

    # ensure team directory exists
    os.makedirs(f"data/{team}", exist_ok=True)

    # if getRoster returns an iterator/zip, make it reusable
    roster = list(getRoster(driver, team))

    # write roster.csv (no mkdir for a file)
    with open(f"data/{team}/roster.csv", "w", encoding="utf-8", newline="") as f:
        f.write("name,link\n")
        for name, link in roster:
            f.write(f'"{name}","{link}"\n')

    # ensure swimmers directory exists
    os.makedirs(f"data/{team}/swimmers", exist_ok=True)

    for name, link in roster:
        swimmer_data = scrapeDataForOneSwimmer(driver, link, name)
        # sanitize filename (spaces → _, remove illegal chars)
        safe = re.sub(r'[\\/:"*?<>|]+', "_", name).strip().replace(" ", "_")
        with open(f"data/{team}/swimmers/{safe}.json", "w", encoding="utf-8") as f:
            json.dump(swimmer_data, f, ensure_ascii=False, indent=2)
        print(f"Saved data for {name}")

    print(f"Finished scraping data for team {team}")






