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

	# Keep prompt compact and avoid passing excessively explicit details directly.
	clean_summary = " ".join(clean_summary.split())[:700]

	return (
		f"A cinematic, detailed, high-quality illustration inspired by the book '{clean_title}', "
		f"based on this summary: {clean_summary}. "
		"Create a visually striking scene or cover-style composition with strong atmosphere, "
		"rich lighting, and storytelling detail."
	)


def _build_safe_cover_prompt(title: str) -> str:
	clean_title = title.strip()
	if not clean_title:
		raise ValueError("Title is required to generate a safe cover image.")

	return (
		f"Create a tasteful, minimalist, symbolic book-cover style illustration for '{clean_title}'. "
		"Use abstract shapes, mood lighting, and color storytelling. "
		"Do not include graphic violence, injury, blood, explicit content, hate symbols, or real-person likenesses. "
		"No text or logos in the image."
	)


def _is_moderation_blocked_error(exc: Exception) -> bool:
	message = str(exc).lower()
	return "moderation_blocked" in message or "safety system" in message


def _generate_image_with_prompt(client: OpenAI, prompt: str):
	return client.images.generate(
		model=IMAGE_MODEL,
		prompt=prompt,
		n=1,
		size="1024x1024",
	)


def generate_book_image(title: str, summary: str) -> str:
	"""Generate one representative image for a book and return a usable URL or file path."""
	client = _get_openai_client()
	prompt = _build_image_prompt(title, summary)

	try:
		response = _generate_image_with_prompt(client, prompt)
	except Exception as exc:
		if _is_moderation_blocked_error(exc):
			# Retry with a safer, cover-only prompt that avoids explicit narrative details.
			safe_prompt = _build_safe_cover_prompt(title)
			try:
				response = _generate_image_with_prompt(client, safe_prompt)
			except Exception as safe_exc:
				if _is_moderation_blocked_error(safe_exc):
					raise ValueError(
						"Image request was blocked by safety filters. Try a more neutral prompt, "
						"or request a symbolic book-cover style image."
					) from safe_exc
				raise
		else:
			raise

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
