from typing import Any, Dict, List

import streamlit as st

from rag import recommend_book


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


def main() -> None:
	st.set_page_config(page_title="Smart Librarian", page_icon="📚", layout="centered")

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

		try:
			with st.spinner("Finding the perfect book for you..."):
				result = recommend_book(user_query)
		except Exception as exc:
			st.error(f"Failed to generate recommendation: {exc}")
			return

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


if __name__ == "__main__":
	main()
