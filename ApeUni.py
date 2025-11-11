import os
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep

# ---------------------------
# Edge driver setup
# ---------------------------
selenium_profile_path = r"D:\Programming\Python\Apeuni\EdgeSeleniumProfile"
os.makedirs(selenium_profile_path, exist_ok=True)
edge_options = Options()
edge_options.add_argument(f"user-data-dir={selenium_profile_path}")
edge_options.add_experimental_option("excludeSwitches", ["enable-logging"])
service = Service(r"msedgedriver.exe")
driver = webdriver.Edge(service=service, options=edge_options)

# ---------------------------
# Fetch answer or dropdowns
# ---------------------------
def fetch_answer(url, mode, output_file):
	selectors = {
		1: "span.WordContainer-sc-126h18d",  # ✅ اصلاح شده برای WFD
		2: "p.Answer__AnswerText-h0b1cq-0",
		3: "p[class^='Answer__Paragraph-']",
		4: ".fupsWk div:nth-child(2) p span:nth-child(even)"
	}

	try:
		driver.get(url)

		# -------------------------------------------------- Mode 1 (WFD)
		if mode == 1:
			sleep(2)
			btn = driver.find_element(By.CSS_SELECTOR, "button.ant-switch")
			btn.click()

			sleep(0.5)
			spans = driver.find_elements(By.CSS_SELECTOR, "span.iDEUQt")
			text = " ".join(s.text.strip() for s in spans if s.text.strip())
			if text:
				qid = url.rstrip("/").split("/")[-1]
				line = f"{qid}. {text}"
				with open(output_file, "a", encoding="utf-8") as f:
					f.write(line + "\n")
				print(line)
				return line

			print(f"[No Answer] {url}")
			return None

		# -------------------------------------------------- Modes 2–4
		elif mode in [2, 3, 4]:
			for _ in range(4):
				try:
					btn = driver.find_element(By.CSS_SELECTOR, "button.ant-switch")
					if btn.get_attribute("aria-checked") == "false":
						driver.execute_script("arguments[0].scrollIntoView(true);", btn)
						sleep(0.1)
						btn.click()
					break
				except:
					sleep(0.5)
					continue

			css = selectors.get(mode)
			for _ in range(15):
				elems = driver.find_elements(By.CSS_SELECTOR, css)
				if elems:
					text = " ".join(e.text.strip() for e in elems if e.text.strip())
					if text:
						qid = url.rstrip("/").split("/")[-1]
						line = f"{qid}. {text}"
						with open(output_file, "a", encoding="utf-8") as f:
							f.write(line + "\n")
						print(line)
						return line
				sleep(0.15)
			print(f"[No Answer] {url}")
			return None

		# -------------------------------------------------- Mode 5 (بدون تغییر)
		else:
			drops = driver.find_elements(By.CSS_SELECTOR, "div.ant-select")
			if not drops:
				print(f"[Warning] No dropdown found for {url}")
				return None

			qid = url.rstrip("/").split("/")[-1]
			lines_to_write = []
			idx = 1

			for drop in drops:
				driver.execute_script("arguments[0].click();", drop)
				sleep(0.5)

			items = driver.find_elements(By.CSS_SELECTOR, "li.ant-select-dropdown-menu-item")
			for li in items:
				text = li.text.strip()
				if text:
					lines_to_write.append(f"{qid}. {idx}. {text}")
				if len(lines_to_write) % 4 == 0:
					idx += 1

			if lines_to_write and output_file:
				with open(output_file, "a", encoding="utf-8") as f:
					f.write("\n".join(lines_to_write) + "\n")
				print("\n".join(lines_to_write))

			return True

	except Exception as e:
		print(f"[Error] {url}: {e}")
		return None


# ---------------------------
# Main program
# ---------------------------
def main():
	mode = input("Enter 1:WFD  2:ASQ  3:RS  4:FIB_WR  5:FIB_WR dropdown => ").strip()
	if mode not in ["1", "2", "3", "4", "5"]:
		print("❌ Only 1–5 are valid.")
		driver.quit()
		return

	mode = int(mode)
	paths = {
		1: (r"WFD\URL 2025-11.txt", r"WFD\Output.txt"),
		2: (r"ASQ\URL 2025-10.txt", r"ASQ\Output.txt"),
		3: (r"RS\URL 2025-10.txt", r"RS\Output.txt"),
		4: (r"FIB_WR\URL 2025-11.txt", r"FIB_WR\Output.txt"),
		5: (r"FIB_WR\URL 2025-11.txt", r"FIB_WR\FIB_WR_Output_Dropdowns.txt")
	}

	input_file, output_file = paths[mode]
	if not os.path.exists(input_file):
		print(f"❌ Input file not found: {input_file}")
		driver.quit()
		return
	if os.path.exists(output_file):
		os.remove(output_file)

	with open(input_file, "r", encoding="utf-8") as f:
		links = [line.strip() for line in f if line.strip()]

	for url in links:
		print(f"Fetching: {url}")
		fetch_answer(url, mode, output_file)

	driver.quit()
	print("✅ Done! Saved to", os.path.abspath(output_file))


if __name__ == "__main__":
	main()
