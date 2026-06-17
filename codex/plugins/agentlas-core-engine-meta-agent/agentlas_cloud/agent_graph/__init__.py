"""Agent Ontology (AO) runtime package.

Loads canonical AO JSONL views, validates grammar/axioms, runs lightweight
graph queries, and migrates legacy .agentlas files into AO materialized views.
"""

from __future__ import annotations

from .loader import AGENT_ONTOLOGY_DIR, load_grammar, load_graph
from .migrate import migrate_ontology, diff_ontology
from .query import describe_graph, execute_query, is_blocked, plan_path, reachable, who_consumes, who_produces
from .validator import validate_graph
from .validator import evaluate_requirements, explain_edge_gate, edge_is_blocked
from .a2a import WELL_KNOWN_PATH, align_capability, export_agent_card, import_agent_card

__all__ = [
    "AGENT_ONTOLOGY_DIR",
    "WELL_KNOWN_PATH",
    "align_capability",
    "export_agent_card",
    "import_agent_card",
    "diff_ontology",
    "describe_graph",
    "execute_query",
    "is_blocked",
    "load_grammar",
    "load_graph",
    "migrate_ontology",
    "plan_path",
    "reachable",
    "validate_graph",
    "evaluate_requirements",
    "explain_edge_gate",
    "edge_is_blocked",
    "who_consumes",
    "who_produces",
]
