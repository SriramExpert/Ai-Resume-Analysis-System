# Resume AI Suite Frontend

## Setup
1. Enter the directory: `cd Frontend`
2. Install dependencies: `npm install` (User mentions this is done)
3. Run the development server: `npm run dev`

## Features
- **AI Router Chat**: Type any query, and the backend LLM decides which tool to call.
- **Unified Vector Search**: Queries are performed across all uploaded resumes stored in ChromaDB.
- **Glassmorphism UI**: Modern, premium dark-themed design.
- **Candidate Database**: Live view of stored candidates in PostgreSQL.

## Backend Connection
The frontend connects to the FastAPI backend at `http://localhost:8000`. Ensure the backend is running before using the chat.
