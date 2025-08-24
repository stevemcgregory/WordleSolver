import requests
import sys
import json
import os
from typing import List, Tuple

WORD_LIST_FILE = "words.json"

def fetch_words(filename: str = WORD_LIST_FILE) -> List[str]:
    try:
        # Resolve local path relative to this file unless absolute path is provided
        path = filename
        if not os.path.isabs(path):
            base = os.path.dirname(__file__)
            path = os.path.join(base, path)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Support either a dict with "words" key or a raw list
        if isinstance(data, dict):
            words = data.get("words", [])
        elif isinstance(data, list):
            words = data
        else:
            words = []
        # sanitize: keep only 5-letter alphabetic words, lowercase
        return [w.lower() for w in words if isinstance(w, str) and len(w) == 5 and w.isalpha()]
    except Exception as e:
        print(f"Error fetching word list: {e}", file=sys.stderr)
        return []


def score_word(secret: str, guess: str) -> str:
    """
    Produce Wordle-like feedback for a given secret and guess.
    Returns a 5-char string using:
      - 'g' for green (correct letter in correct position)
      - 'y' for yellow (letter exists elsewhere in secret)
      - 'b' for black/gray (letter not in secret in remaining counts)
    Correctly handles duplicate letters according to Wordle rules.
    """
    secret = secret.lower()
    guess = guess.lower()
    feedback = ['b'] * 5

    # First pass: mark greens and build counts for non-green letters in secret
    from collections import Counter
    remaining_secret_chars = []
    for i in range(5):
        if guess[i] == secret[i]:
            feedback[i] = 'g'
        else:
            remaining_secret_chars.append(secret[i])
    counts = Counter(remaining_secret_chars)

    # Second pass: mark yellows where appropriate
    for i in range(5):
        if feedback[i] == 'g':
            continue
        ch = guess[i]
        if counts.get(ch, 0) > 0:
            feedback[i] = 'y'
            counts[ch] -= 1
        # else remains 'b'

    return ''.join(feedback)


message = (
    "Wordle Solver\n"
    "- Enter a 5-letter guess and the feedback pattern from the game.\n"
    "- Feedback pattern uses: g = green, y = yellow, b = gray.\n"
    "  (You can also use x or . for gray; they will be treated as b.)\n"
    "- Up to 6 attempts. Type 'quit' to exit early.\n"
)


def normalize_feedback(s: str) -> str:
    s = s.strip().lower()
    trans = {'.': 'b', 'x': 'b'}
    s = ''.join(trans.get(c, c) for c in s)
    return s


def matches_feedback(candidate: str, guess: str, feedback: str) -> bool:
    return score_word(candidate, guess) == feedback


def rank_candidates(candidates: List[str]) -> List[str]:
    """
    Rank candidates by how common their letters are across the remaining pool.
    Scoring rule: sum of frequencies of unique letters in the word, computed from
    the current candidate set. Higher is better. Ties broken alphabetically.
    """
    if not candidates:
        return candidates
    from collections import Counter
    letter_freq = Counter()
    for w in candidates:
        # Use unique letters to avoid over-valuing duplicates within a word
        letter_freq.update(set(w))

    def score(w: str) -> int:
        return sum(letter_freq[ch] for ch in set(w))

    return sorted(candidates, key=lambda w: (-score(w), w))


def main():
    print(message)
    candidates = fetch_words()
    if not candidates:
        print("Could not load the word list. Exiting.")
        return

    print(f"Loaded {len(candidates)} candidate words.")

    constraints: List[Tuple[str, str]] = []

    for attempt in range(1, 7):
        # Sort candidates by most common letters before showing preview
        candidates = rank_candidates(candidates)
        # Show a quick preview of current candidates
        preview = ', '.join(candidates[:20])
        print(f"\nAttempt {attempt}/6. Remaining candidates: {len(candidates)}")
        if preview:
            print(f"Examples: {preview}{'...' if len(candidates) > 20 else ''}")

        guess = input("Enter your 5-letter guess (or 'quit'): ").strip().lower()
        if guess in {"quit", "exit"}:
            break
        if len(guess) != 5 or not guess.isalpha():
            print("Invalid guess. Please enter exactly 5 letters.")
            continue

        feedback = input("Enter feedback for that guess (g/y/b, length 5): ").strip()
        feedback = normalize_feedback(feedback)
        if len(feedback) != 5 or any(c not in {'g', 'y', 'b'} for c in feedback):
            print("Invalid feedback. Use 5 characters with only g, y, b (or x/. for gray).")
            continue

        constraints.append((guess, feedback))

        if feedback == 'ggggg':
            print("Solved! Great job.")
            candidates = [guess]
            break

        # Filter candidates against all constraints
        new_candidates = []
        for cand in candidates:
            ok = True
            for g, f in constraints:
                if not matches_feedback(cand, g, f):
                    ok = False

                    break
            if ok:
                new_candidates.append(cand)

        candidates = new_candidates

        # Re-rank after filtering for the next round
        candidates = rank_candidates(candidates)

        if not candidates:
            print("No candidates remain. You may have entered inconsistent feedback.")
            break

    # Final ranking before output
    candidates = rank_candidates(candidates)
    print("\nRemaining candidate words:")
    print(', '.join(candidates) if candidates else '(none)')


if __name__ == '__main__':
    main()