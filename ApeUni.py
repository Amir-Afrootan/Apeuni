import os
from time import sleep
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException, StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

selenium_profile_path = r"D:\Programming\Python\Apeuni\EdgeSeleniumProfile"
os.makedirs(selenium_profile_path, exist_ok=True)
edge_options = Options(); edge_options.add_argument(f"user-data-dir={selenium_profile_path}"); edge_options.add_experimental_option("excludeSwitches", ["enable-logging"])
service = Service(r"msedgedriver.exe")
driver = webdriver.Edge(service=service, options=edge_options)
wait = WebDriverWait(driver, 5)

def fetch_answer(url, mode, output_file=None):
    selectors = {1: "p.Answer__Paragraph-h0b1cq-4", 2: "p.Answer__AnswerText-h0b1cq-0", 3: "p[class^='Answer__Paragraph-']", 4: ".fupsWk div:nth-child(2) p span:nth-child(even)"}
    try:
        driver.get(url); qid = url.rstrip("/").split("/")[-1]
        if mode in [1, 2, 3, 4]:
            css = selectors.get(mode); 
            if not css: return None
            for attempt in range(4):
                try:
                    btn = driver.find_element(By.CSS_SELECTOR, "button.ant-switch")
                    if btn.get_attribute("aria-checked") == "false":
                        try: btn.click()
                        except Exception: driver.execute_script("arguments[0].click();", btn)
                        sleep(0.8); break
                    else: break
                except NoSuchElementException:
                    print(f"[Try {attempt+1}/4] Answer button not yet loaded: {url}"); sleep(1); continue
            else:
                print(f"[Skip] No Answer button found after 4 tries: {url}"); return f"[No Button] {url}"
            for attempt in range(25):
                try:
                    elems = driver.find_elements(By.CSS_SELECTOR, css)
                    if elems:
                        text = ", ".join(e.text.strip() for e in elems if e.text.strip())
                        if text: return f"{qid}. {text}"
                except StaleElementReferenceException:
                    sleep(0.1); continue
                sleep(0.1)
            return f"[No Answer] {url}"
        else:
            drops = driver.find_elements(By.CSS_SELECTOR, "div.ant-select.ant-select-enabled")
            if not drops: print(f"[Warning] No dropdown found for {url}"); return None
            qid = url.rstrip("/").split("/")[-1]; lines_to_write = []
            for idx, drop in enumerate(drops, start=1):
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", drop); sleep(0.1)
                    driver.execute_script("arguments[0].click();", drop); sleep(0.3)
                    menus = driver.find_elements(By.CSS_SELECTOR, "div.ant-select-dropdown:not(.ant-select-dropdown-hidden) ul.ant-select-dropdown-menu")
                    if not menus: print(f"[Dropdown not opened] {url} #{idx}"); continue
                    for menu in menus:
                        items = menu.find_elements(By.CSS_SELECTOR, "li.ant-select-dropdown-menu-item")
                        for li in items:
                            text = li.text.strip()
                            if text: lines_to_write.append(f"{qid}. {idx}. {text}")
                    driver.execute_script("arguments[0].blur();", drop); sleep(0.1)
                except Exception as e:
                    print(f"[Dropdown Error] {url} #{idx}: {e}"); continue
            if lines_to_write and output_file:
                with open(output_file, "a", encoding="utf-8") as f: f.write("\n".join(lines_to_write) + "\n")
                print("\n".join(lines_to_write))
            return True
    except Exception as e:
        print(f"[Error] {url}: {e}"); return None

def main():
    mode = input("Enter 1:WFD  2:ASQ  3:RS  4:FIB_WR  5:FIB_WR dropdown => ").strip()
    if mode not in ["1", "2", "3", "4", "5"]: print("❌ Only 1–5 are valid."); driver.quit(); return
    mode = int(mode)
    paths = {
        1:(r"WFD\URL 2025-11.txt",r"WFD\Output.txt"),
        2:(r"ASQ\URL 2025-10.txt",r"ASQ\Output.txt"),
        3:(r"RS\URL 2025-10.txt",r"RS\Output.txt"),
        4:(r"FIB_WR\URL 2025-11.txt",r"FIB_WR\Output.txt"),
        5:(r"FIB_WR\URL 2025-11.txt",r"FIB_WR\FIB_WR_Output_Dropdowns.txt")
    }
    input_file, output_file = paths[mode]
    if not os.path.exists(input_file): print(f"❌ Input file not found: {input_file}"); driver.quit(); return
    if os.path.exists(output_file): os.remove(output_file)
    with open(input_file, "r", encoding="utf-8") as f: links=[line.strip() for line in f if line.strip()]
    for url in links:
        print(f"Fetching: {url}")
        try:
            result = fetch_answer(url, mode, output_file if mode == 5 else None)
            if mode != 5:
                if not result: result=f"[No Answer] {url}"
                print(result)
                with open(output_file,"a",encoding="utf-8") as f: f.write(result+"\n")
        except KeyboardInterrupt: print("⛔ Interrupted by user."); break
        except Exception as e: print(f"[Critical Error] {url}: {e}"); continue
    driver.quit(); print("✅ Done! Saved to", os.path.abspath(output_file))

if __name__=="__main__": main()
