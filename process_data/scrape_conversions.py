"""
Script to scrape Swimming World Magazine time converter and calculate linear conversion equations
for each event and course combination.

Uses 3 test times per event to determine the linear equation: y = mx + b
where y = converted time, x = source course time, m = multiplier, b = offset

Source: https://www.swimmingworldmagazine.com/time-conversion

WARNING: this is a one time use script for reference you dont need it anymore
it has some issues so use at caution
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from time import sleep
import json
from sconeswimmer import parse_time_to_seconds

# Try to import numpy, fallback to manual calculation
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    print("Warning: numpy not found. Using manual linear regression calculation.")

CONVERTER_URL = "https://www.swimmingworldmagazine.com/time-conversion"

# Test times in seconds
TEST_TIMES = [60.0, 120.0, 180.0]  # 1:00, 2:00, 3:00

# Course combinations to test (from_course -> to_course)
# Only convert FROM SCM/LCM TO SCY (the page shows all conversions, we just read SCY)
COURSE_COMBINATIONS = [
    ("LCM", "SCY"),
    ("SCM", "SCY"),
]

# Distance mappings based on course
DISTANCES_SCY = {
    "50": "Fifty",
    "100": "Hundred",
    "200": "TwoHundred",
    "500": "FiveHundred",
    "1000": "Thousand",
    "1650": "SixteenFifty"
}

DISTANCES_SCM_LCM = {
    "50": "Fifty",
    "100": "Hundred",
    "200": "TwoHundred",
    "400": "FourHundred",
    "800": "EightHundred",
    "1500": "FifteenHundred"
}

# Stroke IDs
STROKES = {
    "Free": "Free",
    "Back": "Back",
    "Breast": "Breast",
    "Fly": "Fly",
    "IM": "IM"
}

# Gender IDs
GENDERS = ["M", "F"]

def calculate_linear_equation(x_values, y_values):
    """Calculate linear equation y = mx + b from 3 points using least squares"""
    if len(x_values) != 3 or len(y_values) != 3:
        return None, None
    
    if HAS_NUMPY:
        coeffs = np.polyfit(x_values, y_values, 1)
        multiplier = coeffs[0]
        offset = coeffs[1]
    else:
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        
        denominator = n * sum_x2 - sum_x * sum_x
        if abs(denominator) < 1e-10:
            return None, None
        
        multiplier = (n * sum_xy - sum_x * sum_y) / denominator
        offset = (sum_y - multiplier * sum_x) / n
    
    return multiplier, offset

def enter_time(driver, seconds):
    """Enter time using minutes and seconds fields"""
    minutes = int(seconds // 60)
    secs = seconds % 60
    secs_int = int(secs)
    secs_decimal = int((secs - secs_int) * 100)
    
    try:
        # Re-find elements each time to avoid stale references
        minutes_field = driver.find_element(By.ID, "minutes")
        minutes_field.clear()
        sleep(0.1)  # Small delay after clear
        minutes_field.send_keys(str(minutes))
        
        # Enter seconds (as two digits for seconds, then decimal)
        seconds_field = driver.find_element(By.ID, "seconds")
        seconds_field.clear()
        sleep(0.1)  # Small delay after clear
        # Format as SS.mm
        seconds_field.send_keys(f"{secs_int:02d}.{secs_decimal:02d}")
        sleep(0.1)
    except Exception as e:
        # Retry if stale element
        sleep(0.2)
        minutes_field = driver.find_element(By.ID, "minutes")
        minutes_field.clear()
        minutes_field.send_keys(str(minutes))
        seconds_field = driver.find_element(By.ID, "seconds")
        seconds_field.clear()
        seconds_field.send_keys(f"{secs_int:02d}.{secs_decimal:02d}")
        sleep(0.1)

def safe_click(driver, element):
    """Safely click an element, handling ad overlays and using JavaScript as fallback"""
    try:
        # Try scrolling into view first
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        sleep(0.1)
        
        # Try regular click first
        element.click()
    except Exception:
        # If regular click fails, use JavaScript click
        driver.execute_script("arguments[0].click();", element)

def select_course(driver, course):
    """Click course button (SCY, LCM, or SCM)"""
    course_button = driver.find_element(By.ID, course)
    safe_click(driver, course_button)
    sleep(0.1)

def select_distance(driver, distance_id):
    """Click distance button by ID"""
    try:
        distance_button = driver.find_element(By.ID, distance_id)
        safe_click(driver, distance_button)
        sleep(0.1)
        return True
    except NoSuchElementException:
        return False

def select_stroke(driver, stroke_id):
    """Click stroke button"""
    stroke_button = driver.find_element(By.ID, stroke_id)
    safe_click(driver, stroke_button)
    sleep(0.1)

def select_gender(driver, gender_id):
    """Click gender button (M or F)"""
    gender_button = driver.find_element(By.ID, gender_id)
    safe_click(driver, gender_button)
    sleep(0.1)

def get_converted_time(driver):
    """Get converted time from the SCY result div (always read SCY conversion)"""
    try:
        # Re-find element each time to avoid stale element reference
        result_div = driver.find_element(By.ID, "scyDiv")
        time_text = result_div.text.strip()
        
        # Format is "1:00.00 - SCY" or "- SCY" if no conversion
        # Remove " - SCY" suffix
        if " - SCY" in time_text:
            time_text = time_text.split(" - SCY")[0].strip()
        elif time_text == "- SCY" or time_text == "-":
            return None
        
        # If empty, no conversion available
        if not time_text:
            return None
        
        # Parse the time (format: "1:00.00" or "60.00")
        return parse_time_to_seconds(time_text)
    except Exception as e:
        # Retry once if stale element or other error
        try:
            sleep(0.2)
            result_div = driver.find_element(By.ID, "scyDiv")
            time_text = result_div.text.strip()
            if " - SCY" in time_text:
                time_text = time_text.split(" - SCY")[0].strip()
            elif time_text == "- SCY" or time_text == "-":
                return None
            if not time_text:
                return None
            return parse_time_to_seconds(time_text)
        except:
            return None

def clear_time_fields(driver):
    """Clear both time input fields"""
    try:
        # Re-find elements to avoid stale references
        minutes_field = driver.find_element(By.ID, "minutes")
        minutes_field.clear()
        sleep(0.1)
        seconds_field = driver.find_element(By.ID, "seconds")
        seconds_field.clear()
        sleep(0.2)  # Wait for conversion to reset
    except Exception as e:
        # If clearing fails, try again
        try:
            sleep(0.2)
            minutes_field = driver.find_element(By.ID, "minutes")
            minutes_field.clear()
            seconds_field = driver.find_element(By.ID, "seconds")
            seconds_field.clear()
            sleep(0.2)
        except:
            pass

def get_conversion(driver, from_course, distance_id, stroke_id, gender_id, test_time, is_first_time=False):
    """Get a single conversion result (always converts to SCY)"""
    try:
        # Only set up course/distance/stroke/gender on first time
        # After that, just change the time
        if is_first_time:
            # Select from course (this determines which distance buttons are available)
            select_course(driver, from_course)
            
            # Wait for distance buttons to update based on course
            sleep(0.2)
            
            # Select distance (may need to wait for distance buttons to update)
            if not select_distance(driver, distance_id):
                print(f"        Distance button {distance_id} not found for {from_course}")
                return None
            
            # Select stroke
            select_stroke(driver, stroke_id)
            
            # Select gender
            select_gender(driver, gender_id)
        else:
            # Clear previous time to reset conversion
            clear_time_fields(driver)
        
        # Enter time
        enter_time(driver, test_time)
        
        # Click a button to trigger conversion update (even if already selected)
        # Click the course button again to force recalculation
        select_course(driver, from_course)
        
        # Wait for conversion to calculate after button click
        # Longer wait to ensure DOM has updated
        sleep(0.6)
        
        # Read the conversion NOW (for the time we just entered)
        # This must happen before we enter the next time
        # Retry reading if it fails (might be stale element)
        converted = get_converted_time(driver)
        if converted is None:
            # Retry once more with a bit more wait
            sleep(0.3)
            converted = get_converted_time(driver)
        
        return converted
    except Exception as e:
        print(f"        Error: {e}")
        return None

def get_distances_for_course(course, stroke):
    """Get list of distances to test for a given course and stroke"""
    if stroke == "Free":
        if course == "SCY":
            # SCY Free: 50, 100, 200, 500, 1000, 1650 (no 400, 800, 1500)
            return ["50", "100", "200", "500", "1000", "1650"]
        else:  # SCM or LCM
            # SCM/LCM Free: 50, 100, 200, 400, 800, 1500 (no 500, 1000, 1650)
            return ["50", "100", "200", "400", "800", "1500"]
    elif stroke in ["Back", "Breast", "Fly"]:
        return ["50", "100", "200"]
    elif stroke == "IM":
        return ["200", "400"]
    return []

def get_distance_id(distance, course):
    """Get the HTML ID for a distance button based on course"""
    if course == "SCY":
        return DISTANCES_SCY.get(distance)
    else:
        return DISTANCES_SCM_LCM.get(distance)

def scrape_all_conversions():
    """Main function to scrape all conversions"""
    chrome_options = Options()
    
    # Disable images - HUGE speed boost
    prefs = {
        "profile.managed_default_content_settings.images": 2,  # Block images
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Performance optimizations
    #chrome_options.add_argument("--headless")  # Run without GUI - faster!
    chrome_options.add_argument("--disable-images")  # Don't load images
    chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration
    chrome_options.add_argument("--no-sandbox")  # Faster startup
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    chrome_options.add_argument("--disable-extensions")  # Disable extensions
    chrome_options.add_argument("--disable-plugins")  # Disable plugins
    chrome_options.add_argument("--disable-logging")  # Disable verbose logging
    chrome_options.add_argument("--log-level=3")  # Only show errors
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Less overhead
    
    # Block ads to prevent click interception
    chrome_options.add_argument("--disable-popup-blocking")
    
    # Page load strategy - don't wait for all resources to load
    chrome_options.page_load_strategy = "eager"  # Loads when DOM is ready, not all resources
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print(f"Navigating to {CONVERTER_URL}...")
        driver.get(CONVERTER_URL)
        sleep(2)  # Wait for page to load
        
        # Hide ad elements that might intercept clicks
        try:
            driver.execute_script("""
                // Hide Google ad containers
                var adSelectors = [
                    '[id*="google_ads"]',
                    '[id*="ad"]',
                    '.ad',
                    '.ads',
                    'iframe[src*="google"]'
                ];
                adSelectors.forEach(function(selector) {
                    var elements = document.querySelectorAll(selector);
                    elements.forEach(function(el) {
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                        el.style.opacity = '0';
                        el.style.pointerEvents = 'none';
                    });
                });
            """)
            sleep(0.5)
        except Exception as e:
            print(f"Warning: Could not hide ads: {e}")
        
        results = {}
        
        # Initialize results structure
        for from_course, to_course in COURSE_COMBINATIONS:
            key = f"{from_course}_to_{to_course}"
            results[key] = {}
        
        # Process each course combination
        for from_course, to_course in COURSE_COMBINATIONS:
            print(f"\n{'='*60}")
            print(f"Processing conversions: {from_course} -> {to_course}")
            print(f"{'='*60}")
            
            key = f"{from_course}_to_{to_course}"
            
            # Process each stroke
            for stroke_name, stroke_id in STROKES.items():
                print(f"\n  Stroke: {stroke_name}")
                
                # Get distances for this stroke and course
                distances = get_distances_for_course(from_course, stroke_name)
                if not distances:
                    continue
                
                # Process each distance
                for distance in distances:
                    distance_id = get_distance_id(distance, from_course)
                    if not distance_id:
                        print(f"    Skipping {distance} - no ID mapping")
                        continue
                    
                    print(f"    Distance: {distance}")
                    
                    # Process each gender
                    for gender_id in GENDERS:
                        gender_name = "Male" if gender_id == "M" else "Female"
                        print(f"      Gender: {gender_name}")
                        
                        # Test with 3 times
                        input_times = []
                        output_times = []
                        
                        for time_idx, test_time in enumerate(TEST_TIMES):
                            # First time needs to set up course/distance/stroke/gender
                            # Subsequent times just change the time
                            is_first_time = (time_idx == 0)
                            
                            converted = get_conversion(
                                driver, from_course,
                                distance_id, stroke_id, gender_id, test_time,
                                is_first_time=is_first_time
                            )
                            
                            if converted is not None:
                                input_times.append(test_time)
                                output_times.append(converted)
                                print(f"        {test_time:.2f}s -> {converted:.2f}s")
                            else:
                                print(f"        {test_time:.2f}s -> FAILED")
                            
                            # Small pause after each conversion before next one
                            sleep(0.2)
                        
                        # Calculate linear equation if we have 3 points
                        if len(input_times) == 3 and len(output_times) == 3:
                            multiplier, offset = calculate_linear_equation(input_times, output_times)
                            
                            if multiplier is not None:
                                event_key = f"{distance} {stroke_name}"
                                if event_key not in results[key]:
                                    results[key][event_key] = {}
                                
                                results[key][event_key][gender_name] = {
                                    "type": "linear",
                                    "multiplier": round(multiplier, 6),
                                    "offset": round(offset, 6)
                                }
                                print(f"        Equation: y = {multiplier:.6f}x + {offset:.6f}")
                            else:
                                print(f"        Failed to calculate equation")
                        else:
                            print(f"        Not enough data points (got {len(input_times)}/3)")
        
        # Save results
        output_file = "scraped_conversions.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*60}")
        print(f"Scraping complete! Results saved to {output_file}")
        print(f"{'='*60}")
        
        # Print summary
        print("\nSummary:")
        for key in results:
            count = sum(len(events) for events in results[key].values())
            print(f"  {key}: {count} events")
        
        return results
        
    except Exception as e:
        print(f"Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        driver.quit()

if __name__ == "__main__":
    print("Starting conversion scraper...")
    print("This will test each event with 3 different times")
    print("and calculate linear conversion equations.\n")
    
    results = scrape_all_conversions()
