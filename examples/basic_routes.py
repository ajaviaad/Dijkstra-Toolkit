"""Full routes, independent verification, and first-hop forwarding on A–G."""
from pathlib import Path

from dijkstra_toolkit import dijkstra, recover, verify_distances, verify_route
from dijkstra_toolkit.io import load_graph


def main() -> None:
    graph = load_graph(Path(__file__).resolve().parents[1] / "data/a-g.json")
    labels = "ABCDEFG"
    result = dijkstra(graph, 0)
    assert verify_distances(graph, result)
    assert result.distance == (0, 2, 4, 4, 5, 7, 7)
    print("Destination | Cost | First hop | Route")
    for target in range(graph.vertex_count):
        route = recover(result, graph, target)
        assert route is not None
        assert verify_route(graph, 0, target, [e.edge_id for e in route],
                            result.distance[target], graph_digest=result.graph_digest)
        vertices = [0] + [edge.head for edge in route]
        first_hop = labels[route[0].head] if route else "-"
        print(f"{labels[target]:11} | {result.distance[target]:4} | {first_hop:9} | "
              + " -> ".join(labels[v] for v in vertices))


if __name__ == "__main__":
    main()
