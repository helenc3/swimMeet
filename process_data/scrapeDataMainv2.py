from scrapingUtilsv2 import scrapeOneMeet, getonedayurls, save_meet_data_to_mongodb, TIMEDELTA_BETWEEN_GAMES
from mongodb_helper import connect_to_mongodb
from createswimmerprofsutils import OFFICIAL_COLLECTION_NAME
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import date, timedelta
import re
import sys

CONFERENCES = ["CVC"]

def prompt_date_range():
    """
    Prompts user for date range. Default is 2 days ago (TIMEDELTA_BETWEEN_GAMES).
    If user hits enter, uses default. Type "skip" or "none" to skip date range scraping.
    Otherwise expects format: YYYY-MM-DD to YYYY-MM-DD
    
    Returns:
        tuple: (start_date, end_date) as date objects, or (None, None) if skipping
    """
    default_date = date.today() - timedelta(days=TIMEDELTA_BETWEEN_GAMES)
    
    print(f"\nDate Range Selection:")
    print(f"Default: {default_date} to {default_date} (2 days ago)")
    print(f"Type 'skip' or 'none' to skip date range scraping")
    user_input = input("Enter date range (YYYY-MM-DD to YYYY-MM-DD) or press Enter for default: ").strip()
    
    if not user_input:
        # Use default
        return default_date, default_date
    
    # Check if user wants to skip
    if user_input.lower() in ['skip', 'none', 'n']:
        return None, None
    
    # Parse date range
    pattern = re.compile(r'^\s*(\d{4})-(\d{2})-(\d{2})\s+to\s+(\d{4})-(\d{2})-(\d{2})\s*$', re.IGNORECASE)
    match = pattern.match(user_input)
    
    if not match:
        print(f"Invalid format. Using default: {default_date} to {default_date}")
        return default_date, default_date
    
    try:
        start_date = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        end_date = date(int(match.group(4)), int(match.group(5)), int(match.group(6)))
        
        if start_date > end_date:
            print("Start date must be before or equal to end date. Using default.")
            return default_date, default_date
        
        return start_date, end_date
    except ValueError as e:
        print(f"Invalid date: {e}. Using default: {default_date} to {default_date}")
        return default_date, default_date

def prompt_additional_urls():
    """
    Prompts user for additional URLs to scrape.
    User can enter multiple URLs separated by commas.
    
    Returns:
        list: List of URL strings (empty list if none provided)
    """
    print(f"\nAdditional URLs:")
    user_input = input("Enter specific game URLs to scrape (comma-separated) or press Enter to skip: ").strip()
    
    if not user_input:
        return []
    
    # Split by comma and clean up
    urls = [url.strip() for url in user_input.split(',') if url.strip()]
    return urls

if __name__ == "__main__":
    # Prompt for date range
    start_date, end_date = prompt_date_range()
    
    # Prompt for additional URLs
    additional_urls = prompt_additional_urls()
    
    # Check if we have anything to scrape
    if start_date is None and not additional_urls:
        print("No date range or additional URLs provided. Exiting.")
        sys.exit(0)
    
    if start_date is not None:
        print(f"Scraping from {start_date} to {end_date}")
    if additional_urls:
        print(f"Will also scrape {len(additional_urls)} additional URL(s)")
    
    # Connect to MongoDB
    client, db = connect_to_mongodb()
    collection = db[OFFICIAL_COLLECTION_NAME]
    
    # Optimized Chrome options for faster scraping
    chrome_options = Options()
    
    # Disable images - HUGE speed boost
    prefs = {
        "profile.managed_default_content_settings.images": 2,  # Block images
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Performance optimizations
    chrome_options.add_argument("--disable-images")  # Don't load images
    chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    chrome_options.add_argument("--disable-extensions")  # Disable extensions
    chrome_options.add_argument("--disable-plugins")  # Disable plugins
    chrome_options.add_argument("--disable-logging")  # Disable verbose logging
    chrome_options.add_argument("--log-level=3")  # Only show errors (0=info, 3=errors only)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Less overhead
    chrome_options.add_argument("--disable-popup-blocking")
    
    # Page load strategy - don't wait for all resources to load
    chrome_options.page_load_strategy = "eager"  # Loads when DOM is ready, not all resources
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # Collect all URLs to scrape
    all_urls_to_scrape = []
    
    # Get URLs from date range (if provided)
    if start_date is not None:
        current_date = start_date
        while current_date <= end_date:
            print(f"Getting URLs for date: {current_date}")
            game_urls = getonedayurls(driver, current_date, CONFERENCES)
            if game_urls:
                # Store with date for later use
                for url in game_urls:
                    all_urls_to_scrape.append((url, current_date))
            current_date += timedelta(days=1)
    
    # Add additional URLs (use end_date if available, otherwise use today)
    url_date = end_date if end_date is not None else date.today()
    for url in additional_urls:
        all_urls_to_scrape.append((url, url_date))
    
    print(f"\nTotal URLs to scrape: {len(all_urls_to_scrape)}")
    
    if not all_urls_to_scrape:
        print("No URLs to scrape. Exiting.")
        driver.quit()
        client.close()
        sys.exit(0)
    
    # Scrape all URLs
    for url, url_date in all_urls_to_scrape:
        print(f"\nScraping: {url}")
        driver.get(url)
        data = scrapeOneMeet(driver, url_date)
        if data and data.get("data"):
            stats = save_meet_data_to_mongodb(data.get("data"), collection)
            print(f"Meet stats: {stats}")
        else:
            print("No data to save")
    
    driver.quit()
    client.close()

