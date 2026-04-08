# Smart Librarian

Smart Librarian is an AI-powered book recommendation app built with OpenAI, ChromaDB, and Streamlit.

It uses:
- Retrieval-Augmented Generation (RAG) with a local ChromaDB vector store
- OpenAI embeddings for semantic search
- OpenAI chat completion for recommendations
- Tool calling with `get_summary_by_title(title)` for detailed local summaries
- Local moderation for inappropriate language filtering
- Speech-to-text for optional voice input
- Text-to-speech for listening to recommendations
- Image generation for book-inspired visuals

## Objective

Recommend books based on user interests by retrieving relevant summaries from a local vector database, then generate a focused recommendation and enrich it with detailed local summaries, optional voice interaction, audio playback, and representative book imagery.

## Features

- Parses a local dataset of book summaries
- Stores summaries in ChromaDB using `text-embedding-3-small`
- Retrieves top matches by semantic similarity
- Recommends one book with explanation
- Uses a local tool `get_summary_by_title(title)` for detailed summary lookup
- Filters inappropriate language before recommendation
- Supports typed queries and optional voice input with speech-to-text
- Generates spoken output for the final recommendation
- Generates a representative image for the recommended book
- Provides a Streamlit UI with optional retrieval debug view

## Project Structure

```text
Smart_Librarian_project/
├── data/
│   └── book_summaries.txt
├── chroma_db/
├── src/
│   ├── app.py
│   ├── image_gen.py
│   ├── ingest.py
│   ├── moderation.py
│   ├── rag.py
│   ├── stt.py
│   ├── text_to_speech.py
│   ├── tts.py
│   ├── tools.py
│   └── __pycache__/
├── requirements.txt
└── README.md
```

## How It Works

1. `src/ingest.py` reads `data/book_summaries.txt`.
2. Each entry is parsed into title + summary documents.
3. Summaries are embedded with OpenAI model `text-embedding-3-small`.
4. Embeddings are stored in local ChromaDB collection `book_summaries`.
5. In the Streamlit app, the user can type a request or enable Voice mode.
6. If Voice mode is enabled, `src/stt.py` transcribes the recorded audio using OpenAI speech-to-text.
7. `src/moderation.py` checks the final query for inappropriate language.
8. `src/rag.py` embeds the user query and retrieves top matching books.
9. Retrieved context is sent to the chat model to pick one recommendation.
10. The model can call `get_summary_by_title(title)` as a tool to fetch a detailed summary.
11. `src/app.py` displays the recommendation, explanation, detailed summary, and optional debug retrieval results.
12. The user can optionally generate spoken audio with `src/tts.py` or a representative image with `src/image_gen.py`.

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

## Streamlit App Features

- Typed recommendation input
- Optional Voice mode with `st.audio_input`
- English, Romanian, or automatic transcription selection
- Moderation warning for inappropriate language
- Recommendation explanation and detailed summary
- Optional debug section for retrieved books and distances
- Generate Audio button to listen to the recommendation
- Generate Image button to create a book-inspired illustration

## Example Prompts

- I want a book about freedom and control
- Recommend a story about friendship and magic
- I want a war novel focused on trauma and identity
- Suggest a classic about love and social class
- Ce recomanzi pentru cineva care iubește povești de război?

Voice examples:

- Recommend a fantasy book about courage and friendship
- Vreau o carte despre iubire și conflict social

## Tool Calling

Local tool signature:

```python
get_summary_by_title(title: str) -> str
```

## Additional Modules

- `src/moderation.py`: local blocked-word moderation filter
- `src/stt.py`: speech-to-text transcription helper for Streamlit audio input
- `src/tts.py`: text-to-speech helper for recommendation playback
- `src/image_gen.py`: OpenAI image generation helper for book-inspired visuals