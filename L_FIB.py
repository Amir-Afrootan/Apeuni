import os
import json
import random
from flask import Flask, request, session, redirect, url_for, render_template
from deep_translator import GoogleTranslator

# =============================
# Paths & App Config
# =============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "L_FIB")  # 👈 HTMLs are here
)
app.secret_key = "change-this-secret"

WORDS_FILE = os.path.join(BASE_DIR, "L_FIB", "Output 2025-12.txt")
CACHE_FILE = os.path.join(BASE_DIR, "L_FIB", "Output 2025-12.meanings.json")

REQUIRED_STREAK = 2


# =============================
# Utilities
# =============================

def load_words(path):
    with open(path, "r", encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]

    seen = set()
    result = []
    for w in words:
        lw = w.lower()
        if lw not in seen:
            seen.add(lw)
            result.append(w)
    return result


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k.lower(): v for k, v in data.items()}
    except Exception:
        return {}


def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def translate_word(word):
    cache = load_cache()
    key = word.lower()

    if key in cache and cache[key]:
        return cache[key]

    try:
        fa = GoogleTranslator(source="en", target="fa").translate(word)
        if fa:
            cache[key] = fa
            save_cache(cache)
            return fa
    except:
        pass

    return "(meaning not available)"


def pick_word(active, mode, last_word):
    if mode == "ordered":
        return active[0]
    w = random.choice(active)
    if len(active) > 1:
        while w == last_word:
            w = random.choice(active)
    return w


# =============================
# Load words
# =============================

WORDS = load_words(WORDS_FILE)


# =============================
# Routes
# =============================

@app.route("/")
def index():
    if "mode" not in session:
        session["mode"] = "ordered"
        session["mastered"] = []
        session["streak"] = {}
        session["last_word"] = ""
        session["word"] = WORDS[0] if WORDS else ""

    mode = request.args.get("mode")
    if mode in ("ordered", "random"):
        session["mode"] = mode
        session["mastered"] = []
        session["streak"] = {}
        session["last_word"] = ""
        session["word"] = WORDS[0]

    mastered = set(session.get("mastered", []))
    streak = session.get("streak", {})
    last_word = session.get("last_word", "")
    mode = session.get("mode", "ordered")

    active = [w for w in WORDS if w not in mastered]
    if not active:
        return render_template("done.html")

    word = session.get("word")
    if word not in active:
        word = pick_word(active, mode, last_word)
        session["word"] = word
        session["last_word"] = word

    meaning = translate_word(word)
    autoplay = session.pop("autoplay", False)
    message = session.pop("message", "")

    return render_template(
        "index.html",
        word=word,
        meaning=meaning,
        message=message,
        mastered=len(mastered),
        total=len(WORDS),
        req=REQUIRED_STREAK,
        mode_label="Ordered" if mode == "ordered" else "Random",
        autoplay=autoplay
    )


@app.route("/answer", methods=["POST"])
def answer():
    answer = request.form.get("answer", "").strip().lower()
    word = session.get("word", "")

    mastered = set(session.get("mastered", []))
    streak = session.get("streak", {})

    session["autoplay"] = True  # 🔊 auto speak after submit

    if answer == word.lower():
        streak[word] = streak.get(word, 0) + 1

        if streak[word] >= REQUIRED_STREAK:
            mastered.add(word)
            session["mastered"] = list(mastered)
            session["message"] = "<div class='ok'>✅ Correct! Mastered.</div>"

            mode = session.get("mode", "ordered")
            active = [w for w in WORDS if w not in mastered]
            if active:
                next_word = pick_word(active, mode, session.get("last_word", ""))
                session["word"] = next_word
                session["last_word"] = next_word
        else:
            session["message"] = f"<div class='ok'>✅ Correct! ({streak[word]}/{REQUIRED_STREAK})</div>"

        session["streak"] = streak
        return redirect(url_for("index"))

    # ❌ Wrong answer
    streak[word] = 0
    session["streak"] = streak

    meaning = translate_word(word)
    session["message"] = (
        f"<div class='bad'>❌ Incorrect! Correct spelling: "
        f"<b>{word}</b> | <span class='fa'>{meaning}</span></div>"
    )

    return redirect(url_for("index"))


# =============================
# Run
# =============================

if __name__ == "__main__":
    if not WORDS:
        print("❌ No words found in Output file.")
    else:
        app.run(debug=True)
