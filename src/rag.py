import os
import json
from typing import Any, Dict, List

import chromadb
from openai import OpenAI
from tools import get_summary_by_title

try:
	from dotenv import load_dotenv
except ImportError:
	load_dotenv = None


EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_CHAT_MODEL = "gpt-4o-mini"
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "book_summaries"


def get_openai_client() -> OpenAI:
	if load_dotenv is not None:
		load_dotenv()

	api_key = os.getenv("OPENAI_API_KEY")
	if not api_key:
		raise EnvironmentError("OPENAI_API_KEY is not set in environment variables.")
	return OpenAI(api_key=api_key)


def get_collection() -> chromadb.Collection:
	# Load an existing collection only; ingestion is handled separately.
	client = chromadb.PersistentClient(path=CHROMA_PATH)
	try:
		return client.get_collection(name=COLLECTION_NAME)
	except Exception as exc:
		raise RuntimeError(
			f"Chroma collection '{COLLECTION_NAME}' was not found in '{CHROMA_PATH}'. "
			"Run ingest.py first to create and populate it."
		) from exc


def embed_query(openai_client: OpenAI, query: str) -> List[float]:
	response = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=[query])
	return response.data[0].embedding


def retrieve_top_books(
	collection: chromadb.Collection,
	query_embedding: List[float],
	top_k: int = 3,
) -> List[Dict[str, Any]]:
	# Return summary candidates plus vector distance for optional debugging/UI.
	results = collection.query(
		query_embeddings=[query_embedding],
		n_results=top_k,
		include=["documents", "metadatas", "distances"],
	)

	documents = results.get("documents", [[]])[0]
	metadatas = results.get("metadatas", [[]])[0]
	distances = results.get("distances", [[]])[0]

	books: List[Dict[str, Any]] = []
	for doc, meta, distance in zip(documents, metadatas, distances):
		title = (meta or {}).get("title", "Unknown title")
		books.append(
			{
				"title": title,
				"summary": doc,
				"distance": float(distance) if distance is not None else float("inf"),
			}
		)

	return books


def build_context(books: List[Dict[str, Any]]) -> str:
	if not books:
		return "No relevant books were retrieved from the database."

	# Keep context compact and deterministic for stable recommendation output.
	chunks: List[str] = []
	for idx, book in enumerate(books, start=1):
		chunks.append(
			f"Book {idx}\n"
			f"Title: {book['title']}\n"
			f"Summary: {book['summary']}"
		)
	return "\n\n".join(chunks)


def generate_recommendation(openai_client: OpenAI, user_query: str, context: str) -> str:
	# Ask the chat model for a strict two-line response that we can parse reliably.
	chat_model = os.getenv("OPENAI_CHAT_MODEL", DEFAULT_CHAT_MODEL)
	system_prompt = (
		"You are Smart Librarian, a helpful book recommendation assistant. "
		"Use only the retrieved context and do not invent books or details. "
		"Return your answer in this exact format with exactly two lines:\n"
		"Recommended title: <book title>\n"
		"Why it matches: <short explanation>."
	)

	user_prompt = (
		f"User request: {user_query}\n\n"
		f"Retrieved context:\n{context}\n\n"
		"Task: Recommend one book from the context and explain why it matches the user's interests."
	)

	response = openai_client.chat.completions.create(
		model=chat_model,
		messages=[
			{"role": "system", "content": system_prompt},
			{"role": "user", "content": user_prompt},
		],
		temperature=0.0,
	)

	return response.choices[0].message.content or "No recommendation generated."


def generate_recommendation_with_tool(
	openai_client: OpenAI,
	user_query: str,
	context: str,
	fallback_title: str,
) -> Dict[str, str]:
	"""Let the model call get_summary_by_title as an OpenAI tool, then return final text."""
	chat_model = os.getenv("OPENAI_CHAT_MODEL", DEFAULT_CHAT_MODEL)

	system_prompt = (
		"You are Smart Librarian, a helpful book recommendation assistant. "
		"Use only the retrieved context and do not invent books or details. "
		"First, choose one recommended title from the context and call the tool get_summary_by_title. "
		"After receiving the tool result, return exactly two lines in this format:\n"
		"Recommended title: <book title>\n"
		"Why it matches: <short explanation>."
	)

	user_prompt = (
		f"User request: {user_query}\n\n"
		f"Retrieved context:\n{context}\n\n"
		"Task: Recommend one book from the context, use the tool to fetch its summary, then provide the final two-line answer."
	)

	tools = [
		{
			"type": "function",
			"function": {
				"name": "get_summary_by_title",
				"description": "Get a full local summary for an exact book title.",
				"parameters": {
					"type": "object",
					"properties": {
						"title": {
							"type": "string",
							"description": "Exact title of the recommended book.",
						}
					},
					"required": ["title"],
					"additionalProperties": False,
				},
			},
		}
	]

	messages: List[Dict[str, Any]] = [
		{"role": "system", "content": system_prompt},
		{"role": "user", "content": user_prompt},
	]

	first_response = openai_client.chat.completions.create(
		model=chat_model,
		messages=messages,
		tools=tools,
		tool_choice="auto",
		temperature=0.0,
	)
	assistant_message = first_response.choices[0].message

	tool_calls = assistant_message.tool_calls or []
	called_title = ""
	detailed_summary = ""

	assistant_payload: Dict[str, Any] = {
		"role": "assistant",
		"content": assistant_message.content or "",
	}
	if tool_calls:
		assistant_payload["tool_calls"] = [
			{
				"id": call.id,
				"type": call.type,
				"function": {
					"name": call.function.name,
					"arguments": call.function.arguments,
				},
			}
			for call in tool_calls
		]
	messages.append(assistant_payload)

	if tool_calls:
		for call in tool_calls:
			if call.function.name != "get_summary_by_title":
				continue

			try:
				args = json.loads(call.function.arguments or "{}")
			except json.JSONDecodeError:
				args = {}

			candidate_title = str(args.get("title", "")).strip()
			called_title = candidate_title or fallback_title
			detailed_summary = get_summary_by_title(called_title)

			messages.append(
				{
					"role": "tool",
					"tool_call_id": call.id,
					"content": detailed_summary,
				}
			)

		final_response = openai_client.chat.completions.create(
			model=chat_model,
			messages=messages,
			temperature=0.0,
		)
		final_text = final_response.choices[0].message.content or "No recommendation generated."
		return {
			"raw_recommendation": final_text,
			"tool_title": called_title,
			"detailed_summary": detailed_summary,
		}

	# If the model skipped tool calling, preserve behavior with a safe fallback.
	fallback_text = assistant_message.content or "No recommendation generated."
	called_title = fallback_title
	detailed_summary = get_summary_by_title(called_title)
	return {
		"raw_recommendation": fallback_text,
		"tool_title": called_title,
		"detailed_summary": detailed_summary,
	}


