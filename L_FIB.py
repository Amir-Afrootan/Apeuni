import os
import json
import random
import uuid
import tempfile
from flask import Flask, request, session, redirect, url_for, render_template, make_response
from deep_translator import GoogleTranslator
from markupsafe import escape

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "L_FIB"))
app.secret_key = "change-this-secret"

WORDS_FILE = os.path.join(BASE_DIR, "L_FIB", "Output 2025-12.txt")
CACHE_FILE = os.path.join(BASE_DIR, "L_FIB", "Output 2025-12.meanings.json")
MISTAKES_FILE = os.path.join(BASE_DIR, "L_FIB", "Output 2025-12.mistakes.json")

REQUIRED_STREAK = 2

# -----------------------------
# NEW: per-user mistakes storage (cookie + per-user directory)
# -----------------------------
USER_ID_COOKIE = "l_fib_user_id"
USERS_DIR = os.path.join(BASE_DIR, "L_FIB", "users")


def _ensure_dir(path: str) -> None:
	os.makedirs(path, exist_ok=True)


def _atomic_write_json(path: str, data) -> None:
	"""Write JSON atomically to avoid corrupt files on concurrent writes."""
	_ensure_dir(os.path.dirname(path))
	fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", suffix=".json", dir=os.path.dirname(path))
	try:
		with os.fdopen(fd, "w", encoding="utf-8") as f:
			json.dump(data, f, ensure_ascii=False, indent=2)
		os.replace(tmp_path, path)
	finally:
		try:
			if os.path.exists(tmp_path):
				os.remove(tmp_path)
		except Exception:
			pass


def get_user_id():
	"""
	Stable identity per browser via cookie.
	If cookie missing, create a new UUID.
	"""
	uid = request.cookies.get(USER_ID_COOKIE)
	if uid and len(uid) >= 8:
		return uid
	return str(uuid.uuid4())


def get_user_mistakes_file():
	"""
	per-user mistakes path:
	L_FIB/users/<user_id>/Output 2025-12.mistakes.json

	NOTE:
	- We keep MISTAKES_FILE variable untouched (not removed/renamed),
	  but we don't use it for storage anymore.
	"""
	user_id = get_user_id()
	user_dir = os.path.join(USERS_DIR, user_id)
	_ensure_dir(user_dir)
	return os.path.join(user_dir, os.path.basename(MISTAKES_FILE))


# -----------------------------
# Original logic (unchanged names / behavior)
# -----------------------------
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
	# CHANGED: use per-user mistakes file instead of shared MISTAKES_FILE
	path = get_user_mistakes_file()

	if not os.path.exists(path):
		return {}
	try:
		with open(path, "r", encoding="utf-8") as f:
			data = json.load(f)
		if "all" in data:
			data = data["all"]
		return {k.lower(): int(v) for k, v in data.items()}
	except Exception:
		return {}


def save_mistakes_all(mistakes):
	# CHANGED: use per-user mistakes file instead of shared MISTAKES_FILE
	path = get_user_mistakes_file()

	payload = {
		"top": [{"word": w, "mistakes": c} for w, c in sorted(mistakes.items(), key=lambda x: x[1], reverse=True) if c > 0],
		"all": mistakes
	}

	# Use atomic write to avoid corruption on concurrent writes
	_atomic_write_json(path, payload)


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


def _resp_with_user_cookie(html_or_response):
	"""
	Ensure the user_id cookie is set.
	- If html_or_response is a string/html, wrap it in make_response.
	- If already a Response, just set cookie.
	"""
	user_id = get_user_id()

	if hasattr(html_or_response, "set_cookie"):
		resp = html_or_response
	else:
		resp = make_response(html_or_response)

	# Set cookie if missing or different
	if request.cookies.get(USER_ID_COOKIE) != user_id:
		resp.set_cookie(
			USER_ID_COOKIE,
			user_id,
			max_age=60 * 60 * 24 * 365 * 2,  # 2 years
			httponly=True,
			samesite="Lax",
		)
	return resp


@app.route("/")
def index():
	if not WORDS:
		return "No words found."

	# Ensure per-user directory exists early (so mistakes file can be created later)
	_ = get_user_mistakes_file()

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
			html = render_template(
				"index.html",
				word="",
				meaning="",
				message="🎉 No remaining mistakes",
				mode_label="Mistakes Only",
				top_mistakes=[],
				misspelled_words_count=0
			)
			return _resp_with_user_cookie(html)

		html = render_template(
			"index.html",
			word=word,
			meaning=translate_word(word),
			message=session.pop("message", ""),
			mode_label="Mistakes Only",
			top_mistakes=get_top_mistakes(),
			misspelled_words_count=misspelled_words_count,
			autoplay=session.pop("autoplay", False)
		)
		return _resp_with_user_cookie(html)

	mastered = set(session.get("mastered", []))
	active = [w for w in WORDS if w not in mastered]

	if not active:
		html = render_template("done.html")
		return _resp_with_user_cookie(html)

	word = session.get("word")
	if word not in active:
		word = pick_word(active, mode, session.get("last_word", ""))
		session["word"] = word
		session["last_word"] = word

	html = render_template(
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
	return _resp_with_user_cookie(html)


@app.route("/answer", methods=["POST"])
def answer():
	# Ensure per-user directory exists early (so mistakes file can be created later)
	_ = get_user_mistakes_file()

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
