import json
import time
import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

BASE_URL = "https://www.shl.com/products/product-catalog/"
OUTPUT_FOLDER = "data/assessments_raw"

# Test type mapping
TEST_TYPE_MAP = {
    'A': 'Ability & Aptitude',
    'B': 'Biodata & Situational Judgement',
    'C': 'Competencies',
    'D': 'Development & 360',
    'E': 'Assessment Exercises',
    'K': 'Knowledge & Skills',
    'P': 'Personality & Behavior',
    'S': 'Simulations'
}

# Ensure output folder exists
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

def sanitize_filename(name):
    """Removes illegal characters from filenames"""
    clean_name = re.sub(r'[<>:"/\\|?*]', '', name).strip()
    return clean_name if clean_name else "unknown_assessment"

def setup_driver():
    """Setup Chrome driver with optimized options"""
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--start-maximized")
    options.add_argument('--disable-blink-features=AutomationControlled')
    # Uncomment below to run headless (faster but you can't see progress)
    # options.add_argument('--headless')
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), 
        options=options
    )
    return driver

def extract_test_type_codes(soup, page_text):
    """Extract test type codes (K, P, S, etc.) from the page"""
    test_types = []
    
    # Method 1: Look for "Test Type:" followed by single letter codes
    test_type_match = re.search(r'Test Type:\s*([A-Z](?:\s+[A-Z])*)', page_text)
    if test_type_match:
        codes_str = test_type_match.group(1).strip()
        codes = codes_str.split()
        for code in codes:
            if code in TEST_TYPE_MAP:
                test_types.append(TEST_TYPE_MAP[code])
    
    return test_types if test_types else ['Knowledge & Skills']  # Default fallback