def parse_recommendation_response(raw_response: str) -> Dict[str, str]:
	# Parse structured lines safely and degrade gracefully if format drifts.
	recommended_title = "Unknown"
	why_it_matches = "Could not parse model output safely."

	for line in raw_response.splitlines():
		stripped = line.strip()
		if stripped.lower().startswith("recommended title:"):
			recommended_title = stripped.split(":", 1)[1].strip() or "Unknown"
		elif stripped.lower().startswith("why it matches:"):
			why_it_matches = stripped.split(":", 1)[1].strip() or why_it_matches

	if recommended_title == "Unknown" and raw_response.strip():
		first_line = raw_response.strip().splitlines()[0].strip()
		recommended_title = first_line[:120] if first_line else "Unknown"

	return {
		"recommended_title": recommended_title,
		"why_it_matches": why_it_matches,
	}


def recommend_book(user_query: str) -> Dict[str, Any]:
	# Orchestrate retrieval + generation and enrich the result with local summary data.
	openai_client = get_openai_client()
	collection = get_collection()
	query_embedding = embed_query(openai_client, user_query)
	retrieved_books = retrieve_top_books(collection, query_embedding, top_k=3)
	context = build_context(retrieved_books)
	fallback_title = str(retrieved_books[0]["title"]) if retrieved_books else "Unknown"
	tool_result = generate_recommendation_with_tool(
		openai_client=openai_client,
		user_query=user_query,
		context=context,
		fallback_title=fallback_title,
	)
	raw_recommendation = tool_result["raw_recommendation"]
	parsed = parse_recommendation_response(raw_recommendation)

	recommended_title = parsed["recommended_title"].strip()
	# If model output is empty/unknown, use the top retrieved title as fallback.
	if (not recommended_title or recommended_title == "Unknown") and retrieved_books:
		recommended_title = str(retrieved_books[0]["title"])

	# Keep summary aligned with the final chosen title if tool/model titles diverge.
	if recommended_title and recommended_title != "Unknown":
		detailed_summary = get_summary_by_title(recommended_title)
	else:
		detailed_summary = tool_result["detailed_summary"]

	if parsed["why_it_matches"] == "Could not parse model output safely." and retrieved_books:
		parsed["why_it_matches"] = (
			"This title was selected because it is the closest semantic match to your query "
			"within the retrieved context."
		)

	return {
		"recommended_title": recommended_title or "Unknown",
		"why_it_matches": parsed["why_it_matches"],
		"detailed_summary": detailed_summary,
		"retrieved_books": retrieved_books,
	}


def run_cli() -> None:
	debug_retrieval = os.getenv("RAG_DEBUG", "0") == "1"

	print("Smart Librarian RAG CLI")
	print("Type your reading preferences, or type 'exit' / 'quit' to stop.")
	if debug_retrieval:
		print("Debug retrieval mode is ON (RAG_DEBUG=1).")

	while True:
		user_query = input("\nWhat kind of book are you looking for? ").strip()
		if not user_query:
			print("Please enter a query.")
			continue

		if user_query.lower() in {"exit", "quit"}:
			print("Goodbye!")
			break

		result = recommend_book(user_query)

		print("\nRecommendation:")
		print(f"Recommended title: {result['recommended_title']}")
		print(f"Why it matches: {result['why_it_matches']}")
		print(f"Detailed summary: {result['detailed_summary']}")

		if debug_retrieval:
			print("\nRetrieved books (debug):")
			for idx, book in enumerate(result["retrieved_books"], start=1):
				print(
					f"{idx}. {book['title']} "
					f"(distance={book['distance']:.4f})"
				)


if __name__ == "__main__":
	run_cli()
