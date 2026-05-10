"""Stable id helpers."""

from req_tracker.debug.hash import stable_hash


def node_id(project_key: str, external_id: str) -> str:
    """Create a stable node id."""
    return f"node_{project_key}_{external_id.replace('-', '_')}"


def edge_id(source_node_id: str, relation: str, target_node_id: str) -> str:
    """Create a stable edge id."""
    return f"edge_{stable_hash({'s': source_node_id, 'r': relation, 't': target_node_id})[:16]}"

