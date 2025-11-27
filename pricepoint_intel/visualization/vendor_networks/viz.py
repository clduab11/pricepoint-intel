"""Vendor network visualization implementation."""

from typing import Any

import networkx as nx
import plotly.graph_objects as go


class VendorNetworkViz:
    """Vendor network relationship visualization.

    Creates interactive network graphs showing supplier relationships.
    """

    def __init__(self) -> None:
        """Initialize the vendor network visualization."""
        pass

    def create_network_graph(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> go.Figure:
        """Create a network graph visualization.

        Args:
            nodes: List of node data dictionaries.
            edges: List of edge data dictionaries.

        Returns:
            Plotly figure object.
        """
        # Build NetworkX graph
        G = nx.DiGraph()

        for node in nodes:
            G.add_node(node["id"], **node)

        for edge in edges:
            G.add_edge(edge["source"], edge["target"], **edge)

        # Calculate layout
        pos = nx.spring_layout(G, k=2, iterations=50)

        # Create edge traces
        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        edge_trace = go.Scatter(
            x=edge_x,
            y=edge_y,
            line=dict(width=0.5, color="#888"),
            hoverinfo="none",
            mode="lines",
        )

        # Create node traces
        node_x = []
        node_y = []
        node_text = []
        node_color = []

        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_data = G.nodes[node]
            node_text.append(node_data.get("name", node))
            # Color by type
            node_type = node_data.get("type", "unknown")
            color_map = {
                "manufacturer": "#1f77b4",
                "distributor": "#ff7f0e",
                "retailer": "#2ca02c",
                "supplier": "#d62728",
            }
            node_color.append(color_map.get(node_type, "#9467bd"))

        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            hoverinfo="text",
            text=node_text,
            textposition="top center",
            marker=dict(
                showscale=False,
                color=node_color,
                size=20,
                line_width=2,
            ),
        )

        # Create figure
        fig = go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                title="Vendor Relationship Network",
                showlegend=False,
                hovermode="closest",
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            ),
        )

        return fig

    def create_hierarchy_chart(
        self,
        hierarchy_data: dict[str, Any],
    ) -> go.Figure:
        """Create a hierarchical visualization of vendor relationships.

        Args:
            hierarchy_data: Hierarchical vendor data.

        Returns:
            Plotly figure object.
        """
        # Create treemap
        labels = []
        parents = []
        values = []

        def traverse(node: dict, parent: str = "") -> None:
            name = node.get("name", "Unknown")
            labels.append(name)
            parents.append(parent)
            values.append(node.get("value", 1))

            for child in node.get("children", []):
                traverse(child, name)

        traverse(hierarchy_data)

        fig = go.Figure(
            go.Treemap(
                labels=labels,
                parents=parents,
                values=values,
                branchvalues="total",
            )
        )

        fig.update_layout(title="Vendor Hierarchy")

        return fig
