import tempfile
from typing import Any, Dict, List

import streamlit as st

from domain_guard import build_off_topic_response, is_clearly_off_topic
from image_gen import generate_book_image
from moderation import contains_inappropriate_language, get_moderation_message
from rag import recommend_book
from stt import transcribe_audio_file
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
	st.session_state.setdefault("latest_image_url", None)
	st.session_state.setdefault("latest_transcript", "")

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
	voice_mode = st.sidebar.checkbox("Voice mode", value=False)
	language_options = {
		"Auto": None,
		"English": "en",
		"Romanian": "ro",
	}
	selected_language = st.sidebar.selectbox(
		"Transcription language",
		options=list(language_options.keys()),
		disabled=not voice_mode,
	)
	selected_language_code = language_options[selected_language]

	user_query = ""
	audio_input = None
	if voice_mode:
		audio_input = st.audio_input("Record your request")
		st.caption("Record in English or Romanian, then click Recommend a Book.")
	else:
		user_query = st.text_input(
			"What kind of book are you looking for?",
			placeholder="I want a book about friendship and magic",
		)

	if st.button("Recommend a Book", type="primary"):
		final_query = user_query.strip()

		if voice_mode:
			if audio_input is None:
				st.warning("Please record your request before asking for a recommendation.")
				return

			try:
				with st.spinner("Transcribing your request..."):
					final_query = transcribe_audio_file(
						audio_input,
						language=selected_language_code,
					)
			except Exception as exc:
				st.error(f"Failed to transcribe audio: {exc}")
				return

			st.session_state["latest_transcript"] = final_query
			st.success("Voice input processed successfully!")
		else:
			st.session_state["latest_transcript"] = ""

		if not final_query:
			if voice_mode:
				st.warning("Could not understand audio. Please try again.")
			else:
				st.warning("Please enter or record a request before asking for a recommendation.")
			return

		if contains_inappropriate_language(final_query):
			st.warning(get_moderation_message())
			return

		if is_clearly_off_topic(final_query):
			st.session_state["latest_result"] = build_off_topic_response()
			st.session_state["latest_audio_path"] = None
			st.session_state["latest_image_url"] = None
			return

		try:
			with st.spinner("Finding the perfect book for you..."):
				result = recommend_book(final_query)
		except Exception as exc:
			st.error(f"Failed to generate recommendation: {exc}")
			return

		st.session_state["latest_result"] = result
		st.session_state["latest_audio_path"] = None
		st.session_state["latest_image_url"] = None

	latest_transcript = st.session_state.get("latest_transcript", "")
	if voice_mode and latest_transcript:
		st.subheader("Recognized text")
		st.write(latest_transcript)

	latest_result = st.session_state.get("latest_result")
	if isinstance(latest_result, dict):
		render_recommendation(latest_result, show_debug)

		if st.button("Generate Image", key="generate_image"):
			title = str(latest_result.get("recommended_title", "")).strip()
			summary = str(latest_result.get("detailed_summary", "")).strip()
			try:
				with st.spinner("Generating image..."):
					image_url = generate_book_image(title, summary)
				st.session_state["latest_image_url"] = image_url
			except Exception as exc:
				st.error(f"Failed to generate image: {exc}")

		if st.button("Generate Audio", key="generate_audio"):
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

	image_url = st.session_state.get("latest_image_url")
	if isinstance(image_url, str) and image_url:
		st.image(image_url)


if __name__ == "__main__":
	main()
