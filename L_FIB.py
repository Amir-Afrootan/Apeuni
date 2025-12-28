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
MISTAKES_FILE = os.path.join(BASE_DIR, "L_FIB", "Output 2025-12.mistakes.json")

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


# ---------- Mistakes (JSON) ----------

def load_mistakes_all():
    """
    Returns dict: word -> mistakes_count
    Supports both:
      1) {"all": {...}, "top": [...]}
      2) {"word": count, ...}
    """
    if not os.path.exists(MISTAKES_FILE):
        return {}
    try:
        with open(MISTAKES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "all" in data and isinstance(data["all"], dict):
            data = data["all"]
        if not isinstance(data, dict):
            return {}
        return {str(k).lower(): int(v) for k, v in data.items()}
    except Exception:
        return {}


def save_mistakes_all(mistakes_all, top_n=10):
    items = sorted(mistakes_all.items(), key=lambda x: x[1], reverse=True)
    payload = {
        "top": [{"word": w, "mistakes": c} for w, c in items[:top_n] if c > 0],
        "all": mistakes_all
    }
    with open(MISTAKES_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def add_mistake(word):
    mistakes_all = load_mistakes_all()
    key = word.lower()
    mistakes_all[key] = mistakes_all.get(key, 0) + 1
    save_mistakes_all(mistakes_all)


def get_top_mistakes(top_n=10):
    data = load_mistakes_all()
    items = sorted(data.items(), key=lambda x: x[1], reverse=True)
    return [{"word": w, "mistakes": c} for w, c in items[:top_n] if c > 0]


def get_mistake_words():
    data = load_mistakes_all()
    # words that have at least 1 mistake
    words = [w for w, c in data.items() if int(c) > 0]
    return words


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
        # selection mode:
        #   "ordered"  -> full list ordered
        #   "random"   -> full list random
        #   "mistakes" -> only mistaken words (random by default; see pick_word logic)
        session["mode"] = "ordered"
        session["mastered"] = []
        session["streak"] = {}
        session["last_word"] = ""
        session["word"] = WORDS[0] if WORDS else ""

    # allow mode switch via query
    mode_q = request.args.get("mode")
    if mode_q in ("ordered", "random", "mistakes"):
        session["mode"] = mode_q
        # reset session progress on mode switch
        session["mastered"] = []
        session["streak"] = {}
        session["last_word"] = ""
        session["word"] = WORDS[0] if WORDS else ""

    mastered = set(session.get("mastered", []))
    last_word = session.get("last_word", "")
    mode = session.get("mode", "ordered")

    # build active list based on mode
    if mode == "mistakes":
        mistake_words = get_mistake_words()
        # keep only those that exist in WORDS (safety)
        mistake_set = set(w.lower() for w in mistake_words)
        active = [w for w in WORDS if w.lower() in mistake_set and w not in mastered]
    else:
        active = [w for w in WORDS if w not in mastered]

    # if nothing to practice
    if not active:
        if mode == "mistakes":
            message = "<div class='muted'>No mistakes found yet. ✅ Switch to Ordered/Random to practice all words.</div>"
            top_mistakes = get_top_mistakes(10)
            return render_template(
                "index.html",
                word="",
                meaning="",
                message=message,
                mastered=0,
                total=len(WORDS),
                req=REQUIRED_STREAK,
                mode_label="Mistakes Only",
                autoplay=False,
                top_mistakes=top_mistakes
            )
        return render_template("done.html")

    # choose current word (keep if still valid)
    word = session.get("word", "")
    if word not in active:
        # In mistakes mode we want random picks (generally better); in ordered/random use pick_word.
        if mode == "mistakes":
            word = random.choice(active)
        else:
            word = pick_word(active, mode, last_word)

        session["word"] = word
        session["last_word"] = word

    meaning = translate_word(word) if word else ""
    autoplay = session.pop("autoplay", False)
    message = session.pop("message", "")
    top_mistakes = get_top_mistakes(10)

    mode_label = "Mistakes Only" if mode == "mistakes" else ("Ordered" if mode == "ordered" else "Random")

    return render_template(
        "index.html",
        word=word,
        meaning=meaning,
        message=message,
        mastered=len(mastered),
        total=len(WORDS) if mode != "mistakes" else len([w for w in WORDS if w.lower() in set(x.lower() for x in get_mistake_words())]),
        req=REQUIRED_STREAK,
        mode_label=mode_label,
        autoplay=autoplay,
        top_mistakes=top_mistakes
    )


@app.route("/answer", methods=["POST"])
def answer():
    answer_text = request.form.get("answer", "").strip().lower()
    word = session.get("word", "")
    mode = session.get("mode", "ordered")

    if not word:
        return redirect(url_for("index"))

    mastered = set(session.get("mastered", []))
    streak = session.get("streak", {})

    # 🔁 repeat pronunciation
    if answer_text == "-re":
        session["autoplay"] = True
        return redirect(url_for("index"))

    session["autoplay"] = True  # 🔊 auto speak after submit

    if answer_text == word.lower():
        streak[word] = streak.get(word, 0) + 1

        if streak[word] >= REQUIRED_STREAK:
            mastered.add(word)
            session["mastered"] = list(mastered)
            session["message"] = "<div class='ok'>✅ Correct! Mastered.</div>"

            # select next word based on current mode
            if mode == "mistakes":
                mistake_words = get_mistake_words()
                mistake_set = set(w.lower() for w in mistake_words)
                active = [w for w in WORDS if w.lower() in mistake_set and w not in mastered]
                if active:
                    next_word = random.choice(active)
                    session["word"] = next_word
                    session["last_word"] = next_word
            else:
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

    add_mistake(word)

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
