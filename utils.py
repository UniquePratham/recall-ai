import time
import uuid
import httpx
import json
import base64
import mimetypes
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    Filter, FieldCondition, MatchValue, Distance, VectorParams,
    PayloadSchemaType, CreateFieldIndex
)
from config import config, ProviderType
from logging_config import setup_logging, log_error
from exceptions import AIServiceError, DatabaseError

logger = setup_logging()

# Initialize AI clients lazily to avoid dependency issues
ai_clients = {}
qdrant_client = None


def get_ai_client():
    """Get AI client based on configured provider (lazy initialization)"""
    global ai_clients
    provider = config.ai.provider

    if provider not in ai_clients:
        api_key = config.ai.get_api_key()
        base_url = config.ai.get_base_url()

        if provider in ["OpenAI", "GitHub", "Custom"]:
            ai_clients[provider] = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url
            )
        elif provider == "Gemini":
            # For Gemini, we'll use httpx directly
            ai_clients[provider] = httpx.AsyncClient(
                headers={"x-goog-api-key": api_key},
                base_url=base_url,
                timeout=30.0
            )
        elif provider == "Claude":
            # For Claude, we'll use httpx directly
            ai_clients[provider] = httpx.AsyncClient(
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                base_url=base_url,
                timeout=30.0
            )

    return ai_clients[provider]


def get_qdrant_client():
    """Get Qdrant client (lazy initialization)"""
    global qdrant_client
    if qdrant_client is None:
        qdrant_client = AsyncQdrantClient(
            url=config.ai.qdrant_url,
            api_key=config.ai.qdrant_api_key,
            timeout=config.ai.qdrant_timeout,
            prefer_grpc=config.ai.qdrant_prefer_grpc
        )
    return qdrant_client


def get_embedding_dimensions(provider: str, embedding_model: str) -> int:
    """Get the correct embedding dimensions for the provider and model"""
    dimensions_map = {
        "OpenAI": {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072
        },
        "Gemini": {
            "text-embedding-004": 768,
            "embedding-001": 768,
            "embedding-gecko-001": 768
        },
        "Claude": {
            # Claude doesn't have direct embeddings, would use OpenAI compatible
            "text-embedding-ada-002": 1536
        },
        "GitHub": {
            # GitHub Models typically use OpenAI compatible embeddings
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536
        },
        "Custom": {
            # Default for custom providers, should be configured per use case
            "default": 1536
        }
    }

    provider_models = dimensions_map.get(provider, {})
    # Default to 1536 if not found
    return provider_models.get(embedding_model, 1536)


async def ensure_collection_exists(collection_name: str):
    """Ensure the collection exists in Qdrant with correct dimensions and indexes"""
    client = get_qdrant_client()
    try:
        collection_info = await client.get_collection(collection_name)
        # Check if dimensions match current provider
        expected_dims = get_embedding_dimensions(
            config.ai.provider, config.ai.embedding_model)
        actual_dims = collection_info.config.params.vectors.size

        if actual_dims != expected_dims:
            logger.warning(
                f"Collection '{collection_name}' has {actual_dims} dimensions, but current provider needs {expected_dims}. Recreating collection.")
            # Delete and recreate collection with correct dimensions
            await client.delete_collection(collection_name)
            await _create_collection_with_indexes(client, collection_name, expected_dims)
            logger.info(
                f"Recreated collection '{collection_name}' with {expected_dims} dimensions")
        else:
            # Collection exists with correct dimensions, ensure indexes exist
            await _ensure_indexes_exist(client, collection_name)
    except Exception:
        # Collection doesn't exist, create it with correct dimensions and indexes
        expected_dims = get_embedding_dimensions(
            config.ai.provider, config.ai.embedding_model)
        await _create_collection_with_indexes(client, collection_name, expected_dims)
        logger.info(
            f"Created collection '{collection_name}' with {expected_dims} dimensions and indexes")


async def _create_collection_with_indexes(client: AsyncQdrantClient, collection_name: str, dimensions: int):
    """Create collection with proper vector config and payload indexes"""
    await client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE)
    )

    # Create indexes for filtered search
    await _ensure_indexes_exist(client, collection_name)


