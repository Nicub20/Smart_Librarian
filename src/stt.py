# SPEECH-TO-TEXT MODULE

import os
from io import BytesIO
from typing import BinaryIO

from openai import OpenAI

try:
	from dotenv import load_dotenv
except ImportError:
	load_dotenv = None


TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe"


def _get_openai_client() -> OpenAI:
	if load_dotenv is not None:
		load_dotenv()

	api_key = os.getenv("OPENAI_API_KEY")
	if not api_key:
		raise EnvironmentError("OPENAI_API_KEY is not set in environment variables.")

	return OpenAI(api_key=api_key)


def _prepare_audio_file(file_obj: BinaryIO) -> BytesIO:
	"""Copy the incoming file-like object into a named in-memory buffer for OpenAI."""
	if hasattr(file_obj, "seek"):
		file_obj.seek(0)

	audio_bytes = file_obj.read()
	buffer = BytesIO(audio_bytes)
	buffer.name = getattr(file_obj, "name", "audio_input.wav")
	buffer.seek(0)
	return buffer


def transcribe_audio_file(file_obj, language: str | None = None) -> str:
	"""Transcribe a Streamlit audio input file-like object to text."""
	if file_obj is None:
		raise ValueError("Audio file object is required for transcription.")

	client = _get_openai_client()
	audio_file = _prepare_audio_file(file_obj)

	request_kwargs = {
		"model": TRANSCRIPTION_MODEL,
		"file": audio_file,
	}
	if language:
		request_kwargs["language"] = language

	response = client.audio.transcriptions.create(**request_kwargs)
	transcript = (response.text or "").strip()
	return transcript


if __name__ == "__main__":
	print(
		"stt.py is ready. Import transcribe_audio_file(...) from the Streamlit app "
		"and pass the object returned by st.audio_input()."
	)
