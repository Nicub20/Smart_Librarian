import re


# Keep this set small and easy to extend for local moderation rules.
BLOCKED_WORDS = {
	# English
	"brainless",
	"idiotic",
	"moron",
	"fool",
	"jerk",
	"bastard",
	"asshole",
	"useless",
	"noob",
	"dick",
	"dumb",
	"idiot",
	"dickhead",
	"stupid",
	"hate",
	"damn",
	"shit",
    "crap",
	# Romanian
	"prost",
    "pula",
	"proasta",
	"prosti",
	"prostule",
	"tampit",
	"tampita",
	"tampiti",
	"idiotule",
	"dracu",
	"naibii",
}


def _normalize_tokens(text: str) -> set[str]:
	"""Lowercase input and extract word-like tokens for simple matching."""
	normalized_text = text.lower()
	return set(re.findall(r"\b[\w']+\b", normalized_text))


def contains_inappropriate_language(text: str) -> bool:
	"""Return True when the input contains any blocked word."""
	tokens = _normalize_tokens(text)
	return any(word in tokens for word in BLOCKED_WORDS)


def get_moderation_message() -> str:
	"""Return a short, polite moderation response."""
	return "Please use respectful language and try your request again."


if __name__ == "__main__":
	normal_input = "I want a fantasy book about friendship and magic."
	inappropriate_input = "Recommend something, idiot."

	print("Normal input test:")
	print(normal_input)
	print(f"Contains inappropriate language: {contains_inappropriate_language(normal_input)}")
	print()

	print("Inappropriate input test:")
	print(inappropriate_input)
	print(f"Contains inappropriate language: {contains_inappropriate_language(inappropriate_input)}")
	if contains_inappropriate_language(inappropriate_input):
		print(get_moderation_message())
