import os
from pathlib import Path
from typing import Dict, List

import chromadb
from openai import OpenAI

try:
	from dotenv import load_dotenv
except ImportError:
	load_dotenv = None


def load_and_parse_file(file_path: str) -> List[Dict[str, object]]:
	"""Parse book entries from a text file into documents with content + metadata."""
	path = Path(file_path)
	if not path.exists():
		raise FileNotFoundError(f"Input file not found: {file_path}")

	text = path.read_text(encoding="utf-8")
	lines = text.splitlines()

	documents: List[Dict[str, object]] = []
	current_title: str | None = None
	current_summary_lines: List[str] = []

	def flush_entry() -> None:
		nonlocal current_title, current_summary_lines
		if current_title is None:
			return
		summary = "\n".join(line.strip() for line in current_summary_lines).strip()
		if not summary:
			raise ValueError(f"Missing summary for title: {current_title}")
		doc_id = f"book-{len(documents) + 1}"
		documents.append(
			{
				"id": doc_id,
				"page_content": summary,
				"metadata": {"title": current_title},
			}
		)
		current_title = None
		current_summary_lines = []

	for raw_line in lines:
		line = raw_line.strip()
		if line.startswith("## Title:"):
			flush_entry()
			current_title = line.replace("## Title:", "", 1).strip()
			if not current_title:
				raise ValueError("Found an entry with an empty title.")
			continue

		if current_title is not None:
			current_summary_lines.append(raw_line)

	flush_entry()

	if not documents:
		raise ValueError("No valid book entries found in the input file.")

	return documents


def create_embeddings(
	client: OpenAI,
	texts: List[str],
	model: str = "text-embedding-3-small",
) -> List[List[float]]:
	"""Create embeddings for a list of texts using OpenAI embeddings API."""
	response = client.embeddings.create(model=model, input=texts)
	return [item.embedding for item in response.data]


def build_embedding_inputs(documents: List[Dict[str, object]]) -> List[str]:
	"""Combine title and summary so title/author queries retrieve more reliably."""
	inputs: List[str] = []
	for doc in documents:
		title = str((doc.get("metadata") or {}).get("title", "")).strip()
		summary = str(doc.get("page_content", "")).strip()
		inputs.append(f"Title: {title}\nSummary: {summary}")
	return inputs


def store_documents_in_chromadb(
	documents: List[Dict[str, object]],
	embeddings: List[List[float]],
	db_path: str = "./chroma_db",
	collection_name: str = "book_summaries",
) -> chromadb.Collection:
	"""Store parsed documents and embeddings into a persistent ChromaDB collection."""
	if len(documents) != len(embeddings):
		raise ValueError("Documents and embeddings length mismatch.")

	chroma_client = chromadb.PersistentClient(path=db_path)
	collection = chroma_client.get_or_create_collection(name=collection_name)

	ids = [doc["id"] for doc in documents]
	contents = [doc["page_content"] for doc in documents]
	metadatas = [doc["metadata"] for doc in documents]

	collection.upsert(
		ids=ids,
		documents=contents,
		metadatas=metadatas,
		embeddings=embeddings,
	)
	return collection


def query_top_results(
	client: OpenAI,
	collection: chromadb.Collection,
	query_text: str,
	model: str = "text-embedding-3-small",
	top_k: int = 2,
) -> None:
	"""Run a semantic query and print top matches (title + summary)."""
	query_embedding = create_embeddings(client, [query_text], model=model)[0]
	results = collection.query(
		query_embeddings=[query_embedding],
		n_results=top_k,
		include=["documents", "metadatas", "distances"],
	)

	docs = results.get("documents", [[]])[0]
	metas = results.get("metadatas", [[]])[0]
	distances = results.get("distances", [[]])[0]

	print(f"\nQuery: {query_text}\n")
	for idx, (doc, meta, distance) in enumerate(zip(docs, metas, distances), start=1):
		title = (meta or {}).get("title", "Unknown title")
		print(f"Result {idx}:")
		print(f"Title: {title}")
		print(f"Summary: {doc}")
		print(f"Distance: {distance:.4f}\n")


def main() -> None:
	if load_dotenv is not None:
		load_dotenv()

	api_key = os.getenv("OPENAI_API_KEY")
	if not api_key:
		raise EnvironmentError("OPENAI_API_KEY is not set in environment variables.")

	input_file = "data/book_summaries.txt"
	embedding_model = "text-embedding-3-small"

	openai_client = OpenAI(api_key=api_key)

	documents = load_and_parse_file(input_file)
	embedding_inputs = build_embedding_inputs(documents)
	embeddings = create_embeddings(openai_client, embedding_inputs, model=embedding_model)

	collection = store_documents_in_chromadb(
		documents=documents,
		embeddings=embeddings,
		db_path="./chroma_db",
		collection_name="book_summaries",
	)

	print(f"Stored {len(documents)} documents in ChromaDB collection 'book_summaries'.")

	test_query = "I want a book about freedom and control"
	query_top_results(openai_client, collection, test_query, model=embedding_model, top_k=2)


if __name__ == "__main__":
	main()
