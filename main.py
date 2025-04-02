import requests
import threading
from users_automation import BootleggersBot
from deaths_automation import monitor_deaths
from gold_automation import start_gold_price_checker
from cities_automation import start_casino_monitor
from statistics_automation import start_stats_monitor
import time

# Login credentials and URLs
LOGIN_URL = "https://www.bootleggers.us/ajax/global.php?action=login"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Referer": "https://www.bootleggers.us/",
    "X-Requested-With": "XMLHttpRequest"
}
login_payload = {
    "username": "fakeuser",
    "password": "121212@12"  
}

def login():
    """Perform login and return the authenticated session."""
    session = requests.Session()
    login_response = session.post(LOGIN_URL, headers=headers, data=login_payload)
    if "success" not in login_response.text.lower():
        print("❌ Login Failed!")
        return None
    print("✅ Login Successful")
    
    # Follow redirect
    redirect_url = login_response.json().get("href", "//www.bootleggers.us").replace("//", "https://")
    session.get(redirect_url, headers=headers)
    return session

def main():
    """Main function to handle login and start monitoring."""
    session = login()
    if not session:
        return

    
    user_bot = BootleggersBot()
    user_thread = threading.Thread(
        target=user_bot.run,  # Note: pass the method reference without ()
        daemon=True,
        name="UserMonitor"
    )
    user_thread.start()
    
    # monitor_deaths_thread = threading.Thread(target=monitor_deaths, args=(session,))
    # monitor_deaths_thread.daemon = True  # Daemonize thread to exit when the main program exits
    
    # Start the gold price checker in a separate thread
    # gold_thread = threading.Thread(target=start_gold_price_checker, args=(session,))
    # gold_thread.daemon = True  # Daemonize thread to exit when the main program exits
    
    
    # casino_thread = threading.Thread(target=start_casino_monitor, args=(session,))
    # casino_thread.daemon = True  # Daemonize thread to exit when the main program exits
    
    # stats_thread = threading.Thread(target=start_stats_monitor, args=(session,))
    # stats_thread.daemon = True  # Daemonize thread to exit when the main program exits
    # stats_thread.start()
    

    # gold_thread.start()
    # monitor_deaths_thread.start()
    # casino_thread.start()
    

    # Keep the main thread alive to allow the monitoring threads to run
    try:
        while True:
            time.sleep(1)  # Keep the main thread alive
    except KeyboardInterrupt:
        print("\nScript stopped by user")

if __name__ == "__main__":
    main()