import requests
import sys
import json
import os
from typing import List, Tuple
from functools import lru_cache
from collections import defaultdict, Counter
from math import log2

# --- keep your score_word as-is ---

WORD_LIST_FILE = "words.json"

def fetch_words(filename: str = WORD_LIST_FILE) -> List[str]:
    try:
        path = filename
        if not os.path.isabs(path):
            base = os.path.dirname(__file__) if "__file__" in globals() else os.getcwd()
            path = os.path.join(base, path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        words = data.get("words", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        # sanitize + dedupe
        ws = sorted(set(w.lower() for w in words if isinstance(w, str) and len(w) == 5 and w.isalpha()))
        return ws
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

@lru_cache(maxsize=None)
def _pattern_cached(secret: str, guess: str) -> str:
    return score_word(secret, guess)

def bucket_stats(guess: str, candidates: List[str]) -> tuple[int, float, float]:
    buckets = defaultdict(int)
    for s in candidates:
        buckets[_pattern_cached(s, guess)] += 1
    counts = list(buckets.values())
    n = len(candidates)
    bmax = max(counts)
    expected = sum(c*c for c in counts) / n
    # entropy tiebreak: prefer higher entropy => sort by -entropy
    probs = (c / n for c in counts)
    ent = 0.0
    for p in probs:
        if p > 0:
            ent -= p * log2(p)
    return bmax, expected, ent

def _letter_freq_score_pool(S: List[str]):
    from collections import Counter
    freq = Counter()
    for w in S:
        freq.update(set(w))
    def cover_score(w: str) -> int:
        return sum(freq[ch] for ch in set(w))
    return cover_score

def rank_candidates_minimax(G: List[str], S: List[str]) -> list[tuple[str, tuple]]:
    scored = []
    for g in G:
        bmax, expected, ent = bucket_stats(g, S)
        scored.append((g, (bmax, expected, -ent, g)))  # minimize bmax, expected, -entropy, then alpha
    scored.sort(key=lambda x: x[1])
    return scored

def choose_guess(candidates: List[str], guess_pool: List[str] | None = None):
    S = candidates
    if not S:
        return ""
    # Allow a larger probe pool if provided; else just S.
    G = list(set(guess_pool)) if guess_pool else S

    # Two-stage pruning to cut O(|G||S|):
    cover_score = _letter_freq_score_pool(S)
    K = 300 if len(S) > 2000 else 150 if len(S) > 500 else len(G)
    G_pruned = sorted(G, key=lambda w: -cover_score(w))[:min(K, len(G))]

    order = rank_candidates_minimax(G_pruned, S)
    return order if order else ""

def normalize_feedback(s: str) -> str:
    s = s.strip().lower()
    return ''.join({'x':'b','.':'b'}.get(c, c) for c in s)

def matches_feedback(candidate: str, guess: str, feedback: str) -> bool:
    return _pattern_cached(candidate, guess) == feedback

def main():
    candidates = fetch_words()
    if not candidates:
        print("Could not load the word list. Exiting.")
        return

    print(f"Loaded {len(candidates)} candidate words. Printing Top 5 Suggested Guesses:")

    constraints: List[Tuple[str, str]] = []

    # Initial suggestions with caching in initial_guess.json
    try:
        base_dir = os.path.dirname(__file__) if "__file__" in globals() else os.getcwd()
        cache_path = os.path.join(base_dir, "initial_guess.json")
    except Exception:
        cache_path = "initial_guess.json"

    initial_guesses: List[str] | None = None
    # If file exists, try to read list from it
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and all(isinstance(x, str) for x in data):
                initial_guesses = data
        except Exception as e:
            print(f"Warning: could not read initial guesses cache: {e}")
            initial_guesses = None

    # If not present or invalid, compute and write top 5
    if initial_guesses is None:
        probe_pool = candidates  # or a larger list you load separately
        ranked = choose_guess(candidates, guess_pool=probe_pool)
        top = [ranked[i][0] for i in range(min(5, len(ranked)))] if ranked else []
        initial_guesses = top
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(initial_guesses, f)
        except Exception as e:
            print(f"Warning: could not write initial guesses cache: {e}")

    # Print the initial guesses (up to 5)
    for guess in initial_guesses[:5]:
        print(f"{guess}")

    print(message)

    for attempt in range(1, 7):
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
        if not candidates:
            print("No candidates remain. You may have entered inconsistent feedback.")
            break

        # Choose from probe pool when large; else from S only
        probe_pool = candidates  # or a larger list you load separately
        best_guess = choose_guess(candidates, guess_pool=probe_pool)
        for i in range(min(5,len(best_guess))):
            print(f"Suggested guess: {best_guess[i][0]}")


    # After filtering:
    # candidates = [ ... filtered as you do ... ]

if __name__ == '__main__':
    main()