async def _ensure_indexes_exist(client: AsyncQdrantClient, collection_name: str):
    """Ensure required payload indexes exist for filtering"""
    try:
        # Create index for username field (keyword type for exact matching)
        await client.create_payload_index(
            collection_name=collection_name,
            field_name="username",
            field_schema=PayloadSchemaType.KEYWORD
        )

        # Create index for content_type field (keyword type for exact matching)
        await client.create_payload_index(
            collection_name=collection_name,
            field_name="content_type",
            field_schema=PayloadSchemaType.KEYWORD
        )

        # Create index for timestamp field (float type for range queries)
        await client.create_payload_index(
            collection_name=collection_name,
            field_name="timestamp",
            field_schema=PayloadSchemaType.FLOAT
        )

        logger.info(
            f"Ensured payload indexes exist for collection '{collection_name}'")

    except Exception as e:
        # Indexes might already exist, log but don't fail
        logger.debug(
            f"Note: Some indexes may already exist for collection '{collection_name}': {str(e)}")


async def chat_completion(messages: List[Dict[str, str]], max_tokens: int = 300) -> str:
    """Universal chat completion function for all providers"""
    provider = config.ai.provider
    client = get_ai_client()

    try:
        if provider in ["OpenAI", "GitHub", "Custom"]:
            response = await client.chat.completions.create(
                model=config.ai.model,
                messages=messages,
                max_tokens=max_tokens,
                timeout=30.0
            )
            return response.choices[0].message.content

        elif provider == "Gemini":
            # Gemini API format
            contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(
                    {"role": role, "parts": [{"text": msg["content"]}]})

            response = await client.post(
                f"/models/{config.ai.model}:generateContent",
                json={
                    "contents": contents,
                    "generationConfig": {"maxOutputTokens": max_tokens}
                }
            )
            result = response.json()

            if response.status_code >= 400:
                error_message = result.get("error", {}).get(
                    "message") if isinstance(result, dict) else None
                raise AIServiceError(
                    f"Gemini HTTP {response.status_code}: {error_message or result}"
                )

            if isinstance(result, dict) and "error" in result:
                raise AIServiceError(
                    f"Gemini error: {result['error'].get('message', result['error'])}"
                )

            candidates = result.get("candidates") if isinstance(
                result, dict) else None
            if not candidates:
                raise AIServiceError(
                    f"Gemini returned no candidates: {result}")

            first_candidate = candidates[0]
            content = first_candidate.get("content", {}) if isinstance(
                first_candidate, dict) else {}
            parts = content.get("parts") if isinstance(content, dict) else None
            if not parts:
                raise AIServiceError(
                    f"Gemini returned empty content: {first_candidate}")

            first_part = parts[0] if isinstance(
                parts, list) and parts else None
            if not first_part or "text" not in first_part:
                raise AIServiceError(
                    f"Gemini response missing text content: {first_part}")

            return first_part["text"]

        elif provider == "Claude":
            # Claude API format
            system_msg = ""
            user_messages = []

            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                else:
                    user_messages.append(msg)

            payload = {
                "model": config.ai.model,
                "max_tokens": max_tokens,
                "messages": user_messages
            }
            if system_msg:
                payload["system"] = system_msg

            response = await client.post("/v1/messages", json=payload)
            result = response.json()
            return result["content"][0]["text"]

    except Exception as e:
        raise AIServiceError(
            f"Chat completion failed with {provider}: {str(e)}")


async def generate_embedding(text: str) -> List[float]:
    """Generate embeddings for text using configured provider"""
    start_time = time.time()
    provider = config.ai.provider

    try:
        # Clean and prepare text
        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("Text cannot be empty")

        # Truncate if too long
        if len(cleaned_text) > 8000:
            cleaned_text = cleaned_text[:8000]

        if provider in ["OpenAI", "GitHub", "Custom"]:
            client = get_ai_client()
            response = await client.embeddings.create(
                input=cleaned_text,
                model=config.ai.embedding_model,
                timeout=30.0
            )
            embedding = response.data[0].embedding

        elif provider == "Gemini":
            client = get_ai_client()
            response = await client.post(
                f"/models/{config.ai.embedding_model}:embedContent",
                json={
                    "content": {"parts": [{"text": cleaned_text}]},
                    "taskType": "RETRIEVAL_DOCUMENT"
                }
            )
            result = response.json()
            embedding = result["embedding"]["values"]

        else:
            # Fallback to OpenAI for Claude (Claude doesn't have embedding API)
            fallback_client = AsyncOpenAI(api_key=config.ai.openai_api_key)
            response = await fallback_client.embeddings.create(
                input=cleaned_text,
                model="text-embedding-ada-002",
                timeout=30.0
            )
            embedding = response.data[0].embedding

        logger.info(
            f"Generated embedding ({len(cleaned_text)} chars) with {provider} in {time.time() - start_time:.2f}s")
        return embedding

    except Exception as e:
        log_error(logger, e, {"operation": "generate_embedding",
                  "provider": provider, "text_length": len(text)})
        raise AIServiceError(
            f"Failed to generate embedding with {provider}: {str(e)}")


