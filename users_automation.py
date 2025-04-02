import csv
import os
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Configuration
LOGIN_URL = "https://www.bootleggers.us/"
ONLINE_USERS_URL = "https://www.bootleggers.us/usersonline.php"
CSV_FILENAME = "users.csv"
USERNAME = "player8333"
PASSWORD = "12345678"
CHECK_INTERVAL = 45  # Increased interval to reduce load
PROTECTION_PERIOD = timedelta(hours=336)  # 2 weeks protection
MAX_RETRIES = 3
PAGE_LOAD_TIMEOUT = 5  # Increased page load timeout

# Google Sheets Configuration
SHEET_NAME = "Users Online"
SCOPE = ["https://spreadsheets.google.com/feeds", 
         "https://www.googleapis.com/auth/drive"]
CREDS_FILE = "service_account.json"  # Path to your service account JSON file



class BootleggersBot:
    def __init__(self):
        self.driver = self._init_driver()
        self.existing_users = set()
        self._load_existing_users()
        self.gsheet = self._init_google_sheets()

    def _init_driver(self):
        """Initialize Chrome WebDriver with optimized settings"""
        options = Options()
        options.add_argument("--headless=new")  # Use new headless mode
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # WebGL and rendering settings
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-webgl")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-3d-apis")
        
        # Performance optimizations
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-browser-side-navigation")
        options.add_argument("--disable-logging")
        options.add_argument("--log-level=3")
        
        # Stability settings
        options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")
        options.add_argument("--disable-features=VizDisplayCompositor,HardwareMediaKeyHandling")
        
        # Additional flags to prevent GPU-related warnings
        options.add_argument("--use-angle=swiftshader")
        options.add_argument("--disable-gl-drawing-for-tests")
        options.add_argument("--disable-accelerated-2d-canvas")
        
        # Improved stability settings
        options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")
        options.add_argument("--disable-features=VizDisplayCompositor")
        
        prefs = {
            'profile.default_content_setting_values': {
                'images': 2,
                'javascript': 1,
                'plugins': 2,
                'popups': 2,
                'geolocation': 2,
                'notifications': 2
            }
        }
        options.add_experimental_option("prefs", prefs)
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        return driver

    def _init_google_sheets(self):
        """Initialize Google Sheets connection"""
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
            client = gspread.authorize(creds)

            # Try to open the spreadsheet
            spreadsheet = client.open("Heather Bootleggers Automation Deaths data")  
            
            # Try to get the worksheet or create if it doesn't exist
            try:
                worksheet = spreadsheet.worksheet(SHEET_NAME)
            except gspread.exceptions.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows="5000", cols="20")
                
                # Add headers if new sheet
                headers = ['name', 'messages', 'timeleft', 'profile_url', 
                         'check_time', 'account_age', 'account_created']
                worksheet.append_row(headers)
                
                # Format headers to be bold
                worksheet.format("A1:G1", {"textFormat": {"bold": True}})
            
            return worksheet
        except Exception as e:
            print(f"⚠️ Error initializing Google Sheets: {e}")
            return None

    def _save_to_google_sheets(self, user_data):
        """Save user data to Google Sheets"""
        if not self.gsheet:
            return
            
        try:
            data = [
                user_data['name'],
                user_data['messages'],
                user_data['timeleft'],
                user_data['profile_url'],
                user_data['check_time'],
                user_data['account_age'],
                user_data['account_created']
            ]
            self.gsheet.append_row(data)
        except Exception as e:
            print(f"⚠️ Error saving to Google Sheets: {e}")

    def _wait_for_page_load(self, timeout=10):
        """Wait for page to fully load"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete")
        except TimeoutException:
            print("⚠️ Page load timed out, continuing anyway")

    def _load_existing_users(self):
        """Load existing users from CSV file"""
        if not os.path.exists(CSV_FILENAME):
            return
        
        try:
            with open(CSV_FILENAME, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                if reader.fieldnames:
                    self.existing_users = {row['profile_url'] for row in reader}
        except Exception as e:
            print(f"⚠️ Error loading existing users: {e}")

    def _save_user(self, user_data):
        """Save a single user to CSV and Google Sheets"""
        # Save to CSV
        file_exists = os.path.exists(CSV_FILENAME)
        fieldnames = ['name', 'messages', 'timeleft', 'profile_url', 
                     'check_time', 'account_age', 'account_created']
        
        with open(CSV_FILENAME, 'a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(user_data)
        self.existing_users.add(user_data['profile_url'])
        
        # Save to Google Sheets
        self._save_to_google_sheets(user_data)

    def _handle_recaptcha(self):
        """Check for and handle reCAPTCHA if present"""
        try:
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            recaptcha_iframe = None
            
            for iframe in iframes:
                if "recaptcha" in iframe.get_attribute("src").lower():
                    recaptcha_iframe = iframe
                    break
            
            if recaptcha_iframe:
                print("🔍 reCAPTCHA detected - attempting to solve...")
                self.driver.switch_to.frame(recaptcha_iframe)
                checkbox = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.recaptcha-checkbox")))
                checkbox.click()
                self.driver.switch_to.default_content()
                print("✅ reCAPTCHA solved")
                time.sleep(3)  # Increased sleep after CAPTCHA
                return True
        except Exception as e:
            print(f"⚠️ reCAPTCHA handling error: {e}")
            self.driver.switch_to.default_content()
            return False

    def _check_for_captcha_and_recover(self):
        """Check for CAPTCHA and attempt to recover"""
        if self._handle_recaptcha():
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='logout.php']")))
                return True
            except TimeoutException:
                print("⚠️ CAPTCHA handling may have logged us out - attempting to relogin")
                return self.login()
        return True

    def _parse_timeleft(self, timeleft_str):
        """Parse timeleft string into timedelta"""
        if not timeleft_str or timeleft_str == "N/A":
            return None
            
        try:
            if "days" in timeleft_str:
                days_part, time_part = timeleft_str.split("days")
                days = int(days_part.strip())
                h, m, s = map(int, time_part.strip().split(":"))
                return timedelta(days=days, hours=h, minutes=m, seconds=s)
            else:
                h, m, s = map(int, timeleft_str.split(":"))
                return timedelta(hours=h, minutes=m, seconds=s)
        except Exception as e:
            print(f"⚠️ Couldn't parse timeleft: {e}")
            return None

    def _calculate_account_age(self, timeleft_str):
        """Calculate account age based on protection period minus timeleft"""
        timeleft = self._parse_timeleft(timeleft_str)
        if not timeleft:
            return ("N/A", "N/A")
        
        try:
            current_time = datetime.now()
            active_time = PROTECTION_PERIOD - timeleft
            account_created = current_time - active_time
            
            if active_time.days > 0:
                age_str = f"{active_time.days}d {active_time.seconds//3600}h"
            else:
                age_str = f"{active_time.seconds//3600}h {(active_time.seconds%3600)//60}m"
            
            return (age_str, account_created.strftime("%Y-%m-%d %H:%M:%S"))
        except Exception as e:
            print(f"⚠️ Couldn't calculate account age: {e}")
            return ("N/A", "N/A")

    def login(self):
        """Perform login with reCAPTCHA handling and retries"""
        for attempt in range(MAX_RETRIES):
            try:
                self.driver.get(LOGIN_URL)
                self._wait_for_page_load()
                
                if not self._handle_recaptcha():
                    print("⚠️ No CAPTCHA found during login")
                
                username = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "form.loginForm input[name='username']")))
                password = self.driver.find_element(By.CSS_SELECTOR, "form.loginForm input[name='password']")
                submit = self.driver.find_element(By.CSS_SELECTOR, "form.loginForm input[type='submit']")
                
                username.clear()
                username.send_keys(USERNAME)
                password.clear()
                password.send_keys(PASSWORD)
                submit.click()
                
                self._wait_for_page_load()
                self._handle_recaptcha()
                
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='logout.php']")))
                return True
            except Exception as e:
                print(f"⚠️ Login attempt {attempt + 1} failed: {e}")
                if attempt == MAX_RETRIES - 1:
                    return False
                time.sleep(5)
                continue

    def get_online_users(self):
        """Get online users with reCAPTCHA check and retries"""
        for attempt in range(MAX_RETRIES):
            try:
                if not self._check_for_captcha_and_recover():
                    print("⚠️ Couldn't recover from CAPTCHA check")
                    return []
                
                self.driver.get(ONLINE_USERS_URL)
                self._wait_for_page_load()
                self._handle_recaptcha()
                
                user_links = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.listing a[href*='/user/']")))
                return [link.get_attribute('href') for link in user_links]
            except Exception as e:
                print(f"⚠️ Get online users attempt {attempt + 1} failed: {e}")
                if attempt == MAX_RETRIES - 1:
                    return []
                time.sleep(5)
                continue

    def scrape_user_profile(self, profile_url):
        """Scrape user data with improved synchronization"""
        for attempt in range(MAX_RETRIES):
            try:
                if not self._check_for_captcha_and_recover():
                    print("⚠️ Couldn't recover from CAPTCHA check before profile scrape")
                    return None
                
                self.driver.get(profile_url)
                self._wait_for_page_load()
                
                # Use more reliable waiting for elements
                name = WebDriverWait(self.driver, 15).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "td.profile-header"))
                ).text.split("Profile For ")[-1].replace(":", "").strip()
                
                messages = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//td[contains(., "Messages:")]/following-sibling::td')
                    )
                ).text.strip()
                
                try:
                    timeleft = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//td[@class='profile-image-container']//div[@class='profile-window effects']")
                        )
                    ).text
                    account_age, account_created = self._calculate_account_age(timeleft)
                except (NoSuchElementException, TimeoutException):
                    timeleft = "N/A"
                    account_age = "N/A"
                    account_created = "N/A"
                
                return {
                    'name': name,
                    'messages': messages,
                    'timeleft': timeleft,
                    'profile_url': profile_url,
                    'check_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'account_age': account_age,
                    'account_created': account_created
                }
            except Exception as e:
                print(f"⚠️ Profile scraping attempt {attempt + 1} failed for {profile_url}: {e}")
                if attempt == MAX_RETRIES - 1:
                    return None
                time.sleep(3)
                continue

    def check_new_users(self):
        """Check for new users with all tracking and error recovery"""
        for attempt in range(MAX_RETRIES):
            try:
                current_users = self.get_online_users()
                if not current_users:
                    print("⚠️ No users found - may be CAPTCHA or other issue")
                    if attempt == MAX_RETRIES - 1:
                        return False
                    time.sleep(5)
                    continue
                
                new_count = 0
                for url in current_users:
                    if url not in self.existing_users:
                        user_data = self.scrape_user_profile(url)
                        if user_data:
                            self._save_user(user_data)
                            new_count += 1
                            print(f"✅ {user_data['name']} | Timeleft: {user_data['timeleft']} | Age: {user_data['account_age']} | Created: {user_data['account_created']}")
                
                print(f"🔍 Found {new_count} new users | Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                return True
            except Exception as e:
                print(f"⚠️ Check new users attempt {attempt + 1} failed: {e}")
                if attempt == MAX_RETRIES - 1:
                    return False
                time.sleep(5)
                continue

    def run(self):
        """Main monitoring loop with enhanced error recovery"""
        if not self.login():
            print("❌ Login failed after multiple attempts")
            return
            
        print("🚀 Monitoring started - Press Ctrl+C to stop")
        try:
            while True:
                start_time = time.time()
                if not self.check_new_users():
                    print("⚠️ Main check failed - attempting to recover session")
                    if not self.login():
                        print("❌ Failed to recover session - stopping")
                        break
                
                elapsed = time.time() - start_time
                sleep_time = max(0, CHECK_INTERVAL - elapsed)
                print(f"⏳ Next check in {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped")
        except Exception as e:
            print(f"⚠️ Unexpected error in main loop: {e}")
        finally:
            self.driver.quit()

if __name__ == "__main__":
    bot = BootleggersBot()
    bot.run()