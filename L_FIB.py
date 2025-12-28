import json
import os
import random
import pyttsx3
from deep_translator import GoogleTranslator

WORDS_FILE = r"L_FIB\Output 2025-12.txt"
CACHE_FILE = r"L_FIB\Output 2025-12.meanings.json"

REQUIRED_STREAK = 2


def load_words(path):
    with open(path, "r", encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]

    # remove duplicates while keeping order (optional)
    seen = set()
    unique = []
    for w in words:
        lw = w.lower()
        if lw not in seen:
            seen.add(lw)
            unique.append(w)
    return unique


def load_cache(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {str(k).lower(): str(v) for k, v in data.items()}
    except Exception:
        return {}


def save_cache(path, cache):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def speak(text):
    engine = pyttsx3.init()
    engine.setProperty("rate", 100)
    engine.setProperty("volume", 1.0)
    engine.say(text)
    engine.runAndWait()
    engine.stop()


def normalize(text):
    return text.strip().lower()


def translate_to_fa(word, cache):
    key = word.lower()
    if key in cache and cache[key].strip():
        return cache[key]

    try:
        fa = GoogleTranslator(source="en", target="fa").translate(word)
        if fa:
            cache[key] = fa
            save_cache(CACHE_FILE, cache)
            return fa
    except Exception:
        return None

    return None


def main():
    words = load_words(WORDS_FILE)
    if not words:
        print("❌ No words found in words file!")
        return

    cache = load_cache(CACHE_FILE)

    print("=== English Spelling Trainer ===")
    print("Choose training mode:")
    print("1 - Ordered (from file order)")
    print("2 - Random")
    mode = input("Enter 1 or 2: ").strip()
    if mode not in ("1", "2"):
        mode = "1"
    ordered_mode = (mode == "1")

    print("\nCommands:")
    print("  -r      → repeat pronunciation")
    print("  -s      → show Persian meaning (fetch online if missing)")
    print("  -q      → quit")
    print("-" * 60)

    streak = {w: 0 for w in words}
    mastered = set()
    total_attempts = 0
    last_word = None

    while len(mastered) < len(words):
        active = [w for w in words if w not in mastered]

        # select word
        if ordered_mode:
            word = active[0]
        else:
            word = random.choice(active)
            if len(active) > 1:
                while word == last_word:
                    word = random.choice(active)
        last_word = word

        print(f"\nProgress: {len(mastered)}/{len(words)}")
        speak(word)

        while True:
            user_input = input("Your answer: ").strip()
            cmd = user_input.lower()

            if cmd == "-r":
                speak(word)
                continue

            if cmd == "-s":
                meaning = translate_to_fa(word, cache)
                if meaning:
                    print(f"{word} | {meaning}")
                else:
                    print(f"{word} | (meaning not available right now)")
                continue

            if cmd == "-q":
                print("\nSession ended.")
                return

            # real attempt
            total_attempts += 1

            if normalize(user_input) == normalize(word):
                streak[word] += 1

                if streak[word] >= REQUIRED_STREAK:
                    print(f"✅ Correct! ({streak[word]}/{REQUIRED_STREAK}) → Mastered")
                    mastered.add(word)
                    break
                else:
                    # ask again for the same word (2-in-a-row rule)
                    print(f"✅ Correct! ({streak[word]}/{REQUIRED_STREAK})")
                    speak(word)
                    continue
            else:
                streak[word] = 0
                meaning = translate_to_fa(word, cache)

                if meaning:
                    print(f"❌ Incorrect! Correct spelling: {word} | {meaning}")
                else:
                    print(f"❌ Incorrect! Correct spelling: {word} | (meaning not available)")

                print("Try again (streak reset).")
                speak(word)
                continue

    print("\n🎉 Perfect! You mastered all words.")


if __name__ == "__main__":
    main()
