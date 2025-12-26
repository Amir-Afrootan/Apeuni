import random
import pyttsx3

FILE_PATH = r"L_FIB\Output 2025-12.txt"
REQUIRED_STREAK = 2  # must be correct this many times in a row to master


def load_words(path):
    with open(path, "r", encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]
    # Optional: remove duplicates while keeping order
    seen = set()
    unique_words = []
    for w in words:
        lw = w.lower()
        if lw not in seen:
            seen.add(lw)
            unique_words.append(w)
    return unique_words


def speak(text):
    engine = pyttsx3.init()
    engine.setProperty("rate", 100)
    engine.setProperty("volume", 1.0)
    engine.say(text)
    engine.runAndWait()
    engine.stop()


def normalize(text):
    return text.strip().lower()


def print_stats(wrong_counts, total_words):
    print("\n=== Mistake Stats ===")
    # show only words with mistakes, sorted by most mistakes
    items = [(w, c) for w, c in wrong_counts.items() if c > 0]
    if not items:
        print("No mistakes so far. ✅")
        return

    items.sort(key=lambda x: x[1], reverse=True)
    for w, c in items:
        print(f"{w}: {c} mistake(s)")
    print(f"Words with at least 1 mistake: {len(items)}/{total_words}")


def main():
    words = load_words(FILE_PATH)
    if not words:
        print("❌ No words found in file!")
        return

    print("=== English Spelling Trainer (2-in-a-row + stats) ===")
    print(f"Loaded {len(words)} words from: {FILE_PATH}")
    print("Rules: You must spell the current word correctly 2 times in a row to master it.")
    print("Commands:")
    print("  -r      → repeat pronunciation")
    print("  -s      → show word")
    print("  -stats  → show mistake stats")
    print("  -q      → quit")
    print("-" * 70)

    wrong_counts = {w: 0 for w in words}
    streak = {w: 0 for w in words}  # consecutive correct count for each word
    mastered = set()

    total_attempts = 0
    last_word = None

    def progress_text():
        return f"Progress: {len(mastered)}/{len(words)}"

    while len(mastered) < len(words):
        # pick among not-mastered words
        active = [w for w in words if w not in mastered]
        word = random.choice(active)

        # avoid immediate repeat if possible
        if len(active) > 1:
            while word == last_word:
                word = random.choice(active)
        last_word = word

        # Start this word session
        print(f"\n{progress_text()}")

        speak(word)

        while True:
            user_input = input("Your answer: ").strip()
            cmd = user_input.lower()

            if cmd == "-r":
                speak(word)
                continue

            if cmd == "-s":
                print(f"Word: {word}")
                continue

            if cmd == "-stats":
                print_stats(wrong_counts, len(words))
                continue

            if cmd == "-q":
                print("\nSession ended.")
                print(progress_text())
                print(f"Total attempts: {total_attempts}")
                print_stats(wrong_counts, len(words))
                return

            # Real attempt
            total_attempts += 1

            if normalize(user_input) == normalize(word):
                streak[word] += 1

                if streak[word] >= REQUIRED_STREAK:
                    mastered.add(word)
                    print(f"✅ Correct! ({streak[word]}/{REQUIRED_STREAK}) → Mastered! Moving on.")
                    break
                else:
                    # Need one more correct in a row
                    print(f"✅ Correct! ({streak[word]}/{REQUIRED_STREAK})")
                    print("Type it again to confirm (must be correct twice in a row).")
                    speak(word)  # play again for the confirmation attempt
                    continue

            else:
                wrong_counts[word] += 1
                streak[word] = 0  # reset streak on mistake
                print(f"❌ Incorrect! Correct spelling: {word}")
                print("Try again (streak reset).")
                speak(word)  # replay sound after mistake
                continue

    print("\n🎉 Perfect! You mastered all words (2 correct in a row each).")
    print(f"Total attempts: {total_attempts}")
    print_stats(wrong_counts, len(words))


if __name__ == "__main__":
    main()
