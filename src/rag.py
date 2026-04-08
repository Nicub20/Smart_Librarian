import os
from typing import Any, Dict, List

import chromadb
from openai import OpenAI

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

	chunks: List[str] = []
	for idx, book in enumerate(books, start=1):
		chunks.append(
			f"Book {idx}\n"
			f"Title: {book['title']}\n"
			f"Summary: {book['summary']}"
		)
	return "\n\n".join(chunks)


def generate_recommendation(openai_client: OpenAI, user_query: str, context: str) -> str:
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


def parse_recommendation_response(raw_response: str) -> Dict[str, str]:
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
	openai_client = get_openai_client()
	collection = get_collection()
	query_embedding = embed_query(openai_client, user_query)
	retrieved_books = retrieve_top_books(collection, query_embedding, top_k=3)
	context = build_context(retrieved_books)
	raw_recommendation = generate_recommendation(openai_client, user_query, context)
	parsed = parse_recommendation_response(raw_recommendation)

	if parsed["recommended_title"] == "Unknown" and retrieved_books:
		parsed["recommended_title"] = str(retrieved_books[0]["title"])

	if parsed["why_it_matches"] == "Could not parse model output safely." and retrieved_books:
		parsed["why_it_matches"] = (
			"This title was selected because it is the closest semantic match to your query "
			"within the retrieved context."
		)

	return {
		"recommended_title": parsed["recommended_title"],
		"why_it_matches": parsed["why_it_matches"],
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

		if debug_retrieval:
			print("\nRetrieved books (debug):")
			for idx, book in enumerate(result["retrieved_books"], start=1):
				print(
					f"{idx}. {book['title']} "
					f"(distance={book['distance']:.4f})"
				)


if __name__ == "__main__":
	run_cli()
