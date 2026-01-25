"""
Context Resolver - Handles dynamic entity extraction and reference resolution
using LLM for domain-agnostic chat history context.
"""

from typing import List, Dict, Any, Optional
import json


class ContextResolver:
    """
    Resolves contextual references in queries using chat history and LLM.
    Uses fully dynamic entity type detection - no hardcoded categories.
    """
    
    def __init__(self, llm_handler, db_handler):
        """
        Initialize with LLM handler and database handler.
        
        Args:
            llm_handler: LLMHandler instance for entity extraction and resolution
            db_handler: PostgresHandler instance for accessing chat history
        """
        self.llm = llm_handler
        self.db = db_handler
    
    def resolve_query(self, query: str, session_id: str) -> dict:
        """
        Resolve contextual references in query using chat history.
        
        Args:
            query: User's query that may contain pronouns or implicit references
            session_id: Chat session ID for retrieving history
            
        Returns:
            dict: {
                "original_query": str,
                "resolved_query": str,
                "entities": List[dict],
                "context_used": bool,
                "confidence": float
            }
        """
        # Step 1: Extract entities from current query
        extracted = self.extract_entities_with_types(query)
        
        # Check if query contains pronouns/references (LLM extraction OR keyword match)
        pronoun_keywords = {'he', 'she', 'it', 'they', 'his', 'her', 'their', 'this', 'that'}
        query_words = set(query.lower().split())
        
        has_pronouns_llm = any(e.get('is_pronoun', False) for e in extracted.get('entities', []))
        has_pronouns_keyword = bool(query_words.intersection(pronoun_keywords))
        
        if not (has_pronouns_llm or has_pronouns_keyword):
            # No pronouns detected, return original query with extracted entities
            return {
                "original_query": query,
                "resolved_query": query,
                "entities": extracted.get('entities', []),
                "context_used": False,
                "confidence": 1.0
            }
        
        # Determine pronouns for resolution prompt
        pronouns_list = [e for e in extracted.get('entities', []) if e.get('is_pronoun', False)]
        if not pronouns_list and has_pronouns_keyword:
            # Fallback: Create generic pronoun entities if LLM missed them
            for word in query_words.intersection(pronoun_keywords):
                pronouns_list.append({
                    "pronoun": word,
                    "inferred_type": "unknown",
                    "is_pronoun": True,
                    "context": "keyword match"
                })
            # Add to extracted entities for consistency
            if 'entities' not in extracted:
                extracted['entities'] = []
            extracted['entities'].extend(pronouns_list)
        
        # Step 2: Get chat history for context
        history_messages = self.get_context_window(session_id, n=10)
        
        if not history_messages:
            # No history available, can't resolve
            return {
                "original_query": query,
                "resolved_query": query,
                "entities": extracted.get('entities', []),
                "context_used": False,
                "confidence": 0.0,
                "warning": "No chat history available for context resolution"
            }
        
        # Step 3: Resolve references using LLM
        resolution = self.resolve_references(query, history_messages, extracted.get('entities', []))
        
        return {
            "original_query": query,
            "resolved_query": resolution.get('resolved_query', query),
            "entities": resolution.get('entities', []),
            "context_used": True,
            "confidence": resolution.get('confidence', 0.0),
            "reasoning": resolution.get('reasoning', '')
        }
    
    # In context_resolver.py, update the extract_entities_with_types method

    def extract_entities_with_types(self, query: str) -> dict:
        """
        Use LLM to extract entities with dynamically determined types.
        """
        # First, get all candidate names from database to help the LLM
        all_candidates = []
        try:
            resumes = self.db.get_all_resumes()
            all_candidates = [r.candidate_name for r in resumes if r.candidate_name]
        except:
            pass
        
        candidate_context = ""
        if all_candidates:
            candidate_context = f"\nKnown candidate names in database: {', '.join(all_candidates)}"
        
        prompt = f"""You are an intelligent entity extraction assistant.

    TASK: Extract ALL entities from the query and assign appropriate types based on your understanding.

    IMPORTANT: Entity types are NOT predefined. Determine the most appropriate type for each entity based on context and your world knowledge.

    Query: {query}
    {candidate_context}

    SPECIAL INSTRUCTION: If you see names like "sriram", "gobika", "raju", etc., they are VERY LIKELY job candidates/resume names.

    Instructions:
    - Identify all named entities (people, places, things, concepts, etc.)
    - For ANY proper name that could be a person (especially if it matches known candidates), mark it as "job_candidate" type
    - Assign a descriptive type that best represents the entity in this context
    - Types should be specific and meaningful
    - For pronouns, infer what type of entity they likely refer to
    - ALWAYS identify pronouns ("he", "she", "it", "they", "his", "her", "their", "this", "that").

    Return ONLY valid JSON (no markdown, no extra text):
    {{
    "entities": [
        {{
        "name": "entity_name",
        "type": "your_determined_type",
        "is_pronoun": false,
        "context": "brief context about the entity"
        }}
    ]
    }}
    """
        
        try:
            result = self.llm._call_llm(
                prompt=prompt,
                response_format="json_object",
                temperature=0.1
            )
            
            # Post-process: Ensure candidate names are properly typed
            if 'entities' in result:
                for entity in result['entities']:
                    name = entity.get('name', '').lower()
                    # If it looks like a person name and we have it in our database
                    if name and any(cand.lower() == name for cand in all_candidates):
                        entity['type'] = 'job_candidate'
                        entity['context'] = 'Known candidate from resume database'
            
            return result
        except Exception as e:
            print(f"Error extracting entities: {e}")
            return {"entities": []}
        
    def get_context_window(self, session_id: str, n: int = 10) -> List[dict]:
        """
        Get last N messages with their entities from chat history.
        
        Args:
            session_id: Chat session ID
            n: Number of recent messages to retrieve
            
        Returns:
            List of message dicts with entities
        """
        messages = self.db.get_session_history(session_id, limit=n)
        
        history = []
        for msg in messages:
            history.append({
                "role": msg.role,
                "message": msg.message,
                "entities": msg.entities_mentioned or [],
                "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
            })
        
        return history
    
    def resolve_references(self, query: str, history: List[dict], current_entities: List[dict]) -> dict:
        """
        Use LLM to resolve pronouns/implicit references using semantic reasoning.
        
        Args:
            query: Current query with pronouns
            history: Chat history with entities
            current_entities: Entities extracted from current query
            
        Returns:
            dict: {
                "resolved_query": str,
                "entities": List[dict],
                "confidence": float,
                "reasoning": str
            }
        """
        # Format history for LLM
        history_text = ""
        for msg in history:
            entities_str = json.dumps(msg.get('entities', []))
            history_text += f"- {msg['role'].capitalize()}: \"{msg['message']}\"\n  Entities: {entities_str}\n"
        
        # Extract pronouns from current entities
        pronouns = [e for e in current_entities if e.get('is_pronoun', False)]
        pronouns_str = json.dumps(pronouns)
        
        prompt = f"""You are an intelligent context resolution assistant.

TASK: Resolve what pronouns/references refer to using chat history and semantic reasoning.

Chat History (with entities):
{history_text}

Current Query: {query}
Detected Pronouns/References: {pronouns_str}

Instructions:
- Analyze each pronoun and determine what type of entity it could refer to
- Look at chat history entities and find semantically compatible matches
- Consider recency (more recent mentions are more likely)
- Consider semantic compatibility (does the pronoun usage make sense with this entity?)
- Use your reasoning to pick the most likely entity

Return ONLY valid JSON (no markdown, no extra text):
{{
  "resolutions": [
    {{
      "pronoun": "the pronoun",
      "resolved_entity": "entity name from history",
      "entity_type": "type of the resolved entity",
      "confidence": 0.95,
      "reasoning": "detailed explanation"
    }}
  ],
  "resolved_query": "query rewritten with explicit entity names",
  "needs_clarification": false
}}

If multiple entities are equally likely or no clear match exists:
- Set "needs_clarification": true
- In "reasoning", explain the ambiguity
"""
        
        try:
            # Use unified LLM call
            result = self.llm._call_llm(
                prompt=prompt,
                response_format="json_object",
                temperature=0.1
            )
            
            # Calculate overall confidence
            resolutions = result.get('resolutions', [])
            avg_confidence = sum(r.get('confidence', 0) for r in resolutions) / len(resolutions) if resolutions else 0.0
            
            # Combine resolved entities with non-pronoun entities
            all_entities = [e for e in current_entities if not e.get('is_pronoun', False)]
            for resolution in resolutions:
                all_entities.append({
                    "name": resolution['resolved_entity'],
                    "type": resolution['entity_type'],
                    "is_pronoun": False,
                    "resolved_from": resolution['pronoun']
                })
            
            return {
                "resolved_query": result.get('resolved_query', query),
                "entities": all_entities,
                "confidence": avg_confidence,
                "reasoning": "; ".join([r.get('reasoning', '') for r in resolutions]),
                "needs_clarification": result.get('needs_clarification', False)
            }
        except Exception as e:
            print(f"Error resolving references: {e}")
            return {
                "resolved_query": query,
                "entities": current_entities,
                "confidence": 0.0,
                "reasoning": f"Error: {str(e)}"
            }
