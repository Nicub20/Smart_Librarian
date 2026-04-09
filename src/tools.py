from pathlib import Path
from typing import Dict


BOOK_SUMMARIES_PATH = "data/book_summaries.txt"
_SUMMARY_CACHE: Dict[str, str] | None = None


def load_book_summaries(file_path: str = BOOK_SUMMARIES_PATH) -> Dict[str, str]:
	"""Load and parse book summaries into a title -> summary dictionary."""
	path = Path(file_path)
	if not path.exists():
		raise FileNotFoundError(
			f"Book summaries file not found at '{file_path}'. "
			"Make sure the dataset exists before using this tool."
		)

	text = path.read_text(encoding="utf-8")
	lines = text.splitlines()

	summary_map: Dict[str, str] = {}
	current_title: str | None = None
	current_summary_lines: list[str] = []

	def flush_entry() -> None:
		nonlocal current_title, current_summary_lines
		if current_title is None:
			return
		summary = "\n".join(line.strip() for line in current_summary_lines).strip()
		if summary:
			summary_map[current_title] = summary
		current_title = None
		current_summary_lines = []

	for raw_line in lines:
		line = raw_line.strip()
		if line.startswith("## Title:"):
			flush_entry()
			current_title = line.replace("## Title:", "", 1).strip()
			continue

		if current_title is not None:
			current_summary_lines.append(raw_line)

	flush_entry()
	return summary_map


def _get_cached_summaries() -> Dict[str, str]:
	global _SUMMARY_CACHE
	if _SUMMARY_CACHE is None:
		_SUMMARY_CACHE = load_book_summaries()
	return _SUMMARY_CACHE


def find_summary_by_title(title: str) -> str | None:
	"""Return full summary by title using exact or case-insensitive exact match."""
	title = title.strip()
	summaries = _get_cached_summaries()

	if title in summaries:
		return summaries[title]

	lookup = title.casefold()
	for existing_title, summary in summaries.items():
		if existing_title.casefold() == lookup:
			return summary

	return None


def get_summary_by_title(title: str) -> str:
	"""Return a summary string for tool use, with a friendly fallback when missing."""
	summary = find_summary_by_title(title)
	if summary is not None:
		return summary
	return f"Sorry, I couldn't find a detailed summary for '{title}'."


if __name__ == "__main__":
	valid_title = "1984"
	invalid_title = "A Book That Does Not Exist"

	print(f"Lookup: {valid_title}")
	print(get_summary_by_title(valid_title))
	print("\n" + "-" * 60 + "\n")

	print(f"Lookup: {invalid_title}")
	print(get_summary_by_title(invalid_title))
