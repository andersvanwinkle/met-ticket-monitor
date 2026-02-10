import requests
from bs4 import BeautifulSoup
import time
import json
import hashlib
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import os
import ssl
import urllib3

# Disable SSL warnings if we're bypassing verification
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class MetOperaMonitor:
    def __init__(self, check_interval=3600):  # Default: check every hour
        self.url = "https://www.metopera.org/season/tickets/student-tickets/"
        self.check_interval = check_interval
        self.previous_shows = set()
        self.data_file = "met_opera_shows.json"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.load_previous_data()

    def load_previous_data(self):
        """Load previously saved show data from file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.previous_shows = set(data.get('shows', []))
                    print(f"Loaded {len(self.previous_shows)} previously tracked shows")
            except Exception as e:
                print(f"Error loading previous data: {e}")
                self.previous_shows = set()

    def save_data(self, shows):
        """Save current show data to file"""
        try:
            data = {
                'shows': list(shows),
                'last_updated': datetime.now().isoformat(),
                'total_shows': len(shows)
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving data: {e}")

    def fetch_page_content(self):
        """Fetch the web page content"""
        try:
            # First try with normal SSL verification
            response = requests.get(self.url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.SSLError as ssl_error:
            print(f"SSL Error encountered: {ssl_error}")
            print("Attempting to fetch with SSL verification disabled...")
            try:
                # Retry with SSL verification disabled
                response = requests.get(self.url, headers=self.headers, timeout=30, verify=False)
                response.raise_for_status()
                print("✅ Successfully fetched page with SSL verification disabled")
                return response.text
            except requests.RequestException as e:
                print(f"Error fetching page even with SSL disabled: {e}")
                return None
        except requests.RequestException as e:
            print(f"Error fetching page: {e}")
            return None

    def extract_shows(self, html_content):
        """Extract show information from the HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        shows = set()

        # Target the specific xpath: /html/body/div[3]/div/main/div/div/div/ul
        # This translates to: body > div:nth-of-type(3) > div > main > div > div > div > ul

        # Primary strategy: Use the exact xpath location
        target_selectors = [
            'body > div:nth-of-type(3) > div > main > div > div > div > ul',
            'body > div:nth-child(3) > div > main > div > div > div > ul',
            # More flexible versions in case the structure varies slightly
            'main > div > div > div > ul',
            'main ul',
            # Look for any ul that might contain the shows
            'div > ul'
        ]

        found_shows = False
        for selector in target_selectors:
            ul_elements = soup.select(selector)
            if ul_elements:
                print(f"✅ Found UL element(s) using selector: {selector}")
                for ul in ul_elements:
                    # Get all list items in this ul
                    list_items = ul.find_all('li')
                    if list_items:
                        print(f"📋 Found {len(list_items)} list items")
                        found_shows = True
                        for i, li in enumerate(list_items):
                            show_text = self.clean_text(li.get_text())
                            if show_text and len(show_text) > 5:  # Minimum length filter
                                shows.add(show_text)
                                print(f"   {i + 1}. {show_text[:100]}{'...' if len(show_text) > 100 else ''}")
                        break  # Stop after finding the first successful ul
                if found_shows:
                    break

        # Fallback strategy: Look for any ul elements that might contain shows
        if not found_shows:
            print("🔍 Primary selectors failed, trying fallback strategy...")
            all_uls = soup.find_all('ul')
            print(f"📋 Found {len(all_uls)} total UL elements on page")

            for i, ul in enumerate(all_uls):
                list_items = ul.find_all('li')
                if list_items and len(list_items) > 2:  # Only consider ULs with multiple items
                    print(f"🎯 Checking UL #{i + 1} with {len(list_items)} items:")

                    # Check if this looks like a show listing
                    sample_text = self.clean_text(ul.get_text()[:200])
                    print(f"   Sample text: {sample_text}...")

                    # Look for opera-related keywords
                    if any(keyword in sample_text.lower() for keyword in
                           ['opera', 'performance', 'curtain', 'matinee', 'evening', 'pm', 'am',
                            'student', 'ticket', 'sold out', 'available']):
                        print(f"   ✅ This looks like a show listing!")
                        found_shows = True
                        for j, li in enumerate(list_items):
                            show_text = self.clean_text(li.get_text())
                            if show_text and len(show_text) > 5:
                                shows.add(show_text)
                                print(f"      {j + 1}. {show_text[:100]}{'...' if len(show_text) > 100 else ''}")
                        break
                    else:
                        print(f"   ❌ Doesn't look like show listings")

        # Debug: If still no shows found, let's see what we have
        if not found_shows:
            print("⚠️ No shows found with any strategy. Debugging page structure...")

            # Print all div structures that might contain the target
            main_element = soup.find('main')
            if main_element:
                print("📍 Found main element, exploring structure...")
                divs = main_element.find_all('div')
                print(f"   Found {len(divs)} div elements in main")

                for i, div in enumerate(divs):
                    ul = div.find('ul')
                    if ul:
                        items = ul.find_all('li')
                        print(f"   Div #{i} contains UL with {len(items)} items")
                        if items:
                            sample = self.clean_text(items[0].get_text()[:100])
                            print(f"      Sample: {sample}...")

        return shows

    def clean_text(self, text):
        """Clean and normalize text"""
        if not text:
            return ""

        # Remove extra whitespace and normalize
        text = ' '.join(text.split())
        # Remove common unwanted characters
        text = text.replace('\n', ' ').replace('\r', '').replace('\t', ' ')
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def detect_new_shows(self, current_shows):
        """Detect new shows that weren't in the previous check"""
        if not self.previous_shows:
            # First run - all shows are "new"
            print("First run detected. All shows will be considered existing.")
            return set()

        new_shows = current_shows - self.previous_shows
        return new_shows

    def send_notification(self, new_shows, email_config=None):
        """Send notification about new shows"""
        if not new_shows:
            return

        print(f"\n🎭 NEW SHOWS DETECTED ({len(new_shows)}):")
        print("=" * 50)
        for i, show in enumerate(new_shows, 1):
            print(f"{i}. {show}")
        print("=" * 50)

        # Email notification (optional)
        if email_config:
            print("Attempting to send email")
            self.send_email_notification(new_shows, email_config)

    def send_email_notification(self, new_shows, config):
        """Send email notification about new shows"""
        try:
            subject = f"🎭 New Met Opera Student Shows Available! ({len(new_shows)} new)"

            body = f"""
New shows have been added to the Met Opera Student Tickets page!

{len(new_shows)} new show(s) detected:

"""
            for i, show in enumerate(new_shows, 1):
                body += f"{i}. {show}\n"

            body += f"\nCheck them out at: {self.url}\n\nHappy opera-going! 🎵"

            msg = MIMEMultipart()
            msg['From'] = config['from_email']
            msg['To'] = config['to_email']
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
            server.starttls()
            server.login(config['from_email'], config['password'])
            server.send_message(msg)
            server.quit()

            print(f"📧 Email notification sent to {config['to_email']}")
        except Exception as e:
            print(f"❌ Failed to send email notification: {e}")

    def run_single_check(self, email_config=None):
        """Run a single check for new shows"""
        print(f"🔍 Checking for new shows at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        html_content = self.fetch_page_content()
        if not html_content:
            print("❌ Failed to fetch page content")
            return False

        current_shows = self.extract_shows(html_content)
        print(f"📊 Found {len(current_shows)} total shows on the page")

        if not current_shows:
            print("⚠️ No shows found. The page structure might have changed.")
            return False

        new_shows = self.detect_new_shows(current_shows)

        if new_shows:
            print("Attempting to send notifications")
            self.send_notification(new_shows, email_config)
            # Update stored data
            self.save_data(current_shows)
            self.previous_shows = current_shows
            return True
        else:
            print("✅ No new shows detected")
            # Still update the data in case shows were removed
            self.save_data(current_shows)
            self.previous_shows = current_shows
            return False

    def monitor_continuously(self, email_config=None):
        """Continuously monitor for new shows"""
        print(f"🎭 Starting Met Opera Student Tickets Monitor")
        print(f"📍 Monitoring: {self.url}")
        print(f"⏰ Check interval: {self.check_interval} seconds ({self.check_interval / 3600:.1f} hours)")
        print(f"💾 Data file: {self.data_file}")

        while True:
            try:
                found_new = self.run_single_check(email_config)

                if found_new and email_config:
                    # If we found new shows and have email config, send notification
                    pass  # Notification already sent in run_single_check

                print(f"😴 Waiting {self.check_interval} seconds until next check...\n")
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                print("\n👋 Monitor stopped by user")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                print(f"🔄 Continuing monitoring in {self.check_interval} seconds...")
                time.sleep(self.check_interval)


def main():
    # SSL Configuration - try to fix certificate issues
    try:
        import ssl
        # Try to create a default SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
    except Exception as ssl_setup_error:
        print(f"SSL setup warning: {ssl_setup_error}")

    # Configuration
    CHECK_INTERVAL = 1800  # Check every hour (3600 seconds)

    # Email configuration (optional - set to None to disable email notifications)
    EMAIL_CONFIG = {
        'from_email': 'anders.vanwinkle@gmail.com',
        'password': 'ctgk zwbj nqsd ikos',  # Use app password for Gmail
        'to_email': 'jacobrobertvanwinkle@gmail.com',
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587
    }

    # Set to None to disable email notifications
    # EMAIL_CONFIG = None

    # Create and run monitor
    monitor = MetOperaMonitor(check_interval=CHECK_INTERVAL)

    # For testing: run a single check
    # monitor.run_single_check()

    # For continuous monitoring:
    monitor.monitor_continuously(email_config=EMAIL_CONFIG)


if __name__ == "__main__":
    main()