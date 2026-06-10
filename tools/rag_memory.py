"""
tools/rag_memory.py — TOM's RAG (Retrieval-Augmented Generation) Brain

This is TOM's long-term semantic memory. Unlike simple chat history (which only
remembers recent messages), RAG remembers EVERYTHING semantically:
  - Every conversation you've had with TOM
  - Every document TOM has created or read
  - Every piece of knowledge TOM has researched
  - Any files or notes you tell TOM to remember

When you give TOM a command, it retrieves the most relevant knowledge from its
entire history and uses that to give you a smarter, more contextual answer.

Architecture:
  - ChromaDB: local vector database (no cloud, runs 100% on your machine)
  - nomic-embed-text: Ollama embedding model converts text → 768-dim vectors
  - Semantic search: finds relevant memories by meaning, not just keywords

Install: pip install chromadb
"""

import os
import json
import time
import hashlib
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime
from tools.project_paths import project_path_str

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

CHROMA_DIR = project_path_str("tom_brain", "chroma_db")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")

# Collection names inside ChromaDB
COLL_CONVERSATIONS = "conversations"
COLL_KNOWLEDGE     = "knowledge"
COLL_DOCUMENTS     = "documents"
COLL_STRATEGIES    = "strategies"   # learned successful approaches


# ── Embedding via Ollama ─────────────────────────────────────────────────────