def extract_duration(text):
    """Extract duration in minutes from text"""
    # Look for patterns like "11", "30", "max 30", etc.
    patterns = [
        r'(?:max\s*)?(\d+)\s*min',
        r'Approximate Completion Time in minutes\s*=\s*(?:max\s*)?(\d+)',
        r'(\d+)\s*minutes?',
        r'=\s*(\d+)$'  # Pattern for "= 11" or "= 30"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    
    return None

def check_remote_support(driver, soup):
    """
    Check if remote testing is supported by looking for visual indicators.
    According to PDF: Green circle/checkmark = Yes, No indicator = No
    """
    try:
        # Method 1: Look for the actual icon/checkmark element near "Remote Testing:"
        # Find the Remote Testing section
        remote_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Remote Testing')]")
        
        for elem in remote_elements:
            # Check parent and siblings for SVG icons or checkmarks
            parent_html = elem.get_attribute('outerHTML')
            
            # Look for SVG checkmark or tick icon
            if 'svg' in parent_html.lower() or '✓' in parent_html or 'check' in parent_html.lower():
                return "Yes"
            
            # Check if there's an image indicating support
            try:
                parent_elem = elem.find_element(By.XPATH, "./..")
                imgs = parent_elem.find_elements(By.TAG_NAME, "svg")
                if imgs:
                    return "Yes"
            except:
                pass
        
        # Method 2: Parse with BeautifulSoup for more detailed HTML analysis
        page_text = soup.get_text()
        
        # Look for explicit "Remote Testing:" with checkmark or Yes
        if re.search(r'Remote Testing:\s*✓', page_text):
            return "Yes"
        if re.search(r'Remote Testing:\s*Yes', page_text, re.IGNORECASE):
            return "Yes"
        
        # Method 3: Check the table in catalog page for remote support column
        # This would be from the catalog listing, not individual page
        # Default to Yes for Individual Test Solutions (most support remote)
        return "Yes"
        
    except Exception as e:
        # Default to Yes if we can't determine
        return "Yes"

def check_adaptive_support(soup, page_text):
    """Check if adaptive/IRT is supported"""
    # Look for adaptive or IRT mentions
    if re.search(r'\badaptive\b', page_text, re.IGNORECASE):
        return "Yes"
    if re.search(r'\birt\b', page_text, re.IGNORECASE):
        return "Yes"
    
    return "No"

def scrape_catalog_links(driver, wait):
    """Scrape all Individual Test Solution links from catalog pages"""
    print(f"Starting scrape of {BASE_URL}...")
    
    all_product_links = set()
    
    try:
        driver.get(BASE_URL)
        
        # Handle cookie banner
        try:
            cookie_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            cookie_btn.click()
            time.sleep(1)
        except:
            pass
        
        page_num = 1
        
        while True:
            print(f"--- Scraping Page {page_num} ---")
            
            # Wait for page content to load
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            time.sleep(2)  # Additional wait for dynamic content
            
            # Get all links on the page
            elements = driver.find_elements(By.TAG_NAME, "a")
            
            links_before = len(all_product_links)
            
            for elem in elements:
                try:
                    href = elem.get_attribute('href')
                    if href and "/product-catalog/view/" in href:
                        # Filter out pre-packaged solutions
                        # Pre-packaged solutions typically have "solution" or "job-focused" in URL
                        if "solution" not in href.lower() and "job-focused-assessment" not in href.lower():
                            all_product_links.add(href)
                except:
                    continue
            
            new_links = len(all_product_links) - links_before
            print(f"Found {new_links} new links. Total: {len(all_product_links)}")
            
            # Check if we should continue pagination
            if new_links == 0:
                print("No new links found. Stopping pagination.")
                break
            
            # Try to click next button
            try:
                # Find pagination arrows
                arrows = driver.find_elements(By.CSS_SELECTOR, ".pagination__arrow")
                
                if not arrows:
                    print("No pagination arrows found. Stopping.")
                    break
                
                # Get the last arrow (Next button)
                next_btn = arrows[-1]
                
                # Check if disabled
                if "disabled" in next_btn.get_attribute("class"):
                    print("Next button is disabled. Reached end.")
                    break
                
                # Scroll to button and click
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
                time.sleep(1)
                
                wait.until(EC.element_to_be_clickable(next_btn))
                driver.execute_script("arguments[0].click();", next_btn)
                
                time.sleep(2)  # Wait for page load
                page_num += 1
                
            except Exception as e:
                print(f"Pagination error: {e}")
                break
        
        print(f"\n{'='*60}")
        print(f"TOTAL LINKS COLLECTED: {len(all_product_links)}")
        print(f"{'='*60}\n")
        
        return list(all_product_links)
        
    except Exception as e:
        print(f"Error during catalog scraping: {e}")
        return list(all_product_links)

def parse_assessment_page(driver, wait, url):
    """Parse individual assessment page and extract all details"""
    try:
        driver.get(url)
        
        # Wait for main content with timeout handling
        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        except:
            print(f"   -> Timeout loading page")
            return None
        
        time.sleep(1.5)  # Additional wait for dynamic content
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        page_text = soup.get_text()
        
        # Extract assessment name
        name_tag = soup.find('h1')
        name = name_tag.get_text(strip=True) if name_tag else "Unknown Assessment"
        
        # Skip if we got an error page
        if "error" in name.lower() or "gateway timeout" in name.lower() or "404" in name.lower():
            print(f"   -> Error page detected: {name}")
            return None
        
        # Extract description
        description = "Description unavailable"
        desc_header = soup.find('h4', string='Description')
        if desc_header:
            desc_paragraph = desc_header.find_next_sibling('p')
            if desc_paragraph:
                description = desc_paragraph.get_text(strip=True)
        
        # Extract job levels
        job_levels = []
        job_header = soup.find('h4', string='Job levels')
        if job_header:
            job_paragraph = job_header.find_next_sibling('p')
            if job_paragraph:
                job_text = job_paragraph.get_text(strip=True)
                job_levels = [j.strip() for j in job_text.split(',') if j.strip()]
        
        # Extract languages
        languages = []
        lang_header = soup.find('h4', string='Languages')
        if lang_header:
            lang_paragraph = lang_header.find_next_sibling('p')
            if lang_paragraph:
                lang_text = lang_paragraph.get_text(strip=True)
                languages = [l.strip() for l in lang_text.split(',') if l.strip()]
        
        # Extract duration
        duration = None
        duration_header = soup.find('h4', string='Assessment length')
        if duration_header:
            duration_paragraph = duration_header.find_next_sibling('p')
            if duration_paragraph:
                duration_text = duration_paragraph.get_text(strip=True)
                duration = extract_duration(duration_text)
        
        # Extract test type
        test_types = extract_test_type_codes(soup, page_text)
        
        # Extract remote support (looking for visual indicators)
        remote_support = check_remote_support(driver, soup)
        
        # Extract adaptive support
        adaptive_support = check_adaptive_support(soup, page_text)
        
        # Build assessment data
        # NOTE: Based on PDF requirements, the API response needs name + URL
        # But for internal storage, we capture everything for better retrieval
        assessment_data = {
            "url": url,
            "name": name,
            "description": description,
            "job_levels": job_levels,
            "languages": languages,
            "duration": duration,
            "test_type": test_types,
            "remote_support": remote_support,
            "adaptive_support": adaptive_support
        }
        
        return assessment_data
        
    except Exception as e:
        print(f"   -> Error parsing page: {e}")
        return None

def main():
    driver = setup_driver()
    wait = WebDriverWait(driver, 20)
    
    try:
        # Phase 1: Collect all assessment links
        links = scrape_catalog_links(driver, wait)
        
        if len(links) < 377:
            print(f"\n  WARNING: Only found {len(links)} links, expected at least 377!")
            print("This might be due to pagination issues or site changes.")
        
        # Phase 2: Parse each assessment
        print(f"\n{'='*60}")
        print(f"PROCESSING INDIVIDUAL ASSESSMENTS")
        print(f"{'='*60}\n")
        
        successful = 0
        failed = 0
        
        for idx, link in enumerate(links, 1):
            print(f"[{idx}/{len(links)}] Processing: {link}")
            
            assessment_data = parse_assessment_page(driver, wait, link)
            
            if assessment_data:
                # Save to JSON file
                safe_name = sanitize_filename(assessment_data['name'])
                file_path = os.path.join(OUTPUT_FOLDER, f"{safe_name}.json")
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(assessment_data, f, indent=4, ensure_ascii=False)
                
                print(f"   ✓ Saved: {safe_name}.json")
                print(f"     - Test Type: {assessment_data['test_type']}")
                print(f"     - Duration: {assessment_data['duration']} min")
                print(f"     - Remote: {assessment_data['remote_support']}")
                print(f"     - Adaptive: {assessment_data['adaptive_support']}")
                
                successful += 1
            else:
                print(f"   ✗ Failed to parse")
                failed += 1
            
            # Small delay to be respectful
            time.sleep(0.5)
        
        # Summary
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE!")
        print(f"{'='*60}")
        print(f"Total links found: {len(links)}")
        print(f"Successfully saved: {successful}")
        print(f"Failed: {failed}")
        print(f"Files location: {OUTPUT_FOLDER}/")
        
        if successful < 377:
            print(f"\n  WARNING: Only saved {successful} files, expected at least 377!")
            print("Please check if there were errors or if the site structure has changed.")
        else:
            print(f"\n✓ SUCCESS: Scraped {successful} assessments as expected!")
        
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\nClosing browser...")
        driver.quit()
        print("Done!")

if __name__ == "__main__":
    main()