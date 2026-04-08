# Smart Librarian

Smart Librarian is an AI-powered book recommendation app built with OpenAI, ChromaDB, and Streamlit.

It uses:
- Retrieval-Augmented Generation (RAG) with a local ChromaDB vector store
- OpenAI embeddings for semantic search
- OpenAI chat completion for recommendations
- Tool calling with `get_summary_by_title(title)` for detailed local summaries

## Objective

Recommend books based on user interests by retrieving relevant summaries from a local vector database, then generate a focused recommendation and enrich it with a detailed summary from a local tool.

## Features

- Parses a local dataset of book summaries
- Stores summaries in ChromaDB using `text-embedding-3-small`
- Retrieves top matches by semantic similarity
- Recommends one book with explanation
- Uses a local tool `get_summary_by_title(title)` for detailed summary lookup
- Provides a Streamlit UI with optional retrieval debug view

## Project Structure

```text
Smart_Librarian_project/
├── data/
│   └── book_summaries.txt
├── chroma_db/
├── src/
│   ├── ingest.py
│   ├── rag.py
│   ├── tools.py
│   └── app.py
├── requirements.txt
└── README.md
```

## How It Works

1. `src/ingest.py` reads `data/book_summaries.txt`.
2. Each entry is parsed into title + summary documents.
3. Summaries are embedded with OpenAI model `text-embedding-3-small`.
4. Embeddings are stored in local ChromaDB collection `book_summaries`.
5. `src/rag.py` embeds the user query and retrieves top matching books.
6. Retrieved context is sent to the chat model to pick one recommendation.
7. The model can call `get_summary_by_title(title)` as a tool to fetch a detailed summary.
8. `src/app.py` displays recommendation, explanation, detailed summary, and optional debug retrieval results.

## Installation

1. Create and activate a virtual environment (PowerShell):

```bash
py -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set your OpenAI API key:

```bash
setx OPENAI_API_KEY "your_api_key_here"
```

Optional: set chat model override.

```bash
setx OPENAI_CHAT_MODEL "gpt-4o-mini"
```

## Running the Project

1. Ingest the dataset into ChromaDB:

```bash
python src/ingest.py
```

2. Run the CLI recommender (optional):

```bash
python src/rag.py
```

3. Start the Streamlit app:

```bash
streamlit run src/app.py
```

## Example Prompts

- I want a book about freedom and control
- Recommend a story about friendship and magic
- I want a war novel focused on trauma and identity
- Suggest a classic about love and social class
- Ce recomanzi pentru cineva care iubește povești de război?

## Tool Calling

Local tool signature:

```python
get_summary_by_title(title: str) -> str
```