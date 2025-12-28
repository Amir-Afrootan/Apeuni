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
    Returns dict: word -> count
    Supports:
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


def add_mistake(word, delta=1):
    """
    delta=+1 for wrong, delta=-1 for correct in mistakes-mode (clamped to 0).
    """
    mistakes_all = load_mistakes_all()
    key = word.lower()
    cur = int(mistakes_all.get(key, 0))
    cur += int(delta)

    # ✅ clamp (do not go negative)
    if cur < 0:
        cur = 0

    mistakes_all[key] = cur
    save_mistakes_all(mistakes_all)


def get_top_mistakes(top_n=10):
    data = load_mistakes_all()
    items = sorted(data.items(), key=lambda x: x[1], reverse=True)
    return [{"word": w, "mistakes": c} for w, c in items[:top_n] if c > 0]


# =============================
# Mistakes-mode selection logic (circular traversal)
# =============================

def any_positive_mistakes():
    data = load_mistakes_all()
    return any(int(v) > 0 for v in data.values())


def get_next_mistake_word():
    """
    Circularly walks through mistakes_all keys and returns the next word with count>0.
    Keeps pointer in session['mistake_pos'].
    Returns "" if none positive.
    """
    mistakes_all = load_mistakes_all()
    if not mistakes_all:
        return ""

    # fixed order of traversal: order in file (dict insertion order)
    keys = list(mistakes_all.keys())
    if not keys:
        return ""

    # start position
    pos = int(session.get("mistake_pos", 0))
    pos = pos % len(keys)

    # scan at most len(keys) to find a positive count
    for _ in range(len(keys)):
        w = keys[pos]
        cnt = int(mistakes_all.get(w, 0))
        if cnt > 0:
            # keep pos at the selected word (so after correct we can move to next)
            session["mistake_pos"] = pos
            return w
        pos = (pos + 1) % len(keys)

    return ""


def advance_mistake_pos():
    mistakes_all = load_mistakes_all()
    keys = list(mistakes_all.keys())
    if not keys:
        session["mistake_pos"] = 0
        return
    pos = int(session.get("mistake_pos", 0))
    session["mistake_pos"] = (pos + 1) % len(keys)


# =============================
# Load words
# =============================

WORDS = load_words(WORDS_FILE)


# =============================
# Routes
# =============================

@app.route("/")
def index():
    if not WORDS:
        return "❌ No words found in Output file."

    if "mode" not in session:
        session["mode"] = "ordered"
        session["mastered"] = []
        session["streak"] = {}
        session["last_word"] = ""
        session["word"] = WORDS[0]
        session["mistake_pos"] = 0

    # allow mode switch via query (no forced reset here)
    mode_q = request.args.get("mode")
    if mode_q in ("ordered", "random", "mistakes"):
        session["mode"] = mode_q
        # NOTE: we keep progress; no reset

    mode = session.get("mode", "ordered")
    mastered = set(session.get("mastered", []))
    last_word = session.get("last_word", "")

    # ---- Mistakes mode word selection ----
    if mode == "mistakes":
        # pick next positive-count mistake word (circular)
        word = session.get("word", "")
        # If current word is empty or its count is no longer positive, find next
        mistakes_all = load_mistakes_all()
        if (not word) or (int(mistakes_all.get(word.lower(), 0)) <= 0):
            word = get_next_mistake_word()
            session["word"] = word

        if not word:
            # no positive mistakes left
            top_mistakes = get_top_mistakes(10)
            message = "<div class='muted'>🎉 No remaining mistakes (positive counts). ✅ Switch to Ordered/Random to continue.</div>"
            return render_template(
                "index.html",
                word="",
                meaning="",
                message=message,
                mastered=0,
                total=0,
                req=REQUIRED_STREAK,
                mode_label="Mistakes Only",
                autoplay=False,
                top_mistakes=top_mistakes
            )

        meaning = translate_word(word)
        autoplay = session.pop("autoplay", False)
        message = session.pop("message", "")
        top_mistakes = get_top_mistakes(10)

        return render_template(
            "index.html",
            word=word,
            meaning=meaning,
            message=message,
            mastered=0,             # not used in mistakes loop
            total=0,                # not used in mistakes loop
            req=REQUIRED_STREAK,
            mode_label="Mistakes Only",
            autoplay=autoplay,
            top_mistakes=top_mistakes
        )

    # ---- Normal modes (ordered/random) ----
    active = [w for w in WORDS if w not in mastered]
    if not active:
        return render_template("done.html")

    word = session.get("word", "")
    if word not in active:
        word = pick_word(active, mode, last_word)
        session["word"] = word
        session["last_word"] = word

    meaning = translate_word(word)
    autoplay = session.pop("autoplay", False)
    message = session.pop("message", "")
    top_mistakes = get_top_mistakes(10)

    mode_label = "Ordered" if mode == "ordered" else "Random"

    return render_template(
        "index.html",
        word=word,
        meaning=meaning,
        message=message,
        mastered=len(mastered),
        total=len(WORDS),
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

    # 🔁 repeat pronunciation (all modes)
    if answer_text == "-re":
        session["autoplay"] = True
        return redirect(url_for("index"))

    session["autoplay"] = True  # 🔊 auto speak after submit

    # ✅ Correct
    if answer_text == word.lower():

        if mode == "mistakes":
            # In mistakes mode: decrement counter by 1 (clamped to 0), then move to next word
            add_mistake(word, delta=-1)
            session["message"] = "<div class='ok'>✅ Correct! (mistake count -1)</div>"

            # move pointer forward and choose next positive word on next page
            advance_mistake_pos()
            session["word"] = ""  # force next selection
            return redirect(url_for("index"))

        # Normal modes: streak logic
        mastered = set(session.get("mastered", []))
        streak = session.get("streak", {})

        streak[word] = streak.get(word, 0) + 1

        if streak[word] >= REQUIRED_STREAK:
            mastered.add(word)
            session["mastered"] = list(mastered)
            session["message"] = "<div class='ok'>✅ Correct! Mastered.</div>"

            active = [w for w in WORDS if w not in mastered]
            if active:
                next_word = pick_word(active, mode, session.get("last_word", ""))
                session["word"] = next_word
                session["last_word"] = next_word
        else:
            session["message"] = f"<div class='ok'>✅ Correct! ({streak[word]}/{REQUIRED_STREAK})</div>"

        session["streak"] = streak
        return redirect(url_for("index"))

    # ❌ Wrong (all modes): increment counter + reset streak
    if mode != "mistakes":
        streak = session.get("streak", {})
        streak[word] = 0
        session["streak"] = streak

    add_mistake(word, delta=+1)

    meaning = translate_word(word)
    session["message"] = (
        f"<div class='bad'>❌ Incorrect! Correct spelling: "
        f"<b>{word}</b> | <span class='fa'>{meaning}</span></div>"
    )

    # In mistakes mode, keep the same word (so user can try again),
    # and since autoplay=True it will be spoken again.
    return redirect(url_for("index"))


# =============================
# Run
# =============================

if __name__ == "__main__":
    if not WORDS:
        print("❌ No words found in Output file.")
    else:
        app.run(debug=True)
