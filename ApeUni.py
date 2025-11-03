import os
import time
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By


# ---------------------------
# Setup Edge driver
# ---------------------------
selenium_profile_path = r"D:\Programming\Python\Apeuni\EdgeSeleniumProfile"
os.makedirs(selenium_profile_path, exist_ok=True)

edge_options = Options()
edge_options.add_argument(f"user-data-dir={selenium_profile_path}")
edge_options.add_experimental_option("excludeSwitches", ["enable-logging"])
# edge_options.add_argument("--headless")  # برای اجرای بدون مرورگر

service = Service(r"msedgedriver.exe")
driver = webdriver.Edge(service=service, options=edge_options)


# ---------------------------
# General function for all 4 modes
# ---------------------------
def fetch_answer(url, mode):
	"""
	mode:
	  1 -> WFD
	  2 -> ASQ
	  3 -> RS
	  4 -> FIB_WR
	"""

	selectors = {
		1: "p.Answer__Paragraph-h0b1cq-4",						# WFD
		2: "p.Answer__AnswerText-h0b1cq-0",						# ASQ
		3: "p[class^='Answer__Paragraph-']",					# RS
		4: ".fupsWk div:nth-child(2) p span:nth-child(even)"	# FIB_WR
	}

	try:
		driver.get(url)

		# فعال کردن Answer Switch
		for _ in range(6):
			try:
				btn = driver.find_element(By.CSS_SELECTOR, "button.ant-switch")
				if btn.get_attribute("aria-checked") == "false":
					btn.click()
					time.sleep(0.4)
				break
			except Exception:
				time.sleep(0.3)

		# واکشی جواب
		css = selectors.get(mode)
		if not css:
			print(f"[Error] Invalid mode: {mode}")
			return None

		# واکشی داده‌ها
		for _ in range(40):
			elems = driver.find_elements(By.CSS_SELECTOR, css)
			if elems:
				text = " ".join(e.text.strip() for e in elems if e.text.strip())
				if text:
					qid = url.rstrip("/").split("/")[-1]
					return f"{qid}. {text}"

			time.sleep(0.25)

		print(f"[Warning] No answer found for {url}")
		return None

	except Exception as e:
		print(f"[Error] {url}: {e}")
		return None


# ---------------------------
# Main program
# ---------------------------
def main():
	mode = input("Enter 1:WFD  2:ASQ  3:RS  4:FIB_WR => ").strip()
	if mode not in ["1", "2", "3", "4"]:
		print("❌ Only 1–4 are valid.")
		driver.quit()
		return

	mode = int(mode)
	paths = {
		1: (r"WFD\URL 2025-11.txt", r"WFD\Output.txt"),
		2: (r"ASQ\URL 2025-10.txt", r"ASQ\Output.txt"),
		3: (r"RS\URL 2025-10.txt", r"RS\Output.txt"),
		4: (r"FIB_WR\URL 2025-11.txt", r"FIB_WR\Output.txt"),
	}

	input_file, output_file = paths[mode]

	if os.path.exists(output_file):
		os.remove(output_file)

	# خواندن لینک‌ها از فایل ورودی
	with open(input_file, "r", encoding="utf-8") as f:
		links = [line.strip() for line in f if line.strip()]

	# واکشی و ذخیره جواب‌ها
	for url in links:
		print(f"Fetching: {url}")
		result = fetch_answer(url, mode) or f"[No Answer] {url}"
		print(result)

		with open(output_file, "a", encoding="utf-8") as f:
			f.write(result + "\n")

		time.sleep(0.3)

	driver.quit()
	print("✅ Done! Saved to", os.path.abspath(output_file))


if __name__ == "__main__":
	main()
