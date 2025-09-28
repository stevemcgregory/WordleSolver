import os
import json
from typing import List, Tuple

import streamlit as st

from main import (
    fetch_words,
    choose_guess,
    normalize_feedback,
    matches_feedback,
)


def filter_candidates(candidates: List[str], constraints: List[Tuple[str, str]]) -> List[str]:
    if not constraints:
        return candidates
    new_candidates: List[str] = []
    for cand in candidates:
        ok = True
        for g, f in constraints:
            if not matches_feedback(cand, g, f):
                ok = False
                break
        if ok:
            new_candidates.append(cand)
    return new_candidates


def get_initial_guesses(candidates: List[str]) -> List[str]:
    # Use same cache strategy as CLI
    try:
        base_dir = os.path.dirname(__file__) if "__file__" in globals() else os.getcwd()
        cache_path = os.path.join(base_dir, "initial_guess.json")
    except Exception:
        cache_path = "initial_guess.json"

    initial_guesses: List[str] | None = None
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and all(isinstance(x, str) for x in data):
                initial_guesses = data
        except Exception:
            initial_guesses = None

    if initial_guesses is None:
        ranked = choose_guess(candidates, guess_pool=candidates)
        initial_guesses = [ranked[i][0] for i in range(min(5, len(ranked)))] if ranked else []
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(initial_guesses, f)
        except Exception:
            pass

    return initial_guesses[:5]


def main():
    st.set_page_config(page_title="Wordle Solver", page_icon="🧩", layout="centered")

    st.title("Wordle Solver 🧩")
    st.write(
        "Enter your guesses and the feedback pattern from Wordle to narrow down candidates and get suggestions."
    )
    with st.expander("How to use"):
        st.markdown(
            "- Guess must be a 5-letter word.\n"
            "- Feedback pattern uses: g = green, y = yellow, b = gray.\n"
            "  (You can also use x or . for gray; they will be treated as b.)\n"
            "- Add up to 6 attempts, or reset to start over."
        )

    # Load candidates once
    if "all_words" not in st.session_state:
        st.session_state.all_words = fetch_words()
    all_words: List[str] = st.session_state.all_words

    if not all_words:
        st.error("Could not load the word list. Ensure words.json is present.")
        st.stop()

    # Initialize session state
    if "constraints" not in st.session_state:
        st.session_state.constraints: List[Tuple[str, str]] = []
    if "candidates" not in st.session_state:
        st.session_state.candidates = all_words

    # Sidebar: initial suggestions
    with st.sidebar:
        st.subheader("Initial suggestions")
        initial = get_initial_guesses(all_words)
        if initial:
            st.write(", ".join(initial))
        st.divider()
        if st.button("Reset session", type="secondary"):
            st.session_state.constraints = []
            st.session_state.candidates = all_words
            st.experimental_rerun()

    st.markdown(f"**Candidates remaining:** {len(st.session_state.candidates)}")

    # Input form
    with st.form("add_attempt", clear_on_submit=True):
        cols = st.columns([2, 1])
        with cols[0]:
            guess = st.text_input("Guess (5 letters)", max_chars=5, help="e.g., crane").strip().lower()
        with cols[1]:
            feedback = st.text_input("Feedback (g/y/b)", max_chars=5, help="e.g., bygyb").strip().lower()
        submitted = st.form_submit_button("Add attempt")

    if submitted:
        # Validate inputs
        if len(guess) != 5 or not guess.isalpha():
            st.warning("Invalid guess. Please enter exactly 5 letters.")
        else:
            fb = normalize_feedback(feedback)
            if len(fb) != 5 or any(c not in {"g", "y", "b"} for c in fb):
                st.warning("Invalid feedback. Use 5 characters with only g, y, b (or x/. for gray).")
            else:
                st.session_state.constraints.append((guess, fb))
                # Early solved?
                if fb == "ggggg":
                    st.success("Solved! 🎉")
                    st.session_state.candidates = [guess]
                else:
                    st.session_state.candidates = filter_candidates(all_words, st.session_state.constraints)
                    if not st.session_state.candidates:
                        st.error("No candidates remain. You may have entered inconsistent feedback.")
                # fall through to display suggestions

    # Show constraints table
    if st.session_state.constraints:
        st.subheader("Attempts")
        attempt_rows = [
            {"#": i + 1, "Guess": g, "Feedback": f}
            for i, (g, f) in enumerate(st.session_state.constraints)
        ]
        st.dataframe(attempt_rows, hide_index=True, use_container_width=True)

    # Suggestions
    if st.session_state.candidates:
        st.subheader("Suggested next guesses")
        with st.spinner("Computing suggestions..."):
            ranked = choose_guess(st.session_state.candidates, guess_pool=st.session_state.candidates)
        if ranked:
            top5 = [ranked[i][0] for i in range(min(5, len(ranked)))]
            st.write(", ".join(top5))
        else:
            st.write("No suggestions available.")

    # Optional: show remaining candidates in an expander for power users
    with st.expander("Show remaining candidates"):
        st.write(", ".join(st.session_state.candidates[:500]))
        if len(st.session_state.candidates) > 500:
            st.caption(f"and {len(st.session_state.candidates) - 500} more ...")


if __name__ == "__main__":
    main()
