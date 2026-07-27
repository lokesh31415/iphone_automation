import time
import os

# 'load_dotenv' loads environment variables from a .env file into the script
from dotenv import load_dotenv

# 'webdriver' is the core component of Appium/Selenium that actually controls the phone
from appium import webdriver

# 'XCUITestOptions' is where we define all the settings/capabilities for our iOS automation
from appium.options.ios import XCUITestOptions

# 'AppiumBy' allows us to choose HOW we want to find elements on the screen (by ID, by Name, etc.)
from appium.webdriver.common.appiumby import AppiumBy

# 'WebDriverWait' allows us to tell the script to "wait up to X seconds" for something to happen on screen
from selenium.webdriver.support.ui import WebDriverWait

# 'expected_conditions' (imported as 'EC' for short) defines WHAT we are waiting for (e.g. wait for a button to be clickable)
from selenium.webdriver.support import expected_conditions as EC

# We import this specific error so we can tell our script to ignore it if the screen flashes or updates while searching
from selenium.common.exceptions import StaleElementReferenceException

# Load variables from the .env file (keeps your personal IDs hidden from GitHub)
load_dotenv()

# ==========================================
# CONFIGURATION VARIABLES
# (Loaded from .env file)
# ==========================================

# Your physical iPhone's unique ID. Appium needs this so it knows which USB device to talk to.
DEVICE_UDID = os.getenv("DEVICE_UDID")

# The name of your AirPods exactly as they appear in your Bluetooth menu.
AIRPODS_NAME = os.getenv("AIRPODS_NAME")

# The custom Bundle ID used to sign WebDriverAgent in Xcode
WDA_BUNDLE_ID = os.getenv("WDA_BUNDLE_ID", "com.facebook.WebDriverAgentRunner")

# The address where the Appium server is running on your Mac (default is usually 127.0.0.1:4723)
APPIUM_SERVER_URL = "http://127.0.0.1:4723"

def cycle_bluetooth():
    """
    This function automates the process of opening the Settings app, 
    navigating to the Bluetooth menu, and tapping your AirPods to connect/disconnect them.
    """
    
    # ---------------------------------------------------------
    # STEP 1: SET UP AUTOMATION CAPABILITIES
    # Think of these options as the "instructions" we pass to Appium
    # ---------------------------------------------------------
    options = XCUITestOptions()
    options.platform_name = "iOS"
    options.automation_name = "XCUITest" # XCUITest is Apple's official automation framework under the hood
    options.device_name = "iPhone"
    options.udid = DEVICE_UDID
    
    # bundle_id tells Appium exactly which app to launch. 'com.apple.Preferences' is the internal ID for the iOS Settings app.
    options.bundle_id = "com.apple.Preferences"
    
    # no_reset tells Appium NOT to delete the app's data or uninstall it when the test is done.
    options.no_reset = True
    
    # This prints Xcode's internal logs to your terminal so we can see what's happening if it fails.
    options.set_capability("showXcodeLog", True)
    
    # This is the magic bullet for physical iOS devices. It tells Appium: 
    # "Don't try to build the WebDriverAgent app from scratch, just use the one I already installed via Xcode!"
    options.set_capability("usePrebuiltWDA", True)
    
    # We pass the custom Bundle ID we created in Xcode so Appium knows exactly which app on the phone is the automation server.
    options.set_capability("updatedWDABundleId", WDA_BUNDLE_ID)
    
    # We use a custom port (8101 instead of default 8100) to ensure Xcode isn't blocking our connection.
    options.set_capability("wdaLocalPort", 8101)

    # ---------------------------------------------------------
    # STEP 2: START THE SESSION
    # ---------------------------------------------------------
    print(f"Connecting to Appium Server at {APPIUM_SERVER_URL}...")
    # This line officially starts the automation. Your phone screen will light up and open the Settings app!
    driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)

    # ---------------------------------------------------------
    # STEP 3: CONFIGURE OUR 'WAIT' STRATEGY
    # ---------------------------------------------------------
    # Because phones can be slow or fast, we don't want to use hardcoded sleep times like time.sleep(5) to wait for buttons.
    # Instead, we create a 'WebDriverWait' that will intelligently wait up to 15 seconds for a button to appear.
    # If the button appears in 1 second, it immediately clicks it and moves on!
    wait = WebDriverWait(
        driver, 
        timeout=15, 
        ignored_exceptions=[StaleElementReferenceException] # If the UI updates while we are looking at it, ignore the error and try looking again
    )

    try:
        # ---------------------------------------------------------
        # STEP 4: TAP THE "BLUETOOTH" MENU
        # ---------------------------------------------------------
        print("Navigating to Bluetooth settings...")
        
        # We tell our 'wait' to look for an element with the exact accessibility ID of "Bluetooth", and wait until it is clickable.
        bluetooth_menu = wait.until(
            EC.element_to_be_clickable((AppiumBy.ACCESSIBILITY_ID, "Bluetooth"))
        )
        # Once found, we click it!
        bluetooth_menu.click()

        # ---------------------------------------------------------
        # STEP 5: CONNECT TO THE AIRPODS
        # ---------------------------------------------------------
        print(f"Waiting for '{AIRPODS_NAME}' to appear in the Bluetooth list...")
        
        # Why are we using IOS_PREDICATE here?
        # Apple dynamically adds "Not Connected" or "Connected" to the hidden label of the AirPods row.
        # If we asked Appium to look for exactly "Lokesh's AirPods", it would fail because the real label is "Lokesh's AirPods, Not Connected".
        # IOS_PREDICATE allows us to do a "CONTAINS" search, which finds the row regardless of its connection status!
        predicate_query = f"label CONTAINS '{AIRPODS_NAME}'"
        
        airpods_element = wait.until(
            EC.element_to_be_clickable((AppiumBy.IOS_PREDICATE, predicate_query))
        )
        
        print(f"Tapping to connect to '{AIRPODS_NAME}'...")
        airpods_element.click()

        # We use a hardcoded sleep here because the physical Bluetooth connection takes a few seconds.
        # The screen might look connected immediately, but the hardware needs time to catch up.
        print("Waiting 5 seconds for physical hardware connection handshake to complete...")
        time.sleep(5)

        # ---------------------------------------------------------
        # STEP 6: DISCONNECT FROM THE AIRPODS
        # ---------------------------------------------------------
        print(f"Re-locating '{AIRPODS_NAME}' to avoid stale references and disconnecting...")
        
        # After connecting, the screen updated (it now says "Connected"). 
        # Because the screen changed, our old 'airpods_element' variable is technically "stale" (outdated). 
        # We MUST search for it again before clicking it a second time.
        airpods_element_reloaded = wait.until(
            EC.element_to_be_clickable((AppiumBy.IOS_PREDICATE, predicate_query))
        )
        airpods_element_reloaded.click()
        print("Disconnection tap successful.")

    except Exception as e:
        # If anything goes wrong (e.g., Bluetooth menu isn't found), print the exact error so we can fix it.
        print(f"An error occurred during automation: {e}")

    finally:
        # ---------------------------------------------------------
        # STEP 7: CLEANUP
        # ---------------------------------------------------------
        # The 'finally' block ensures that no matter what happens (success or failure), 
        # we always tell the Appium server to close the connection properly.
        print("Tearing down the driver session...")
        driver.quit()

# This is standard Python boilerplate that just means: 
# "If someone runs this file directly from the terminal, execute the cycle_bluetooth() function!"
if __name__ == "__main__":
    cycle_bluetooth()
