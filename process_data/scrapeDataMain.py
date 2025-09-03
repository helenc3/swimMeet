from scrapingUtils import openpage_signin, chooseOtherSzn, get_divisions, chooseDivision, chooseTeam, scrapeDataForOneSwimmer
from selenium import webdriver
from datetime import date
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
chooseDivision(driver, div)





