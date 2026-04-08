import tempfile
from typing import Any, Dict, List

import streamlit as st

from moderation import contains_inappropriate_language, get_moderation_message
from rag import recommend_book
from tts import text_to_speech_file


def render_debug_results(retrieved_books: List[Dict[str, Any]]) -> None:
	"""Render optional retrieval diagnostics in a compact expandable section."""
	with st.expander("Retrieved Books (Debug)", expanded=False):
		if not retrieved_books:
			st.write("No books were retrieved.")
			return

		for idx, book in enumerate(retrieved_books, start=1):
			title = str(book.get("title", "Unknown title"))
			distance = book.get("distance")
			summary = str(book.get("summary", ""))

			st.markdown(f"**{idx}. {title}**")
			if isinstance(distance, (int, float)):
				st.write(f"Distance: {distance:.4f}")
			else:
				st.write("Distance: N/A")
			st.write(f"Summary: {summary}")
			st.divider()


def build_audio_text(result: Dict[str, Any]) -> str:
	"""Build the final recommendation text that will be converted to audio."""
	recommended_title = str(result.get("recommended_title", "Unknown"))
	why_it_matches = str(result.get("why_it_matches", "No explanation available."))
	detailed_summary = str(result.get("detailed_summary", "No detailed summary available."))

	return (
		f"Recommended title: {recommended_title}. "
		f"Why it matches: {why_it_matches}. "
		f"Detailed summary: {detailed_summary}"
	)


def render_recommendation(result: Dict[str, Any], show_debug: bool) -> None:
	"""Render the latest recommendation result and optional debug data."""
	st.subheader("Recommended title")
	st.success(result.get("recommended_title", "Unknown"))

	st.subheader("Why it matches")
	st.write(result.get("why_it_matches", "No explanation available."))

	with st.expander("Detailed summary"):
		st.write(result.get("detailed_summary", "No detailed summary available."))

	if show_debug:
		retrieved_books = result.get("retrieved_books", [])
		if isinstance(retrieved_books, list):
			render_debug_results(retrieved_books)
		else:
			st.warning("Debug data was returned in an unexpected format.")


def main() -> None:
	st.set_page_config(page_title="Smart Librarian", page_icon="📚", layout="centered")
	st.session_state.setdefault("latest_result", None)
	st.session_state.setdefault("latest_audio_path", None)

	st.title("Smart Librarian")
	st.write(
		"Discover book recommendations powered by retrieval-augmented generation. "
		"Describe what kind of story or themes you want, and get a tailored suggestion."
	)

	st.sidebar.subheader("Example prompts")
	st.sidebar.write("- I want a book about friendship and magic")
	st.sidebar.write("- Recommend a classic about love and social class")
	st.sidebar.write("- I want a war novel focused on identity and trauma")
	st.sidebar.write("- Suggest a dystopian story about freedom and control")

	show_debug = st.sidebar.checkbox("Show retrieved books (debug)", value=False)

	user_query = st.text_input(
		"What kind of book are you looking for?",
		placeholder="I want a book about friendship and magic",
	)

	if st.button("Recommend a Book", type="primary"):
		if not user_query.strip():
			st.warning("Please enter a request before asking for a recommendation.")
			return

		if contains_inappropriate_language(user_query):
			st.warning(get_moderation_message())
			return

		try:
			with st.spinner("Finding the perfect book for you..."):
				result = recommend_book(user_query)
		except Exception as exc:
			st.error(f"Failed to generate recommendation: {exc}")
			return

		st.session_state["latest_result"] = result
		st.session_state["latest_audio_path"] = None

	latest_result = st.session_state.get("latest_result")
	if isinstance(latest_result, dict):
		render_recommendation(latest_result, show_debug)

		if st.button("Generate Audio"):
			audio_text = build_audio_text(latest_result)
			try:
				with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
					audio_path = text_to_speech_file(audio_text, output_path=temp_file.name)
				st.session_state["latest_audio_path"] = audio_path
			except Exception as exc:
				st.error(f"Failed to generate audio: {exc}")

	audio_path = st.session_state.get("latest_audio_path")
	if isinstance(audio_path, str) and audio_path:
		st.audio(audio_path, format="audio/mp3")


if __name__ == "__main__":
	main()