async def extract_text_from_image(image_file_path: str) -> str:
    """Extract text from image using vision API"""
    start_time = time.time()

    try:
        provider = config.ai.provider

        if provider == "Gemini":
            client = get_ai_client()

            mime_type, _ = mimetypes.guess_type(image_file_path)
            if not mime_type:
                mime_type = "image/jpeg"

            with open(image_file_path, "rb") as image_file:
                base64_image = base64.b64encode(
                    image_file.read()).decode('utf-8')

            response = await client.post(
                f"/models/{config.ai.model}:generateContent",
                json={
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {"text": "Extract all text from this image. Return only the text content."},
                                {
                                    "inline_data": {
                                        "mime_type": mime_type,
                                        "data": base64_image
                                    }
                                }
                            ]
                        }
                    ],
                    "generationConfig": {"maxOutputTokens": 300}
                }
            )

            result_json = response.json()

            if response.status_code >= 400:
                error_message = result_json.get("error", {}).get(
                    "message") if isinstance(result_json, dict) else None
                raise AIServiceError(
                    f"Gemini vision HTTP {response.status_code}: {error_message or result_json}"
                )

            candidates = result_json.get("candidates") if isinstance(
                result_json, dict) else None
            if not candidates:
                raise AIServiceError(
                    f"Gemini vision returned no candidates: {result_json}")

            parts = candidates[0].get("content", {}).get(
                "parts") if isinstance(candidates[0], dict) else None
            if not parts:
                raise AIServiceError(
                    f"Gemini vision returned empty content: {candidates[0]}")

            text_part = parts[0]
            if not isinstance(text_part, dict) or "text" not in text_part:
                raise AIServiceError(
                    f"Gemini vision response missing text content: {text_part}")

            result = text_part["text"]

        else:
            with open(image_file_path, "rb") as image_file:
                base64_image = base64.b64encode(
                    image_file.read()).decode('utf-8')

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract all text from this image. Return only the text content, no descriptions."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]

            # Only OpenAI and compatible providers support vision directly
            if provider in ["OpenAI", "GitHub", "Custom"]:
                client = get_ai_client()
                response = await client.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=messages,
                    max_tokens=300,
                    timeout=30.0
                )
                result = response.choices[0].message.content
            else:
                # Fallback to OpenAI for remaining providers if key is available
                fallback_api_key = config.ai.openai_api_key
                if not fallback_api_key:
                    raise AIServiceError(
                        "Vision extraction requires a compatible provider or OPENAI_API_KEY fallback.")

                fallback_client = AsyncOpenAI(api_key=fallback_api_key)
                response = await fallback_client.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=messages,
                    max_tokens=300,
                    timeout=30.0
                )
                result = response.choices[0].message.content

        logger.info(
            f"Extracted text from image in {time.time() - start_time:.2f}s")
        return result

    except Exception as e:
        log_error(logger, e, {
                  "operation": "extract_text_from_image", "image_path": image_file_path})
        raise AIServiceError(f"Failed to extract text from image: {str(e)}")


async def summarize_text(text: str, max_length: int = 500) -> str:
    """Summarize text using configured AI provider"""
    start_time = time.time()

    try:
        messages = [
            {
                "role": "system",
                "content": f"Summarize the following text in no more than {max_length} characters. Keep the key information and main points."
            },
            {
                "role": "user",
                "content": text
            }
        ]

        result = await chat_completion(messages, max_tokens=150)
        logger.info(
            f"Summarized text ({len(text)} chars) with {config.ai.provider} in {time.time() - start_time:.2f}s")
        return result

    except Exception as e:
        log_error(logger, e, {"operation": "summarize_text",
                  "provider": config.ai.provider, "text_length": len(text)})
        raise AIServiceError(f"Failed to summarize text: {str(e)}")


