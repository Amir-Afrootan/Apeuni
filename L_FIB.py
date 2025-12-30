import os
import json
import random
from flask import Flask, request, session, redirect, url_for, render_template
from deep_translator import GoogleTranslator
from markupsafe import escape

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "L_FIB"))
app.secret_key = "change-this-secret"

WORDS_FILE = os.path.join(BASE_DIR, "L_FIB", "Output 2025-12.txt")
CACHE_FILE = os.path.join(BASE_DIR, "L_FIB", "Output 2025-12.meanings.json")
MISTAKES_FILE = os.path.join(BASE_DIR, "L_FIB", "Output 2025-12.mistakes.json")

REQUIRED_STREAK = 2


def load_words(path):
	with open(path, "r", encoding="utf-8") as f:
		words = [w.strip() for w in f if w.strip()]
	seen, result = set(), []
	for w in words:
		if w.lower() not in seen:
			seen.add(w.lower())
			result.append(w)
	return result


def load_cache():
	if not os.path.exists(CACHE_FILE):
		return {}
	try:
		with open(CACHE_FILE, "r", encoding="utf-8") as f:
			return {k.lower(): v for k, v in json.load(f).items()}
	except Exception:
		return {}


def save_cache(cache):
	with open(CACHE_FILE, "w", encoding="utf-8") as f:
		json.dump(cache, f, ensure_ascii=False, indent=2)


def translate_word(word):
	cache = load_cache()
	key = word.lower()

	if key in cache:
		return cache[key]

	try:
		fa = GoogleTranslator(source="en", target="fa").translate(word)
		cache[key] = fa
		save_cache(cache)
		return fa
	except Exception:
		return "(meaning not available)"


def pick_word(active, mode, last_word):
	if mode == "ordered":
		return active[0]
	w = random.choice(active)
	while len(active) > 1 and w == last_word:
		w = random.choice(active)
	return w


def load_mistakes_all():
	if not os.path.exists(MISTAKES_FILE):
		return {}
	try:
		with open(MISTAKES_FILE, "r", encoding="utf-8") as f:
			data = json.load(f)
		if "all" in data:
			data = data["all"]
		return {k.lower(): int(v) for k, v in data.items()}
	except Exception:
		return {}


def save_mistakes_all(mistakes):
	payload = {
		"top": [{"word": w, "mistakes": c} for w, c in sorted(mistakes.items(), key=lambda x: x[1], reverse=True) if c > 0],
		"all": mistakes
	}
	with open(MISTAKES_FILE, "w", encoding="utf-8") as f:
		json.dump(payload, f, ensure_ascii=False, indent=2)


def add_mistake(word, delta):
	data = load_mistakes_all()
	key = word.lower()
	data[key] = max(0, int(data.get(key, 0)) + delta)
	save_mistakes_all(data)


def get_top_mistakes():
	return [{"word": w, "mistakes": c} for w, c in load_mistakes_all().items() if c > 0]


def get_next_mistake_word():
	data = load_mistakes_all()
	keys = list(data.keys())
	if not keys:
		return ""

	pos = session.get("mistake_pos", 0) % len(keys)
	for _ in range(len(keys)):
		w = keys[pos]
		if data.get(w, 0) > 0:
			session["mistake_pos"] = pos
			return w
		pos = (pos + 1) % len(keys)
	return ""


def advance_mistake_pos():
	data = load_mistakes_all()
	keys = list(data.keys())
	if not keys:
		session["mistake_pos"] = 0
		return
	session["mistake_pos"] = (session.get("mistake_pos", 0) + 1) % len(keys)


WORDS = load_words(WORDS_FILE)


@app.route("/")
def index():
	if not WORDS:
		return "No words found."

	if "mode" not in session:
		session.update({
			"mode": "ordered",
			"mastered": [],
			"streak": {},
			"last_word": "",
			"word": WORDS[0],
			"mistake_pos": 0
		})

	mode = session.get("mode")

	if request.args.get("mode") in ("ordered", "random", "mistakes"):
		session["mode"] = request.args["mode"]

	mistakes_all = load_mistakes_all()
	misspelled_words_count = sum(1 for c in mistakes_all.values() if c > 0)

	if mode == "mistakes":
		word = session.get("word", "")
		if not word or mistakes_all.get(word, 0) <= 0:
			word = get_next_mistake_word()
			session["word"] = word
			session["mistakes_streak"] = 0

		if not word:
			return render_template(
				"index.html",
				word="",
				meaning="",
				message="🎉 No remaining mistakes",
				mode_label="Mistakes Only",
				top_mistakes=[],
				misspelled_words_count=0
			)

		return render_template(
			"index.html",
			word=word,
			meaning=translate_word(word),
			message=session.pop("message", ""),
			mode_label="Mistakes Only",
			top_mistakes=get_top_mistakes(),
			misspelled_words_count=misspelled_words_count,
			autoplay=session.pop("autoplay", False)
		)

	mastered = set(session.get("mastered", []))
	active = [w for w in WORDS if w not in mastered]

	if not active:
		return render_template("done.html")

	word = session.get("word")
	if word not in active:
		word = pick_word(active, mode, session.get("last_word", ""))
		session["word"] = word
		session["last_word"] = word

	return render_template(
		"index.html",
		word=word,
		meaning=translate_word(word),
		message=session.pop("message", ""),
		mastered=len(mastered),
		total=len(WORDS),
		req=REQUIRED_STREAK,
		mode_label=mode.capitalize(),
		top_mistakes=get_top_mistakes(),
		misspelled_words_count=misspelled_words_count,
		autoplay=session.pop("autoplay", False)
	)


@app.route("/answer", methods=["POST"])
def answer():
	word = session.get("word", "")
	mode = session.get("mode")
	answer = request.form.get("answer", "").strip().lower()

	if answer == "-re":
		session["autoplay"] = True
		return redirect(url_for("index"))

	if answer == word.lower():
		if mode == "mistakes":
			streak = session.get("mistakes_streak", 0) + 1
			session["mistakes_streak"] = streak

			if streak < REQUIRED_STREAK:
				session["message"] = f"✅ Correct ({streak}/{REQUIRED_STREAK})"
				return redirect(url_for("index"))

			add_mistake(word, -1)
			session["mistakes_streak"] = 0
			session["word"] = ""
			advance_mistake_pos()
			session["message"] = "✅ Correct! Count reduced."
			return redirect(url_for("index"))

		streaks = session.get("streak", {})
		streaks[word] = streaks.get(word, 0) + 1

		if streaks[word] >= REQUIRED_STREAK:
			session.setdefault("mastered", []).append(word)

		session["streak"] = streaks
		session["message"] = "✅ Correct"
		return redirect(url_for("index"))

	add_mistake(word, +1)
	session["mistakes_streak"] = 0
	session["message"] = f"❌ Your answer : {escape(answer)} <br/> ✔ Correct word: {word}"
	return redirect(url_for("index"))


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=5000, debug=True)
