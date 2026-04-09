# Smart Librarian

Smart Librarian is a full-stack AI book recommendation project built with OpenAI, ChromaDB, FastAPI, Streamlit, and React.

It combines retrieval-augmented generation with a local book-summary dataset and exposes the recommendation flow through both a Streamlit interface and a React frontend.

## Core Capabilities

- Retrieval-Augmented Generation (RAG) with ChromaDB
- OpenAI embeddings for semantic retrieval
- OpenAI chat completions for final recommendation selection
- Local summary lookup with `get_summary_by_title(title)`
- Moderation filter for inappropriate language
- Speech-to-text for voice input
- Text-to-speech for audio playback
- Image generation for book-cover style visuals
- FastAPI backend for frontend integration
- React frontend with chat-style UI

## Current Architecture

### Backend

- `src/ingest.py`: parses `data/book_summaries.txt`, builds embeddings, and stores vectors in ChromaDB
- `src/rag.py`: retrieves relevant books, reranks candidates, calls the model, and returns structured recommendation output
- `src/tools.py`: local title-to-summary lookup helper
- `src/moderation.py`: simple local moderation filter
- `src/stt.py`: speech-to-text helper
- `src/tts.py`: text-to-speech helper
- `src/image_gen.py`: image generation helper with moderation-aware fallback behavior
- `src/api.py`: FastAPI app exposing `/recommend`, `/image`, `/tts`, and `/stt`
- `src/app.py`: Streamlit interface for testing and demos

### Frontend

- `smart-librarian-frontend/`: Vite + React frontend
- Chat-style interface with sidebar, voice mode, recommendation cards, media rendering, and modern UI polish

## Project Structure

```text
Smart_Librarian_project/
├── chroma_db/
├── data/
│   └── book_summaries.txt
├── smart-librarian-frontend/
│   ├── package.json
│   └── src/
├── src/
│   ├── api.py
│   ├── app.py
│   ├── image_gen.py
│   ├── ingest.py
│   ├── moderation.py
│   ├── rag.py
│   ├── stt.py
│   ├── tools.py
│   └── tts.py
├── requirements.txt
└── README.md
```

## Dataset and Retrieval Flow

1. `src/ingest.py` reads `data/book_summaries.txt`
2. Each entry is parsed into `title + summary`
3. Embeddings are created from combined title and summary text using `text-embedding-3-small`
4. Embeddings are stored in local ChromaDB collection `book_summaries`
5. `src/rag.py` embeds the user query and retrieves top matches
6. Retrieved books are reranked using semantic distance plus lexical/title signals
7. The chat model recommends one title and enriches the result with a local detailed summary

## Installation

### Python Environment

```bash
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Environment Variables

```bash
setx OPENAI_API_KEY "your_api_key_here"
```

Optional:

```bash
setx OPENAI_CHAT_MODEL "gpt-4o-mini"
```

Restart your terminal after setting environment variables.

### Frontend Dependencies

```bash
cd smart-librarian-frontend
npm install
```

## Running the Project

### 1. Build or refresh the vector database

Run this after changing the dataset or embedding logic.

```bash
python src/ingest.py
```

### 2. Run the FastAPI backend

```bash
uvicorn src.api:app --reload
```

Backend default URL:

```text
http://localhost:8000
```

### 3. Run the React frontend

```bash
cd smart-librarian-frontend
npm run dev
```

Frontend default URL:

```text
http://localhost:5173
```

### 4. Optional interfaces

CLI recommender:

```bash
python src/rag.py
```

Streamlit app:

```bash
streamlit run src/app.py
```

## API Endpoints

- `GET /`: health/status route
- `POST /recommend`: returns book recommendation, explanation, detailed summary, and retrieved books
- `POST /image`: returns a generated image URL or data URL
- `POST /tts`: returns generated MP3 audio
- `POST /stt`: transcribes uploaded or recorded audio

## Frontend Features

- Chat-style recommendation flow
- Collapsible sidebar
- Voice mode with live recording timer
- Typing indicator and animated message appearance
- Image generation per recommendation
- Audio generation per recommendation
- Recent prompt shortcuts
- Polished dark UI with responsive layout

## Streamlit Features

- Typed input or voice input
- Moderation checks
- Recommendation explanation and detailed summary
- Optional retrieval debug panel
- Generate image and audio actions

## Notes

- `src/tts.py` is the active text-to-speech module used by `src/api.py` and `src/app.py`
- The old duplicate file `src/text_to_speech.py` was redundant and has been removed
- Generated media is intended for UI/demo use and is not persisted as part of chat history

## Example Prompts

- I want a book about freedom and control
- Recommend a fantasy book about friendship and courage
- Suggest a classic about love and social class
- I want a biography similar to Steve Jobs
- Ce carte recomanzi despre război și traumă?