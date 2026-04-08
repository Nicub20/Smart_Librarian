import os
import base64
import tempfile
from pathlib import Path

from openai import OpenAI

try:
	from dotenv import load_dotenv
except ImportError:
	load_dotenv = None


IMAGE_MODEL = "gpt-image-1"


def _get_openai_client() -> OpenAI:
	if load_dotenv is not None:
		load_dotenv()

	api_key = os.getenv("OPENAI_API_KEY")
	if not api_key:
		raise EnvironmentError("OPENAI_API_KEY is not set in environment variables.")

	return OpenAI(api_key=api_key)


def _build_image_prompt(title: str, summary: str) -> str:
	clean_title = title.strip()
	clean_summary = summary.strip()
	if not clean_title or not clean_summary:
		raise ValueError("Both title and summary are required to generate an image.")

	return (
		f"A cinematic, detailed, high-quality illustration inspired by the book '{clean_title}', "
		f"based on this summary: {clean_summary}. "
		"Create a visually striking scene or cover-style composition with strong atmosphere, "
		"rich lighting, and storytelling detail."
	)


def generate_book_image(title: str, summary: str) -> str:
	"""Generate one representative image for a book and return a usable URL or file path."""
	prompt = _build_image_prompt(title, summary)
	client = _get_openai_client()

	response = client.images.generate(
		model=IMAGE_MODEL,
		prompt=prompt,
		n=1,
		size="1024x1024",
	)

	image_data = response.data[0]
	image_url = getattr(image_data, "url", None)
	if image_url:
		return image_url

	b64_image = getattr(image_data, "b64_json", None)
	if b64_image:
		image_bytes = base64.b64decode(b64_image)
		output_dir = Path(tempfile.gettempdir()) / "smart_librarian_images"
		output_dir.mkdir(parents=True, exist_ok=True)
		output_path = output_dir / "generated_book_image.png"
		output_path.write_bytes(image_bytes)
		return str(output_path)

	raise RuntimeError("Image generation succeeded but no image URL or image data was returned.")


if __name__ == "__main__":
	sample_title = "1984"
	sample_summary = (
		"A dystopian story about surveillance, propaganda, and a society controlled by fear."
	)
	image_url = generate_book_image(sample_title, sample_summary)
	print(f"Generated image URL: {image_url}")