async def store_in_vector_db(embedding: List[float], text: str, username: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Store embedding and text in Qdrant vector database"""
    start_time = time.time()
    collection_name = config.ai.qdrant_collection_name

    try:
        # Ensure collection exists
        await ensure_collection_exists(collection_name)

        # Prepare point data
        point_id = str(uuid.uuid4())
        payload = {
            "text": text,
            "username": username,
            "timestamp": time.time(),
            "content_type": "general"
        }

        # Add custom metadata if provided
        if metadata:
            payload.update(metadata)

        # Store in Qdrant
        await get_qdrant_client().upsert(
            collection_name=collection_name,
            points=[
                {
                    "id": point_id,
                    "vector": embedding,
                    "payload": payload
                }
            ]
        )

        logger.info(
            f"Stored document for {username}: {len(text)} chars, point_id={point_id}, time={time.time() - start_time:.2f}s")
        return point_id

    except Exception as e:
        log_error(logger, e, {
            "operation": "store_in_vector_db",
            "username": username,
            "text_length": len(text)
        })
        raise DatabaseError(f"Failed to store in vector database: {str(e)}")


async def search_vector_db_enhanced(query_embedding: List[float], username: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Enhanced search with lower score threshold for broader results"""
    start_time = time.time()
    collection_name = config.ai.qdrant_collection_name

    try:
        # Ensure collection exists before attempting to search
        await ensure_collection_exists(collection_name)

        # Create filter for user's data
        user_filter = Filter(
            must=[
                FieldCondition(
                    key="username",
                    match=MatchValue(value=username)
                )
            ]
        )

        # Search similar vectors with lower score threshold for broader results
        search_result = await get_qdrant_client().search(
            collection_name=collection_name,
            query_vector=query_embedding,
            query_filter=user_filter,
            limit=limit,
            with_payload=True,
            score_threshold=0.3  # Lower threshold to catch more results
        )

        # Format results
        results = [
            {
                "id": hit.id,
                "score": hit.score,
                "text": hit.payload.get("text", ""),
                "timestamp": hit.payload.get("timestamp", 0),
                "content_type": hit.payload.get("content_type", "general"),
                "metadata": {k: v for k, v in hit.payload.items() if k not in ["text", "username", "timestamp", "content_type"]}
            }
            for hit in search_result
        ]

        logger.info(
            f"Enhanced search for {username}: found {len(results)} results, limit={limit}, time={time.time() - start_time:.2f}s")
        return results

    except Exception as e:
        log_error(logger, e, {
            "operation": "search_vector_db_enhanced",
            "username": username,
            "limit": limit
        })
        raise DatabaseError(f"Failed to search vector database: {str(e)}")


async def search_vector_db(query_embedding: List[float], username: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search vector database for similar content"""
    start_time = time.time()
    collection_name = config.ai.qdrant_collection_name

    try:
        # Ensure collection exists before attempting to search
        await ensure_collection_exists(collection_name)

        # Create filter for user's data
        user_filter = Filter(
            must=[
                FieldCondition(
                    key="username",
                    match=MatchValue(value=username)
                )
            ]
        )

        # Search similar vectors
        search_result = await get_qdrant_client().search(
            collection_name=collection_name,
            query_vector=query_embedding,
            query_filter=user_filter,
            limit=limit,
            with_payload=True
        )

        # Format results
        results = [
            {
                "id": hit.id,
                "score": hit.score,
                "text": hit.payload.get("text", ""),
                "timestamp": hit.payload.get("timestamp", 0),
                "content_type": hit.payload.get("content_type", "general"),
                "metadata": {k: v for k, v in hit.payload.items() if k not in ["text", "username", "timestamp", "content_type"]}
            }
            for hit in search_result
        ]

        logger.info(
            f"Search for {username}: found {len(results)} results, limit={limit}, time={time.time() - start_time:.2f}s")
        return results

    except Exception as e:
        log_error(logger, e, {
            "operation": "search_vector_db",
            "username": username,
            "limit": limit
        })
        raise DatabaseError(f"Failed to search vector database: {str(e)}")


async def search_cache_first(query: str, username: str, limit: int = 10) -> str:
    """Search cache first, then vector database if no cached results found"""
    start_time = time.time()

    try:
        from cache_manager import cache_manager

        # First, check if we have a cached result for this exact query
        cached_searches = cache_manager.get_cached_searches(username, limit=20)

        for cached_search in cached_searches:
            # Check for exact match or very similar query
            if (cached_search.query.lower() == query.lower() or
                (len(query) > 10 and query.lower() in cached_search.query.lower()) or
                    (len(cached_search.query) > 10 and cached_search.query.lower() in query.lower())):

                logger.info(
                    f"Cache hit for {username}: using cached result for '{query}'")

                # Update cache position (move to most recent)
                cache_manager.cache_search_result(
                    query, cached_search.results, username)

                # Generate response from cached results
                if cached_search.results:
                    context = "\n\n".join([
                        f"Content {i+1} (relevance: {result['score']:.3f}):\n{result['text']}"
                        for i, result in enumerate(cached_search.results)
                    ])

                    messages = [
                        {
                            "role": "system",
                            "content": """You are a helpful assistant that answers questions based on the user's personal knowledge base. 
                            When the user asks to "list all" or for multiple items, provide a comprehensive list showing ALL relevant results found.
                            For each item, include the website name/URL and key details.
                            Provide direct, clean answers without any formatting like 'Your Question:', 'Answer:', or markdown symbols like **. 
                            If referring to files or links, present them clearly with proper formatting. 
                            Keep responses organized and helpful. If you don't have the information, simply say so."""
                        },
                        {
                            "role": "user",
                            "content": f"Context:\n{context}\n\nQuestion: {query}"
                        }
                    ]

                    result = await chat_completion(messages, max_tokens=800)
                    logger.info(
                        f"Cache-based query for {username}: {len(result)} chars response, time={time.time() - start_time:.2f}s")
                    return result
                else:
                    return "I couldn't find any relevant information in your knowledge base for this query."

        # No cache hit, search vector database
        logger.info(
            f"Cache miss for {username}: searching vector database for '{query}'")
        return await query_knowledge_base(query, username, limit)

    except Exception as e:
        log_error(logger, e, {
            "operation": "search_cache_first",
            "username": username,
            "query_length": len(query)
        })
        raise AIServiceError(
            f"Failed to search with cache-first logic: {str(e)}")


