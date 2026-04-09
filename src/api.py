import tempfile
import base64
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

try:
	from .domain_guard import build_off_topic_response, is_clearly_off_topic
	from .image_gen import generate_book_image
	from .moderation import contains_inappropriate_language, get_moderation_message
	from .rag import recommend_book
	from .stt import transcribe_audio_file
	from .tts import text_to_speech_file
except ImportError:
	from domain_guard import build_off_topic_response, is_clearly_off_topic
	from image_gen import generate_book_image
	from moderation import contains_inappropriate_language, get_moderation_message
	from rag import recommend_book
	from stt import transcribe_audio_file
	from tts import text_to_speech_file


class RecommendRequest(BaseModel):
	query: str


class ImageRequest(BaseModel):
	title: str
	summary: str


class TTSRequest(BaseModel):
	text: str


app = FastAPI(title="Smart Librarian API")

app.add_middleware(
	CORSMiddleware,
	allow_origins=[
		"http://localhost:3000",
		"http://127.0.0.1:3000",
		"http://localhost:5173",
		"http://127.0.0.1:5173",
	],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
	return {"status": "Smart Librarian API is running."}


@app.post("/recommend")
def recommend(payload: RecommendRequest) -> dict:
	query = payload.query.strip()
	if not query:
		raise HTTPException(status_code=400, detail="Query cannot be empty.")

	if contains_inappropriate_language(query):
		raise HTTPException(status_code=400, detail=get_moderation_message())

	if is_clearly_off_topic(query):
		return build_off_topic_response()

	try:
		result = recommend_book(query)
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Recommendation failed: {exc}") from exc

	return {
		"recommended_title": result.get("recommended_title", "Unknown"),
		"why_it_matches": result.get("why_it_matches", ""),
		"detailed_summary": result.get("detailed_summary", ""),
		"retrieved_books": result.get("retrieved_books", []),
		"off_topic": result.get("off_topic", False),
	}


@app.post("/image")
def image(payload: ImageRequest) -> dict[str, str]:
	title = payload.title.strip()
	summary = payload.summary.strip()
	if not title or not summary:
		raise HTTPException(status_code=400, detail="Title and summary are required.")

	try:
		image_url = generate_book_image(title, summary)
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Image generation failed: {exc}") from exc

	# If image generation returns a local file path, convert it to a data URL for frontend rendering.
	image_path = Path(image_url)
	if image_path.exists() and image_path.is_file():
		try:
			image_bytes = image_path.read_bytes()
			encoded = base64.b64encode(image_bytes).decode("ascii")
			image_url = f"data:image/png;base64,{encoded}"
		except Exception as exc:
			raise HTTPException(status_code=500, detail=f"Failed to encode image: {exc}") from exc

	return {"image_url": image_url}


@app.post("/tts")
def tts(payload: TTSRequest) -> FileResponse:
	text = payload.text.strip()
	if not text:
		raise HTTPException(status_code=400, detail="Text cannot be empty.")

	output_dir = Path(tempfile.gettempdir()) / "smart_librarian_audio"
	output_dir.mkdir(parents=True, exist_ok=True)
	output_path = output_dir / f"tts_{uuid4().hex}.mp3"

	try:
		audio_path = text_to_speech_file(text, output_path=str(output_path))
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Text-to-speech failed: {exc}") from exc

	return FileResponse(path=audio_path, media_type="audio/mpeg", filename="recommendation.mp3")


@app.post("/stt")
async def stt(audio_file: UploadFile = File(...), language: str | None = Form(default=None)) -> dict[str, str]:
	if audio_file is None:
		raise HTTPException(status_code=400, detail="Audio file is required.")

	try:
		audio_bytes = await audio_file.read()
		if not audio_bytes:
			raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

		buffer = BytesIO(audio_bytes)
		buffer.name = audio_file.filename or "recording.webm"
		transcript = transcribe_audio_file(buffer, language=language)
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Speech-to-text failed: {exc}") from exc
	finally:
		await audio_file.close()

	return {"transcript": transcript}
