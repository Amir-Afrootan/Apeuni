import time
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FFService
from selenium.webdriver.firefox.options import Options as FFOptions

GECKO_PATH  = r"geckodriver.exe"
TOR_FIREFOX = r"D:\My Program Files\Tor Browser\Browser\firefox.exe"
TOR_PROFILE = r"D:\My Program Files\Tor Browser\Browser\TorBrowser\Data\Browser\profile.default"
TARGET_URL  = "https://www-yi.apeuni.com/practice/fib_rd/102"

skip_wait = False

def wait_for_enter():
    global skip_wait
    input("Press Enter to continue early...\n")
    skip_wait = True

options = FFOptions()
options.binary_location = TOR_FIREFOX
options.profile = TOR_PROFILE

service = FFService(GECKO_PATH)
driver = webdriver.Firefox(service=service, options=options)

try:
    print("Tor Browser started.")
    print("Waiting up to 2 minutes for Tor network connection...")

    t = threading.Thread(target=wait_for_enter, daemon=True)
    t.start()

    start = time.time()
    while time.time() - start < 300:
        if skip_wait:
            print("Enter pressed, continuing early...")
            break
        time.sleep(0.5)

    print("Opening target URL...")
    driver.get(TARGET_URL)

    answer_btn = driver.find_element(By.CSS_SELECTOR, "button.ant-switch")
    driver.execute_script("arguments[0].click();", answer_btn)

    print("Current URL:", driver.current_url)
    print("Done.")

    time.sleep(300)

finally:
    driver.quit()
