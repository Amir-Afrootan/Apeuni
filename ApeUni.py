import os
import time
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By

# ---------------------------
# Edge setup (profile + log suppression)
# ---------------------------
selenium_profile_path = r"C:\Users\Amir\EdgeSeleniumProfile"
os.makedirs(selenium_profile_path, exist_ok=True)

edge_options = Options()
edge_options.add_argument(f"user-data-dir={selenium_profile_path}")
edge_options.add_experimental_option("excludeSwitches", ["enable-logging"])
# edge_options.add_argument("--headless")  # در صورت نیاز

service = Service(r"D:\Programming\Python\Apeuni\msedgedriver.exe")
driver = webdriver.Edge(service=service, options=edge_options)

# ---------------------------
# Common fetch helper
# ---------------------------
def fetch_answer(url, css_selector, wait_time=10, is_rs=False):
    """
    واکشی جواب برای WFD, ASQ و RS
    """
    try:
        driver.get(url)

        # --- Step 1: چند بار چک کردن Answer switch ---
        for _ in range(4):
            try:
                btn = driver.find_element(By.CSS_SELECTOR, "button.ant-switch")
                if btn.get_attribute("aria-checked") == "false":
                    btn.click()
                    time.sleep(0.3)  # کوتاه برای رندر
                break
            except Exception:
                time.sleep(0.2)

        # --- Step 2: پیدا کردن پاراگراف جواب ---
        paragraph = None
        total_checks = int(wait_time / 0.25)
        for _ in range(total_checks):
            elems = driver.find_elements(By.CSS_SELECTOR, css_selector)
            if elems:
                paragraph = elems[0]
                spans = paragraph.find_elements(By.TAG_NAME, "span")
                text = " ".join(span.text.strip() for span in spans if span.text.strip())
                if text:
                    qid = url.rstrip("/").split("/")[-1]
                    return f"{qid}. {text}" if is_rs else f"{text} #{qid}"
            time.sleep(0.25)

        print(f"[Warning] No Answer paragraph for {url}")
        return None

    except Exception as e:
        print(f"[Error] {url}: {e}")
        return None

# ---------------------------
# Specific fetch functions
# ---------------------------
def fetch_answer_wfd(url): return fetch_answer(url, "p.Answer__Paragraph-h0b1cq-4")
def fetch_answer_asq(url): return fetch_answer(url, "p.Answer__AnswerText-h0b1cq-0")
def fetch_answer_rs(url):  return fetch_answer(url, "p[class^='Answer__Paragraph-']", wait_time=10, is_rs=True)

# ---------------------------
# Main program
# ---------------------------
def main():
    mode = input("Enter 1:WFD 2:ASQ 3:RS => ").strip()
    files = {
        "1": (r"WFD\wfds.txt", r"WFD\Output.txt", fetch_answer_wfd),
        "2": (r"ASQ\URL 2025-10.txt", r"ASQ\Output.txt", fetch_answer_asq),
        "3": (r"RS\URL 2025-10.txt", r"RS\Output.txt", fetch_answer_rs)
    }

    if mode not in files:
        print("Only 1, 2, 3 are valid.")
        driver.quit()
        return

    input_file, output_file, fetch_func = files[mode]
    if os.path.exists(output_file):
        os.remove(output_file)

    with open(input_file, "r", encoding="utf-8") as f:
        links = [line.strip() for line in f if line.strip()]

    for url in links:
        print(f"Fetching: {url}")
        result = fetch_func(url)
        if not result:
            result = f"[No Answer] #{url}"
        print(result)

        # --- ذخیره فوری در فایل ---
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(result + "\n")

        time.sleep(0.3)  # کوتاه برای رندر و آماده شدن صفحه

    driver.quit()
    print("✅ All done! Results saved to", os.path.abspath(output_file))

if __name__ == "__main__":
    main()
