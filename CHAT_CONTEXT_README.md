# Chat History Context System

A fully dynamic, domain-agnostic conversational AI system that maintains chat history and automatically resolves contextual references.

## 🌟 Features

- **Fully Dynamic Entity Detection** - LLM automatically determines entity types (no hardcoded categories)
- **Semantic Reference Resolution** - Resolves pronouns (it, he, she, his, her, their) using context
- **Domain-Agnostic** - Works for ANY domain (resumes, products, locations, etc.)
- **Session-Based** - Multiple independent conversations
- **Context-Aware** - Maintains last 10 messages for context

## 🚀 Quick Start

### 1. Start the Server

```bash
python -m uvicorn src.server:app --reload
```

### 2. Create a Chat Session

```bash
curl -X POST http://localhost:8000/api/chat/new-session
```

Response:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "New chat session created"
}
```

### 3. Send Queries

**First Query (Establish Context):**
```bash
curl -X POST http://localhost:8000/api/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Sriram salary?",
    "session_id": "YOUR_SESSION_ID"
  }'
```

**Follow-up Query (With Pronoun):**
```bash
curl -X POST http://localhost:8000/api/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is his technical skill?",
    "session_id": "YOUR_SESSION_ID"
  }'
```

The system will automatically resolve "his" → "Sriram" using chat history!

## 📋 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat/new-session` | POST | Create new chat session |
| `/api/chat/query` | POST | Send query with context resolution |
| `/api/chat/history/{session_id}` | GET | Retrieve conversation history |
| `/api/chat/clear/{session_id}` | DELETE | Clear session messages |

## 💡 How It Works

### Example: Resume Domain

1. **User:** "What is Sriram's salary?"
   - System extracts: `{"name": "Sriram", "type": "job_candidate"}`
   - Saves to chat history

2. **User:** "What is his technical skill?"
   - System detects pronoun: `"his"`
   - Fetches chat history
   - LLM resolves: `"his" → "Sriram"`
   - Rewrites: "What is Sriram's technical skill?"

### Example: Product Domain

1. **User:** "What is Colgate price?"
   - System extracts: `{"name": "Colgate", "type": "oral_care_product"}`
   - Note: LLM determined "oral_care_product" dynamically!

2. **User:** "What are the chemical components it has?"
   - System detects: `"it"`
   - LLM resolves: `"it" → "Colgate"`
   - Rewrites: "What are the chemical components Colgate has?"

## 🧪 Testing

Run the test script:

```bash
python test_chat_context.py
```

This will test:
- Session creation
- Entity extraction
- Pronoun resolution
- Chat history tracking
- Domain-agnostic operation

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                            │
│  /api/chat/new-session  /api/chat/query  /api/chat/history │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   ChatHistoryManager                        │
│  • Session management                                       │
│  • Message coordination                                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   ContextResolver                           │
│  • Dynamic entity extraction (LLM)                          │
│  • Semantic reference resolution (LLM)                      │
│  • Query rewriting                                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL Database                       │
│  • ChatSession (sessions)                                   │
│  • ChatMessage (messages + entities)                        │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Files

- `src/utils/db_handler.py` - Database models and operations
- `src/utils/context_resolver.py` - Entity extraction and resolution
- `src/utils/chat_manager.py` - Session management
- `src/server.py` - API endpoints
- `test_chat_context.py` - Test script

## 🎯 Key Innovation: Dynamic Entity Types

Instead of hardcoded types like "person", "product", the LLM determines:

| Entity | Context | LLM Type |
|--------|---------|----------|
| Colgate | Price query | `toothpaste_brand` |
| Python | Tech discussion | `programming_language` |
| Apple | Stock price | `publicly_traded_technology_company` |
| Apple | Grocery shopping | `fruit` |

**Zero configuration. Works for ANY domain.**

## 🔧 Configuration

Default context window: 10 messages

To change, modify in `context_resolver.py`:
```python
def get_context_window(self, session_id: str, n: int = 10):
    # Change n to desired window size
```

## 📝 Response Format

```json
{
  "session_id": "uuid",
  "original_query": "What is his technical skill?",
  "resolved_query": "What is Sriram's technical skill?",
  "context_applied": true,
  "confidence": 0.98,
  "entities_used": [
    {
      "name": "Sriram",
      "type": "job_candidate",
      "resolved_from": "his"
    }
  ],
  "tool_detected": "ask",
  "response": "Sriram's technical skills include..."
}
```

## 🚨 Requirements

- Python 3.8+
- PostgreSQL database
- OpenAI API key (for LLM)
- FastAPI
- SQLAlchemy

## 📚 Documentation

- [Implementation Plan](file:///C:/Users/Sriram/.gemini/antigravity/brain/ffff0646-87d8-40cf-9faf-85e890df13b3/implementation_plan.md)
- [Walkthrough](file:///C:/Users/Sriram/.gemini/antigravity/brain/ffff0646-87d8-40cf-9faf-85e890df13b3/walkthrough.md)
- [Task Breakdown](file:///C:/Users/Sriram/.gemini/antigravity/brain/ffff0646-87d8-40cf-9faf-85e890df13b3/task.md)

## 🎉 Success!

The system is fully implemented and ready to use. It provides:
- ✅ Natural conversational AI
- ✅ Automatic context resolution
- ✅ Domain-agnostic operation
- ✅ Session management
- ✅ Entity tracking with dynamic types
