import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# Output directory — bind-mounted to ~/Desktop/pv-workbench-output/ on the host
OUTPUT_DIR = Path("/app/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Vault
VAULT_PATH = BASE_DIR / "vault"

# ChromaDB
CHROMA_PATH = BASE_DIR / "chroma_db"
COLLECTION_NAME = "pv_vault"

# Ollama
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
EMBED_MODEL = "nomic-embed-text"
REASON_MODEL = "gemma4:26b"    # Thinking Mode — regulatory Q&A, signal interpretation, MedDRA deliberation
DRAFT_MODEL = "gemma4:e4b"     # Prose generation — ICSR narratives, digests, summaries

# Chunking
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# Retrieval
TOP_K = 5
