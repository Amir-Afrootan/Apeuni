import os

# ---------------------------
# Input file path
# ---------------------------
input_file = r"WFD\Output.txt"

if not os.path.exists(input_file):
    print("❌ File WFD\\Output.txt not found.")
    exit()

# ---------------------------
# Compare two sentences
# ---------------------------
def compare_sentences(original, typed):
    """Returns number of correct words and list of incorrect words"""
    orig_words = original.strip().split()
    typed_words = typed.strip().split()

    correct_count = 0
    mistakes = []

    for i, word in enumerate(orig_words):
        if i < len(typed_words) and typed_words[i].lower() == word.lower():
            correct_count += 1
        else:
            mistakes.append(word)

    return correct_count, len(orig_words), mistakes

# ---------------------------
# Main program
# ---------------------------
def main():
    total_sentences = 0
    total_correct_words = 0

    with open(input_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    print("📘 WFD Practice - Start\n")

    for line in lines:
        total_sentences += 1
        print(f"\nSentence {total_sentences}:")
        print(f"👉 {line}")
        typed = input("✏️ Please type the sentence: ").strip()

        correct_count, total_words, mistakes = compare_sentences(line, typed)

        print(f"Score Info {correct_count}/{total_words}")

        if mistakes:
            print("Incorrect words:", ", ".join(mistakes))
        else:
            print("✅ Perfect! All words correct.")

    print("\n🏁 Practice Finished!")
    print(f"Total sentences: {total_sentences}")

if __name__ == "__main__":
    main()
