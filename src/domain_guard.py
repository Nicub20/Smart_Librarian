import re

try:
	from .tools import load_book_summaries
except ImportError:
	from tools import load_book_summaries


BOOK_KEYWORDS = {
	"author",
	"authors",
	"biography",
	"book",
	"books",
	"classic",
	"fiction",
	"genre",
	"genres",
	"literature",
	"memoir",
	"novel",
	"novels",
	"plot",
	"poetry",
	"read",
	"reading",
	"recommend",
	"recommendation",
	"recommendations",
	"romanian",
	"story",
	"suggest",
	"summary",
	"summaries",
	"theme",
	"themes",
	"writer",
	"written",
	"fantasy",
	"dystopian",
	"mystery",
	"thriller",
	"romance",
	"horror",
	"scifi",
	"sci-fi",
	"science",
	"comedy",
	"humor",
	"humour",
	"funny",
}


TECH_TOPIC_KEYWORDS = {
	"algorithm",
	"algorithms",
	"bug",
	"code",
	"coding",
	"compiler",
	"function",
	"java",
	"javascript",
	"leetcode",
	"math",
	"program",
	"programming",
	"python",
	"recipe",
	"sql",
	"c",
	"c++",
	"html",
	"css",
	"api",
	"debug",
	"fix",
	"browser",
	"server",
}


TASK_INTENT_KEYWORDS = {
	"build",
	"calculate",
	"code",
	"debug",
	"develop",
	"fix",
	"implement",
	"solve",
	"translate",
	"write",
}


STRONG_OFF_TOPIC_PHRASES = {
	"tell me a joke",
	"say a joke",
	"make me laugh",
	"help me code",
	"help me write c code",
	"help me write code",
	"help me debug",
	"help me fix",
	"help me implement",
	"help me solve",
	"write python code",
	"write javascript code",
	"write c code",
	"write code",
	"debug my code",
	"debug my javascript",
	"debug javascript",
	"fix my code",
	"fix my javascript",
	"what's the weather",
	"what is the weather",
	"weather today",
	"temperature today",
	"weather forecast",
	"translate this sentence",
	"solve this math problem",
}


TOPIC_SEEKING_PHRASES = {
	"i want something",
	"i want a story",
	"i want a novel",
	"something related to",
	"something about",
	"looking for something",
	"looking for a story",
	"looking for a novel",
	"recommend something",
	"suggest something",
	"in the mood for",
}


OFF_TOPIC_MESSAGE = (
	"I'm mainly here to help with book recommendations and book-related questions. "
	"If you want, I can still recommend a book related to that topic."
)


def _normalize_tokens(text: str) -> set[str]:
	return set(re.findall(r"\b[\w+\-']+\b", text.casefold()))


def _get_known_titles() -> list[str]:
	try:
		summaries = load_book_summaries()
	except Exception:
		return []
	return [title.casefold() for title in summaries.keys() if title.strip()]


def _mentions_known_title(query: str) -> bool:
	query_cf = query.casefold()
	for title in _get_known_titles():
		if len(title) < 3:
			continue
		if title in query_cf:
			return True
	return False


def _is_strong_off_topic_query(query_cf: str, tokens: set[str]) -> bool:
	if any(phrase in query_cf for phrase in STRONG_OFF_TOPIC_PHRASES):
		return True

	translation_task_tokens = {"translate", "translation", "sentence", "text", "phrase"}
	math_task_tokens = {"math", "equation", "problem", "calculate", "calculation"}
	weather_question_tokens = {"weather", "temperature", "forecast"}

	if {"what", "whats", "what's"}.intersection(tokens) and tokens.intersection(weather_question_tokens):
		return True

	if "today" in tokens and tokens.intersection(weather_question_tokens):
		return True

	if "translate" in tokens and tokens.intersection(translation_task_tokens):
		return True

	if {"solve", "calculate"}.intersection(tokens) and tokens.intersection(math_task_tokens):
		return True

	# Block technical/programming requests only when there is clear task intent.
	if tokens.intersection(TECH_TOPIC_KEYWORDS) and tokens.intersection(TASK_INTENT_KEYWORDS):
		return True

	if "help" in tokens and tokens.intersection(TECH_TOPIC_KEYWORDS):
		return True

	return False


def _is_topic_seeking_query(query_cf: str) -> bool:
	return any(phrase in query_cf for phrase in TOPIC_SEEKING_PHRASES)


def is_clearly_off_topic(query: str) -> bool:
	"""Return True only for obviously non-book task requests.

	This guard is intentionally conservative: broad topic discovery prompts should pass.
	"""
	clean_query = query.strip()
	if not clean_query:
		return True

	query_cf = clean_query.casefold()
	tokens = _normalize_tokens(clean_query)

	if _mentions_known_title(clean_query):
		return False

	if tokens.intersection(BOOK_KEYWORDS):
		return False

	if _is_topic_seeking_query(query_cf):
		return False

	return _is_strong_off_topic_query(query_cf, tokens)


def is_book_related_query(query: str) -> bool:
	return not is_clearly_off_topic(query)


def build_off_topic_response() -> dict[str, object]:
	return {
		"recommended_title": "Book-related assistance only",
		"why_it_matches": OFF_TOPIC_MESSAGE,
		"detailed_summary": "You can ask for a recommendation by theme, mood, genre, author, or subject, and I'll help you discover a book that fits.",
		"retrieved_books": [],
		"off_topic": True,
	}


def get_off_topic_message() -> str:
	return OFF_TOPIC_MESSAGE