async def query_knowledge_base(query: str, username: str, limit: int = 10) -> str:
    """Query the knowledge base and generate a response"""
    start_time = time.time()

    try:
        # For queries asking for "all" or "list", increase the search limit
        if any(word in query.lower() for word in ['all', 'list', 'every', 'entire', 'complete']):
            limit = min(limit * 2, 20)  # Double the limit for comprehensive queries
        
        # Generate embedding for the query
        query_embedding = await generate_embedding(query)

        # Search for relevant content with lower score threshold for broader results
        search_results = await search_vector_db_enhanced(query_embedding, username, limit)

        if not search_results:
            return "I couldn't find any relevant information in your knowledge base for this query."

        # Cache the search results for later use
        from cache_manager import cache_manager
        cache_manager.cache_search_result(query, search_results, username)

        # Prepare context from search results
        context = "\n\n".join([
            f"Content {i+1} (relevance: {result['score']:.3f}):\n{result['text']}"
            for i, result in enumerate(search_results)
        ])

        # Generate response using configured AI provider with enhanced system prompt
        messages = [
            {
                "role": "system",
                "content": """You are a helpful assistant that answers questions based on the user's personal knowledge base. 
                When the user asks to "list all" or for multiple items, provide a comprehensive list showing ALL relevant results found.
                For each item, include the website name/URL and key details.
                Provide direct, clean answers without any formatting like 'Your Question:', 'Answer:', or markdown symbols like **. 
                If referring to files or links, present them clearly with proper formatting. 
                Keep responses organized and helpful. If you don't have the information, simply say so.
                
                Special handling:
                - If a website shows 404 or access errors, mention it but still include it in the list
                - Focus on providing complete information rather than just mentioning one result
                - Group similar items together when appropriate"""
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {query}"
            }
        ]

        result = await chat_completion(messages, max_tokens=800)
        logger.info(
            f"Query for {username}: {len(query)} chars query, {len(search_results)} results, {len(result)} chars response, time={time.time() - start_time:.2f}s")
        return result

    except Exception as e:
        log_error(logger, e, {
            "operation": "query_knowledge_base",
            "username": username,
            "query_length": len(query)
        })
        raise AIServiceError(f"Failed to query knowledge base: {str(e)}")


