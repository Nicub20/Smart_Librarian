# TEXT-TO-SPEECH MODULE

import os
from pathlib import Path

from openai import OpenAI

try:
	from dotenv import load_dotenv
except ImportError:
	load_dotenv = None


TTS_MODEL = "gpt-4o-mini-tts"
TTS_VOICE = "alloy"


def _get_openai_client() -> OpenAI:
	if load_dotenv is not None:
		load_dotenv()

	api_key = os.getenv("OPENAI_API_KEY")
	if not api_key:
		raise EnvironmentError("OPENAI_API_KEY is not set in environment variables.")

	return OpenAI(api_key=api_key)


def text_to_speech_file(text: str, output_path: str = "output_audio.mp3") -> str:
	"""Convert text to speech with OpenAI and save it as an MP3 file."""
	clean_text = text.strip()
	if not clean_text:
		raise ValueError("Text for text-to-speech cannot be empty.")

	client = _get_openai_client()
	output_file = Path(output_path)
	output_file.parent.mkdir(parents=True, exist_ok=True)

	response = client.audio.speech.create(
		model=TTS_MODEL,
		voice=TTS_VOICE,
		input=clean_text,
		response_format="mp3",
	)
	response.stream_to_file(output_file)

	return str(output_file)


if __name__ == "__main__":
	sample_text = "Hello. This is Smart Librarian reading your book recommendation."
	file_path = text_to_speech_file(sample_text)
	print(f"Audio saved to: {file_path}")
