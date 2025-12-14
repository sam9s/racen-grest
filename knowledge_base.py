"""
Knowledge Base / RAG Module for JoveHeal Chatbot

This module handles:
- Document ingestion (web scraping, PDF, text files)
- Vector storage using ChromaDB
- Retrieval for RAG queries
"""

import os
import json
import hashlib
from pathlib import Path
from typing import List, Optional

import chromadb
from chromadb.config import Settings
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from web_scraper import scrape_joveheal_website

KNOWLEDGE_BASE_DIR = Path("knowledge_base")
VECTOR_DB_DIR = Path("vector_db")
DOCUMENTS_DIR = KNOWLEDGE_BASE_DIR / "documents"
METADATA_FILE = KNOWLEDGE_BASE_DIR / "metadata.json"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def ensure_directories():
    """Ensure all necessary directories exist."""
    KNOWLEDGE_BASE_DIR.mkdir(exist_ok=True)
    DOCUMENTS_DIR.mkdir(exist_ok=True)
    VECTOR_DB_DIR.mkdir(exist_ok=True)


def get_chroma_client():
    """Get or create ChromaDB client."""
    ensure_directories()
    return chromadb.PersistentClient(
        path=str(VECTOR_DB_DIR),
        settings=Settings(anonymized_telemetry=False)
    )


def get_or_create_collection(client=None):
    """Get or create the JoveHeal knowledge collection."""
    if client is None:
        client = get_chroma_client()
    
    return client.get_or_create_collection(
        name="joveheal_knowledge",
        metadata={"description": "JoveHeal website and document knowledge base"}
    )


def load_metadata() -> dict:
    """Load knowledge base metadata."""
    ensure_directories()
    if METADATA_FILE.exists():
        try:
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"documents": [], "last_scrape": None}
    return {"documents": [], "last_scrape": None}


def save_metadata(metadata: dict):
    """Save knowledge base metadata."""
    ensure_directories()
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, default=str)


def generate_doc_id(content: str, source: str, chunk_index: int) -> str:
    """Generate a unique ID for a document chunk using full content."""
    hash_input = f"{source}:{chunk_index}:{content}"
    return hashlib.md5(hash_input.encode()).hexdigest()


def is_valid_text_content(text: str, min_printable_ratio: float = 0.85) -> bool:
    """
    Validate that text content is mostly printable characters.
    Rejects binary/encoded content that would poison the knowledge base.
    """
    if not text or len(text.strip()) < 50:
        return False
    
    printable_chars = sum(1 for c in text if c.isprintable() or c in '\n\r\t')
    ratio = printable_chars / len(text)
    
    return ratio >= min_printable_ratio