async def delete_memories_by_terms(search_terms: str, username: str, preview_only: bool = True) -> tuple:
    """Delete memories containing specific terms"""
    start_time = time.time()
    collection_name = config.ai.qdrant_collection_name

    try:
        # Ensure collection exists
        await ensure_collection_exists(collection_name)

        # Generate embedding for search terms
        query_embedding = await generate_embedding(search_terms)

        # Search for matching memories with high limit to find all matches
        user_filter = Filter(
            must=[
                FieldCondition(
                    key="username",
                    match=MatchValue(value=username)
                )
            ]
        )

        # Get all matching results
        search_results = await get_qdrant_client().search(
            collection_name=collection_name,
            query_vector=query_embedding,
            query_filter=user_filter,
            limit=1000,  # High limit to get all matches
            with_payload=True,
            score_threshold=0.1  # Lower threshold to catch more matches
        )

        # Filter results that actually contain the search terms (case-insensitive)
        matching_results = []
        search_terms_lower = search_terms.lower()

        for hit in search_results:
            text = hit.payload.get("text", "").lower()
            if search_terms_lower in text:
                matching_results.append(hit)

        if not matching_results:
            return 0, "No matching memories found."

        if preview_only:
            # Return preview information
            preview_lines = []
            # Show first 5 matches
            for i, hit in enumerate(matching_results[:5]):
                text_snippet = hit.payload.get("text", "")[:100]
                if len(text_snippet) == 100:
                    text_snippet += "..."
                content_type = hit.payload.get("content_type", "general")
                preview_lines.append(f"{i+1}. [{content_type}] {text_snippet}")

            if len(matching_results) > 5:
                preview_lines.append(
                    f"... and {len(matching_results) - 5} more memories")

            preview = "\n".join(preview_lines)
            return len(matching_results), preview

        # Actually delete the memories
        point_ids = [hit.id for hit in matching_results]

        await get_qdrant_client().delete(
            collection_name=collection_name,
            points_selector=point_ids
        )

        # Generate summary
        content_types = {}
        for hit in matching_results:
            content_type = hit.payload.get("content_type", "general")
            content_types[content_type] = content_types.get(
                content_type, 0) + 1

        summary_parts = [
            f"• {count} {content_type} memories" for content_type, count in content_types.items()]
        summary = "\n".join(summary_parts)

        logger.info(
            f"Deleted {len(matching_results)} memories for {username} containing '{search_terms}' in {time.time() - start_time:.2f}s")
        return len(matching_results), summary

    except Exception as e:
        log_error(logger, e, {
            "operation": "delete_memories_by_terms",
            "username": username,
            "search_terms": search_terms
        })
        raise DatabaseError(f"Failed to delete memories: {str(e)}")


async def clear_all_memories(username: str, preview_only: bool = True) -> int:
    """Clear all memories for a user"""
    start_time = time.time()
    collection_name = config.ai.qdrant_collection_name

    try:
        # Ensure collection exists
        await ensure_collection_exists(collection_name)

        # Create filter for user's data
        user_filter = Filter(
            must=[
                FieldCondition(
                    key="username",
                    match=MatchValue(value=username)
                )
            ]
        )

        # Get all user's memories to count them
        search_results = await get_qdrant_client().search(
            collection_name=collection_name,
            query_vector=[0.0] * get_embedding_dimensions(
                config.ai.provider, config.ai.embedding_model),  # Dummy vector
            query_filter=user_filter,
            limit=10000,  # Very high limit to get all
            with_payload=False  # We only need IDs for deletion
        )

        total_count = len(search_results)

        if preview_only:
            return total_count

        if total_count == 0:
            return 0

        # Delete all user memories
        point_ids = [hit.id for hit in search_results]

        await get_qdrant_client().delete(
            collection_name=collection_name,
            points_selector=point_ids
        )

        logger.info(
            f"Cleared {total_count} memories for {username} in {time.time() - start_time:.2f}s")
        return total_count

    except Exception as e:
        log_error(logger, e, {
            "operation": "clear_all_memories",
            "username": username
        })
        raise DatabaseError(f"Failed to clear all memories: {str(e)}")
