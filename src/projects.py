"""
Project / Drug Management Layer

A PV project represents one active drug under pharmacovigilance.
Multiple projects can run in parallel without interference because
each gets its own ChromaDB collection and vault subfolder.

Usage:
    from projects import load_project, list_projects, ProjectConfig

    proj = load_project("cefiderocol")
    hits = query_vault("Evans criteria", project=proj)
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

from config import BASE_DIR, VAULT_PATH, CHROMA_PATH, EMBED_MODEL, OLLAMA_BASE_URL, TOP_K

PROJECTS_FILE = BASE_DIR / "projects.json"


@dataclass
class ProjectConfig:
    drug_name: str                      # Primary drug under surveillance (e.g. "cefiderocol")
    display_name: str = ""              # Human-readable name for UI
    comparator: str = "meropenem"       # FAERS background comparator
    max_bg_records: int = 5000          # Cap on background FAERS records
    collection_name: str = ""           # ChromaDB collection (auto-derived if empty)
    vault_folder: str = ""              # Vault subfolder for this drug (auto-derived if empty)
    pubmed_terms: list[str] = field(default_factory=list)   # PubMed search queries
    active: bool = True

    def __post_init__(self):
        slug = self.drug_name.lower().replace(" ", "-")
        if not self.display_name:
            self.display_name = self.drug_name.title()
        if not self.collection_name:
            self.collection_name = f"pv_{slug}"
        if not self.vault_folder:
            self.vault_folder = f"Drugs/{self.drug_name.title()}"
        if not self.pubmed_terms:
            self.pubmed_terms = [
                f"{self.drug_name}[tiab] AND (adverse[tiab] OR safety[tiab] OR pharmacovigilance[tiab])",
                f"{self.drug_name}[tiab] AND (resistance[tiab] OR failure[tiab])",
            ]


# --- Persistence ---

def load_projects() -> dict[str, ProjectConfig]:
    """Load all projects from projects.json. Returns {} if file missing."""
    if not PROJECTS_FILE.exists():
        return {}
    data = json.loads(PROJECTS_FILE.read_text())
    return {k: ProjectConfig(**v) for k, v in data.items()}


def save_projects(projects: dict[str, ProjectConfig]) -> None:
    PROJECTS_FILE.write_text(json.dumps({k: asdict(v) for k, v in projects.items()}, indent=2))


def load_project(drug_name: str) -> ProjectConfig:
    """
    Load a project by drug name, or create a default config if it doesn't exist.
    The default config is not persisted — call save_project() to persist it.
    """
    projects = load_projects()
    key = drug_name.lower()
    return projects.get(key, ProjectConfig(drug_name=drug_name))


def save_project(project: ProjectConfig) -> None:
    projects = load_projects()
    projects[project.drug_name.lower()] = project
    save_projects(projects)


def list_projects() -> list[ProjectConfig]:
    return sorted(load_projects().values(), key=lambda p: p.drug_name)


# --- Shared collection name for Guidelines (drug-agnostic) ---
GUIDELINES_COLLECTION = "pv_vault"     # Ingested by vault_ingester — shared across all projects