def split_text_into_chunks(text: str, source: str = "") -> List[dict]:
    """Split text into chunks for embedding."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    chunks = splitter.split_text(text)
    
    return [
        {
            "id": generate_doc_id(chunk, source, i),
            "content": chunk,
            "source": source,
            "chunk_index": i
        }
        for i, chunk in enumerate(chunks)
    ]


def clear_website_chunks():
    """Remove all website-sourced chunks from the collection."""
    try:
        collection = get_or_create_collection()
        results = collection.get(where={"type": "website"})
        if results and results.get("ids"):
            collection.delete(ids=results["ids"])
            print(f"Cleared {len(results['ids'])} existing website chunks.")
    except Exception as e:
        print(f"Error clearing website chunks: {e}")


def ingest_website_content(max_pages: int = 50, clear_existing: bool = True) -> int:
    """
    Scrape the JoveHeal website and add content to the knowledge base.
    Returns the number of chunks added.
    
    WARNING: Website scraping may produce unreliable results due to encoding issues.
    Prefer using document uploads for reliable content ingestion.
    """
    from datetime import datetime
    
    print("Scraping JoveHeal website...")
    documents = scrape_joveheal_website(max_pages=max_pages)
    
    if not documents:
        print("No content found from website.")
        return 0
    
    if clear_existing:
        clear_website_chunks()
        metadata = load_metadata()
        metadata["website_pages"] = 0
        metadata["website_chunks"] = 0
        save_metadata(metadata)
    
    collection = get_or_create_collection()
    chunks_added = 0
    chunks_rejected = 0
    
    for doc in documents:
        if not is_valid_text_content(doc["content"]):
            print(f"  Rejecting invalid content from {doc['url']}")
            chunks_rejected += 1
            continue
            
        chunks = split_text_into_chunks(doc["content"], doc["url"])
        
        for chunk in chunks:
            if not is_valid_text_content(chunk["content"], min_printable_ratio=0.90):
                chunks_rejected += 1
                continue
                
            try:
                collection.upsert(
                    ids=[chunk["id"]],
                    documents=[chunk["content"]],
                    metadatas=[{
                        "source": chunk["source"],
                        "type": "website",
                        "chunk_index": chunk["chunk_index"]
                    }]
                )
                chunks_added += 1
            except Exception as e:
                print(f"Error adding chunk: {e}")
    
    metadata = load_metadata()
    metadata["last_scrape"] = datetime.now().isoformat()
    metadata["website_pages"] = len(documents)
    metadata["website_chunks"] = chunks_added
    save_metadata(metadata)
    
    print(f"Added {chunks_added} chunks from {len(documents)} pages (rejected {chunks_rejected} invalid chunks).")
    return chunks_added


def ingest_pdf_file(file_path: str, original_filename: str = None) -> int:
    """
    Ingest a PDF file into the knowledge base.
    Returns the number of chunks added.
    """
    if original_filename is None:
        original_filename = os.path.basename(file_path)
    
    try:
        reader = PdfReader(file_path)
        text_content = ""
        
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_content += page_text + "\n\n"
        
        if not text_content.strip():
            print(f"No text content found in PDF: {original_filename}")
            return 0
        
        if not is_valid_text_content(text_content):
            print(f"PDF content failed validation (binary/malformed): {original_filename}")
            return 0
        
        chunks = split_text_into_chunks(text_content, f"PDF: {original_filename}")
        collection = get_or_create_collection()
        chunks_added = 0
        
        for chunk in chunks:
            if not is_valid_text_content(chunk["content"], min_printable_ratio=0.90):
                continue
            try:
                collection.upsert(
                    ids=[chunk["id"]],
                    documents=[chunk["content"]],
                    metadatas=[{
                        "source": original_filename,
                        "type": "pdf",
                        "chunk_index": chunk["chunk_index"]
                    }]
                )
                chunks_added += 1
            except Exception as e:
                print(f"Error adding chunk: {e}")
        
        metadata = load_metadata()
        if "documents" not in metadata:
            metadata["documents"] = []
        existing_doc = next((d for d in metadata["documents"] if d["filename"] == original_filename), None)
        if existing_doc:
            existing_doc["chunks"] = chunks_added
        else:
            metadata["documents"].append({
                "filename": original_filename,
                "type": "pdf",
                "chunks": chunks_added
            })
        save_metadata(metadata)
        
        print(f"Added {chunks_added} chunks from PDF: {original_filename}")
        return chunks_added
        
    except Exception as e:
        print(f"Error processing PDF {original_filename}: {e}")
        return 0


def ingest_text_file(file_path: str, original_filename: str = None) -> int:
    """
    Ingest a text file into the knowledge base.
    Returns the number of chunks added.
    """
    if original_filename is None:
        original_filename = os.path.basename(file_path)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text_content = f.read()
        
        if not text_content.strip():
            print(f"No content found in text file: {original_filename}")
            return 0
        
        if not is_valid_text_content(text_content):
            print(f"Text file content failed validation (binary/malformed): {original_filename}")
            return 0
        
        chunks = split_text_into_chunks(text_content, f"Document: {original_filename}")
        collection = get_or_create_collection()
        chunks_added = 0
        
        for chunk in chunks:
            if not is_valid_text_content(chunk["content"], min_printable_ratio=0.90):
                continue
            try:
                collection.upsert(
                    ids=[chunk["id"]],
                    documents=[chunk["content"]],
                    metadatas=[{
                        "source": original_filename,
                        "type": "text",
                        "chunk_index": chunk["chunk_index"]
                    }]
                )
                chunks_added += 1
            except Exception as e:
                print(f"Error adding chunk: {e}")
        
        metadata = load_metadata()
        if "documents" not in metadata:
            metadata["documents"] = []
        existing_doc = next((d for d in metadata["documents"] if d["filename"] == original_filename), None)
        if existing_doc:
            existing_doc["chunks"] = chunks_added
        else:
            metadata["documents"].append({
                "filename": original_filename,
                "type": "text",
                "chunks": chunks_added
            })
        save_metadata(metadata)
        
        print(f"Added {chunks_added} chunks from text file: {original_filename}")
        return chunks_added
        
    except Exception as e:
        print(f"Error processing text file {original_filename}: {e}")
        return 0


def ingest_coaching_transcript(text_content: str, topic: str, video_title: str, speaker: str = "Shweta", youtube_url: str = None) -> int:
    """
    Ingest a coaching video transcript into the knowledge base with topic metadata.
    Used for SOMERA's coaching knowledge.
    
    Args:
        text_content: The full transcript text
        topic: Topic category (e.g., "procrastination", "peace", "relationships")
        video_title: Title of the video
        speaker: Speaker name (default: Shweta)
        youtube_url: YouTube video URL for reference
    
    Returns the number of chunks added.
    """
    if not text_content.strip():
        print(f"No content found in transcript: {video_title}")
        return 0
    
    if not is_valid_text_content(text_content):
        print(f"Transcript content failed validation: {video_title}")
        return 0
    
    source_name = f"Coaching: {video_title}"
    chunks = split_text_into_chunks(text_content, source_name)
    collection = get_or_create_collection()
    chunks_added = 0
    
    for chunk in chunks:
        if not is_valid_text_content(chunk["content"], min_printable_ratio=0.90):
            continue
        try:
            chunk_metadata = {
                "source": source_name,
                "type": "coaching_transcript",
                "topic": topic.lower(),
                "speaker": speaker,
                "video_title": video_title,
                "chunk_index": chunk["chunk_index"]
            }
            if youtube_url:
                chunk_metadata["youtube_url"] = youtube_url
            collection.upsert(
                ids=[chunk["id"]],
                documents=[chunk["content"]],
                metadatas=[chunk_metadata]
            )
            chunks_added += 1
        except Exception as e:
            print(f"Error adding chunk: {e}")
    
    metadata = load_metadata()
    if "coaching_transcripts" not in metadata:
        metadata["coaching_transcripts"] = []
    
    existing = next((t for t in metadata["coaching_transcripts"] if t["video_title"] == video_title), None)
    if existing:
        existing["chunks"] = chunks_added
        existing["topic"] = topic.lower()
        if youtube_url:
            existing["youtube_url"] = youtube_url
    else:
        transcript_meta = {
            "video_title": video_title,
            "topic": topic.lower(),
            "speaker": speaker,
            "chunks": chunks_added
        }
        if youtube_url:
            transcript_meta["youtube_url"] = youtube_url
        metadata["coaching_transcripts"].append(transcript_meta)
    save_metadata(metadata)
    
    print(f"Added {chunks_added} chunks from coaching transcript: {video_title} (topic: {topic})")
    return chunks_added


def search_coaching_content(query: str, n_results: int = 5, topic: str = None) -> List[dict]:
    """
    Search only coaching content for SOMERA responses.
    Optionally filter by topic.
    
    Args:
        query: Search query
        n_results: Number of results to return
        topic: Optional topic filter (e.g., "procrastination")
    
    Returns a list of matching documents with metadata.
    """
    try:
        collection = get_or_create_collection()
        
        count = collection.count()
        if count == 0:
            return []
        
        where_filter = {"type": "coaching_transcript"}
        if topic:
            where_filter = {"$and": [
                {"type": "coaching_transcript"},
                {"topic": topic.lower()}
            ]}
        
        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, count),
            where=where_filter
        )
        
        if not results or not results.get("documents") or not results["documents"][0]:
            return []
        
        documents = []
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
            distance = results["distances"][0][i] if results.get("distances") else None
            
            documents.append({
                "content": doc,
                "source": metadata.get("source", "Unknown"),
                "type": metadata.get("type", "Unknown"),
                "topic": metadata.get("topic", "general"),
                "speaker": metadata.get("speaker", "Unknown"),
                "video_title": metadata.get("video_title", "Unknown"),
                "youtube_url": metadata.get("youtube_url"),
                "relevance_score": 1 - distance if distance else None
            })
        
        return documents
        
    except Exception as e:
        print(f"Error searching coaching content: {e}")
        return []


def get_coaching_stats() -> dict:
    """Get statistics about coaching content in the knowledge base."""
    metadata = load_metadata()
    transcripts = metadata.get("coaching_transcripts", [])
    
    topics = {}
    total_chunks = 0
    for t in transcripts:
        topic = t.get("topic", "general")
        chunks = t.get("chunks", 0)
        if topic not in topics:
            topics[topic] = {"count": 0, "chunks": 0}
        topics[topic]["count"] += 1
        topics[topic]["chunks"] += chunks
        total_chunks += chunks
    
    return {
        "total_transcripts": len(transcripts),
        "total_chunks": total_chunks,
        "topics": topics,
        "transcripts": transcripts
    }


def search_knowledge_base(query: str, n_results: int = 5) -> List[dict]:
    """
    Search the knowledge base for relevant content.
    Returns a list of matching documents with their metadata.
    """
    try:
        collection = get_or_create_collection()
        
        count = collection.count()
        if count == 0:
            return []
        
        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, count)
        )
        
        if not results or not results.get("documents"):
            return []
        
        documents = []
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
            distance = results["distances"][0][i] if results.get("distances") else None
            
            documents.append({
                "content": doc,
                "source": metadata.get("source", "Unknown"),
                "type": metadata.get("type", "Unknown"),
                "relevance_score": 1 - distance if distance else None
            })
        
        return documents
        
    except Exception as e:
        print(f"Error searching knowledge base: {e}")
        return []


def get_knowledge_base_stats() -> dict:
    """Get statistics about the knowledge base."""
    metadata = load_metadata()
    
    try:
        collection = get_or_create_collection()
        total_chunks = collection.count()
    except Exception:
        total_chunks = 0
    
    return {
        "total_chunks": total_chunks,
        "last_scrape": metadata.get("last_scrape"),
        "website_pages": metadata.get("website_pages", 0),
        "documents": metadata.get("documents", [])
    }


def clear_knowledge_base():
    """Clear all content from the knowledge base."""
    try:
        client = get_chroma_client()
        try:
            client.delete_collection("joveheal_knowledge")
        except Exception:
            pass
        
        metadata = {"documents": [], "last_scrape": None}
        save_metadata(metadata)
        
        print("Knowledge base cleared.")
        return True
    except Exception as e:
        print(f"Error clearing knowledge base: {e}")
        return False


def load_sample_documents() -> int:
    """Load sample documents from the documents directory."""
    chunks_added = 0
    
    if DOCUMENTS_DIR.exists():
        for file_path in DOCUMENTS_DIR.iterdir():
            if file_path.suffix.lower() == '.txt':
                chunks = ingest_text_file(str(file_path), file_path.name)
                chunks_added += chunks
            elif file_path.suffix.lower() == '.pdf':
                chunks = ingest_pdf_file(str(file_path), file_path.name)
                chunks_added += chunks
    
    return chunks_added


def initialize_knowledge_base(force_refresh: bool = False, enable_web_scrape: bool = False) -> bool:
    """
    Initialize the knowledge base.
    Loads sample documents first, then optionally scrapes website.
    
    Args:
        force_refresh: If True, clear all content and rebuild
        enable_web_scrape: If True, attempt to scrape the JoveHeal website
                          (disabled by default due to encoding issues)
    """
    ensure_directories()
    
    stats = get_knowledge_base_stats()
    
    if stats["total_chunks"] > 0 and not force_refresh:
        print(f"Knowledge base already initialized with {stats['total_chunks']} chunks.")
        return True
    
    if force_refresh:
        clear_knowledge_base()
    
    chunks_added = 0
    
    print("Loading sample documents...")
    sample_chunks = load_sample_documents()
    chunks_added += sample_chunks
    print(f"Loaded {sample_chunks} chunks from sample documents.")
    
    if enable_web_scrape:
        print("Attempting website scraping (experimental)...")
        website_chunks = ingest_website_content(max_pages=30)
        chunks_added += website_chunks
    
    return chunks_added > 0
