"""Relationship mapping for supply chain network analysis."""

from dataclasses import dataclass
from typing import Any

import networkx as nx


@dataclass
class SupplyChainNode:
    """Node in the supply chain network."""

    entity_id: str
    entity_name: str
    entity_type: str  # "manufacturer", "distributor", "retailer", "supplier"
    location: str | None
    attributes: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "entity_type": self.entity_type,
            "location": self.location,
            "attributes": self.attributes,
        }


@dataclass
class SupplyChainEdge:
    """Edge in the supply chain network."""

    source_id: str
    target_id: str
    relationship_type: str
    confidence: float
    source_data: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "confidence": self.confidence,
            "source_data": self.source_data,
        }


class RelationshipMapper:
    """Supply chain relationship mapper.

    Builds and analyzes supply chain network graphs
    from various data sources.
    """

    def __init__(self) -> None:
        """Initialize the relationship mapper."""
        self._graph = nx.DiGraph()

    def add_node(self, node: SupplyChainNode) -> None:
        """Add a node to the supply chain graph.

        Args:
            node: Supply chain node to add.
        """
        self._graph.add_node(
            node.entity_id,
            name=node.entity_name,
            type=node.entity_type,
            location=node.location,
            **node.attributes,
        )

    def add_edge(self, edge: SupplyChainEdge) -> None:
        """Add an edge to the supply chain graph.

        Args:
            edge: Supply chain edge to add.
        """
        self._graph.add_edge(
            edge.source_id,
            edge.target_id,
            relationship=edge.relationship_type,
            confidence=edge.confidence,
            source=edge.source_data,
        )

    def get_suppliers(self, entity_id: str) -> list[dict[str, Any]]:
        """Get suppliers for an entity.

        Args:
            entity_id: Entity identifier.

        Returns:
            List of supplier data dictionaries.
        """
        if entity_id not in self._graph:
            return []

        suppliers = []
        for pred in self._graph.predecessors(entity_id):
            edge_data = self._graph.edges[pred, entity_id]
            node_data = self._graph.nodes[pred]
            suppliers.append({
                "entity_id": pred,
                "entity_name": node_data.get("name", "Unknown"),
                "entity_type": node_data.get("type", "Unknown"),
                "relationship": edge_data.get("relationship", "Unknown"),
                "confidence": edge_data.get("confidence", 0.0),
            })

        return suppliers

    def get_customers(self, entity_id: str) -> list[dict[str, Any]]:
        """Get customers for an entity.

        Args:
            entity_id: Entity identifier.

        Returns:
            List of customer data dictionaries.
        """
        if entity_id not in self._graph:
            return []

        customers = []
        for succ in self._graph.successors(entity_id):
            edge_data = self._graph.edges[entity_id, succ]
            node_data = self._graph.nodes[succ]
            customers.append({
                "entity_id": succ,
                "entity_name": node_data.get("name", "Unknown"),
                "entity_type": node_data.get("type", "Unknown"),
                "relationship": edge_data.get("relationship", "Unknown"),
                "confidence": edge_data.get("confidence", 0.0),
            })

        return customers

    def find_path(
        self,
        source_id: str,
        target_id: str,
    ) -> list[str] | None:
        """Find supply chain path between two entities.

        Args:
            source_id: Source entity identifier.
            target_id: Target entity identifier.

        Returns:
            List of entity IDs in the path, or None if no path exists.
        """
        try:
            return nx.shortest_path(self._graph, source_id, target_id)
        except nx.NetworkXNoPath:
            return None

    def get_network_stats(self) -> dict[str, Any]:
        """Get statistics about the supply chain network.

        Returns:
            Dictionary of network statistics.
        """
        return {
            "node_count": self._graph.number_of_nodes(),
            "edge_count": self._graph.number_of_edges(),
            "density": nx.density(self._graph) if self._graph.number_of_nodes() > 1 else 0,
            "is_connected": nx.is_weakly_connected(self._graph)
            if self._graph.number_of_nodes() > 0
            else False,
        }

    def export_graph(self) -> dict[str, Any]:
        """Export the graph as a dictionary.

        Returns:
            Dictionary representation of the graph.
        """
        nodes = []
        for node_id, data in self._graph.nodes(data=True):
            nodes.append({"id": node_id, **data})

        edges = []
        for source, target, data in self._graph.edges(data=True):
            edges.append({"source": source, "target": target, **data})

        return {"nodes": nodes, "edges": edges}