def _embed_text(text: str) -> Optional[List[float]]:
    """Generate embeddings using the local Ollama nomic-embed-text model."""
    try:
        import urllib.request
        payload = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
        req = urllib.request.Request(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data.get("embedding")
    except Exception as e:
        logger.warning(f"[RAG] Embedding failed: {e}")
        return None


# ── ChromaDB Setup ───────────────────────────────────────────────────────────

def _get_chroma_client():
    """Return a persistent ChromaDB client, creating the directory if needed."""
    import chromadb
    os.makedirs(CHROMA_DIR, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_DIR)


def _get_or_create_collection(client, name: str):
    """Get or create a ChromaDB collection with cosine similarity."""
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


# ── RAGMemory Class ──────────────────────────────────────────────────────────

class RAGMemory:
    """
    TOM's semantic long-term memory.

    Usage:
        rag = RAGMemory()
        rag.store_conversation("user", "remind me about my meeting tomorrow")
        rag.store_knowledge("Python asyncio", "asyncio is Python's async framework...")
        results = rag.retrieve("meeting tomorrow", top_k=5)
    """

    def __init__(self):
        self._available = False
        try:
            self._client = _get_chroma_client()
            self._conv_coll   = _get_or_create_collection(self._client, COLL_CONVERSATIONS)
            self._know_coll   = _get_or_create_collection(self._client, COLL_KNOWLEDGE)
            self._doc_coll    = _get_or_create_collection(self._client, COLL_DOCUMENTS)
            self._strat_coll  = _get_or_create_collection(self._client, COLL_STRATEGIES)
            self._available = True
            logger.info("[RAG] ChromaDB connected. TOM's brain is active.")
        except ImportError:
            logger.warning("[RAG] chromadb not installed. Run: pip install chromadb")
        except Exception as e:
            logger.warning(f"[RAG] Could not initialise ChromaDB: {e}")

    @property
    def available(self) -> bool:
        return self._available

    # ── ID helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _make_id(text: str) -> str:
        """Create a stable unique ID from text content."""
        return hashlib.sha256((text + str(time.time())).encode()).hexdigest()[:32]

    # ── Store ────────────────────────────────────────────────────────────────

    def store_conversation(self, role: str, content: str,
                           metadata: Optional[Dict] = None) -> bool:
        """Store a conversation turn (user or assistant) in RAG memory."""
        if not self._available or not content.strip():
            return False
        try:
            embedding = _embed_text(content)
            if embedding is None:
                return False
            doc_id = self._make_id(content)
            meta = {
                "role": role,
                "timestamp": datetime.now().isoformat(),
                "type": "conversation",
                **(metadata or {}),
            }
            self._conv_coll.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[meta],
            )
            return True
        except Exception as e:
            logger.debug(f"[RAG] store_conversation error: {e}")
            return False

    def store_knowledge(self, topic: str, content: str,
                        source: str = "research") -> bool:
        """Store a piece of knowledge TOM has researched or been told."""
        if not self._available or not content.strip():
            return False
        try:
            combined = f"Topic: {topic}\n\n{content}"
            embedding = _embed_text(combined)
            if embedding is None:
                return False
            doc_id = self._make_id(combined)
            meta = {
                "topic": topic,
                "source": source,
                "timestamp": datetime.now().isoformat(),
                "type": "knowledge",
            }
            self._know_coll.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[combined],
                metadatas=[meta],
            )
            return True
        except Exception as e:
            logger.debug(f"[RAG] store_knowledge error: {e}")
            return False

    def store_document(self, filename: str, content: str,
                       doc_type: str = "file") -> bool:
        """Store a document (Word, PDF, code file, etc.) in RAG memory."""
        if not self._available or not content.strip():
            return False
        try:
            # Chunk large documents into 1000-char segments with 200-char overlap
            chunks = _chunk_text(content, chunk_size=1000, overlap=200)
            for i, chunk in enumerate(chunks):
                labeled = f"File: {filename} (chunk {i+1}/{len(chunks)})\n\n{chunk}"
                embedding = _embed_text(labeled)
                if embedding is None:
                    continue
                doc_id = self._make_id(labeled)
                self._doc_coll.add(
                    ids=[doc_id],
                    embeddings=[embedding],
                    documents=[labeled],
                    metadatas=[{
                        "filename": filename,
                        "doc_type": doc_type,
                        "chunk": i,
                        "timestamp": datetime.now().isoformat(),
                        "type": "document",
                    }],
                )
            return True
        except Exception as e:
            logger.debug(f"[RAG] store_document error: {e}")
            return False

    def store_strategy(self, command_pattern: str, approach: str,
                       outcome: str, score: float = 1.0) -> bool:
        """Store a successful strategy TOM has learned."""
        if not self._available:
            return False
        try:
            content = (f"Pattern: {command_pattern}\n"
                       f"Approach: {approach}\n"
                       f"Outcome: {outcome}\n"
                       f"Score: {score}")
            embedding = _embed_text(content)
            if embedding is None:
                return False
            doc_id = self._make_id(content)
            self._strat_coll.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[{
                    "pattern": command_pattern,
                    "score": score,
                    "timestamp": datetime.now().isoformat(),
                    "type": "strategy",
                }],
            )
            return True
        except Exception as e:
            logger.debug(f"[RAG] store_strategy error: {e}")
            return False

    # ── Retrieve ─────────────────────────────────────────────────────────────

    def retrieve(self, query: str, top_k: int = 5,
                 collections: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve the most semantically relevant memories for a query.

        Args:
            query: The user's command or question.
            top_k: How many results to return per collection.
            collections: Which collections to search. None = all.

        Returns:
            List of dicts with 'text', 'type', 'score', 'metadata'.
        """
        if not self._available:
            return []

        embedding = _embed_text(query)
        if embedding is None:
            return []

        all_colls = {
            COLL_CONVERSATIONS: self._conv_coll,
            COLL_KNOWLEDGE:     self._know_coll,
            COLL_DOCUMENTS:     self._doc_coll,
            COLL_STRATEGIES:    self._strat_coll,
        }
        search_colls = (
            {k: v for k, v in all_colls.items() if k in collections}
            if collections else all_colls
        )

        results = []
        for coll_name, coll in search_colls.items():
            try:
                count = coll.count()
                if count == 0:
                    continue
                k = min(top_k, count)
                res = coll.query(
                    query_embeddings=[embedding],
                    n_results=k,
                    include=["documents", "metadatas", "distances"],
                )
                docs      = res.get("documents", [[]])[0]
                metas     = res.get("metadatas",  [[]])[0]
                distances = res.get("distances",  [[]])[0]
                for doc, meta, dist in zip(docs, metas, distances):
                    # ChromaDB cosine distance → similarity score (0-1, higher=better)
                    score = max(0.0, 1.0 - dist)
                    if score > 0.3:   # Only keep reasonably relevant results
                        results.append({
                            "text":       doc,
                            "type":       coll_name,
                            "score":      round(score, 3),
                            "metadata":   meta or {},
                        })
            except Exception as e:
                logger.debug(f"[RAG] retrieve error ({coll_name}): {e}")

        # Sort by relevance score, highest first
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k * 2]   # Cap total results

    def build_rag_context(self, query: str, max_chars: int = 3000) -> str:
        """
        Build a context string from retrieved memories for injection into prompts.
        """
        results = self.retrieve(query, top_k=6)
        if not results:
            return ""

        parts = ["[TOM's Relevant Memory & Knowledge]"]
        total = 0
        for r in results:
            entry = f"\n• [{r['type'].upper()} | relevance {r['score']:.0%}]\n  {r['text'][:400]}"
            if total + len(entry) > max_chars:
                break
            parts.append(entry)
            total += len(entry)

        return "\n".join(parts)

    # ── Ingest Files ─────────────────────────────────────────────────────────

    def ingest_file(self, filepath: str) -> Dict[str, Any]:
        """Read a file from disk and store it in RAG memory."""
        try:
            path = Path(filepath)
            if not path.exists():
                return {"status": "error", "message": f"File not found: {filepath}"}
            suffix = path.suffix.lower()
            if suffix in (".docx",):
                from docx import Document as DocxDoc
                doc = DocxDoc(str(path))
                content = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            elif suffix in (".pdf",):
                try:
                    import pdfplumber
                    with pdfplumber.open(str(path)) as pdf:
                        content = "\n".join(
                            page.extract_text() or "" for page in pdf.pages
                        )
                except ImportError:
                    return {"status": "error", "message": "pip install pdfplumber for PDF ingestion"}
            else:
                content = path.read_text(encoding="utf-8", errors="ignore")

            ok = self.store_document(path.name, content, doc_type=suffix.lstrip("."))
            if ok:
                return {"status": "success",
                        "message": f"Ingested {path.name} into TOM's brain ({len(content)} chars)"}
            return {"status": "error", "message": "Embedding failed — is Ollama running?"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def ingest_folder(self, folder_path: str,
                      extensions: Optional[List[str]] = None) -> Dict[str, Any]:
        """Ingest all readable files in a folder into RAG memory."""
        ext_filter = set(extensions or [".txt", ".md", ".py", ".html", ".css",
                                         ".js", ".json", ".docx", ".pdf", ".csv"])
        folder = Path(folder_path)
        if not folder.is_dir():
            return {"status": "error", "message": f"Not a directory: {folder_path}"}

        success, failed = [], []
        for fpath in folder.rglob("*"):
            if fpath.suffix.lower() in ext_filter and fpath.is_file():
                r = self.ingest_file(str(fpath))
                if r["status"] == "success":
                    success.append(fpath.name)
                else:
                    failed.append(f"{fpath.name}: {r['message']}")
        return {
            "status": "success",
            "message": f"Ingested {len(success)} files. Failed: {len(failed)}.",
            "ingested": success,
            "failed": failed,
        }

    # ── Stats ────────────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Return memory statistics."""
        if not self._available:
            return {"available": False, "message": "ChromaDB not installed"}
        return {
            "available": True,
            "conversations": self._conv_coll.count(),
            "knowledge_items": self._know_coll.count(),
            "document_chunks": self._doc_coll.count(),
            "learned_strategies": self._strat_coll.count(),
            "db_path": CHROMA_DIR,
            "embed_model": EMBED_MODEL,
        }

    def clear_collection(self, collection: str) -> Dict[str, Any]:
        """Clear a specific memory collection."""
        try:
            self._client.delete_collection(collection)
            # Re-create empty
            setattr(self, f"_{collection.split('_')[0]}_coll",
                    _get_or_create_collection(self._client, collection))
            return {"status": "success", "message": f"Cleared {collection}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


# ── Text Chunking ─────────────────────────────────────────────────────────────

def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks for embedding."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        # Try to break at a sentence boundary
        last_period = chunk.rfind(". ")
        if last_period > chunk_size // 2:
            chunk = chunk[:last_period + 1]
        chunks.append(chunk.strip())
        start += len(chunk) - overlap
    return [c for c in chunks if c]


# ── Module-level singleton ────────────────────────────────────────────────────

_rag_instance: Optional[RAGMemory] = None

def get_rag() -> RAGMemory:
    """Get the global RAGMemory singleton."""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGMemory()
    return _rag_instance
