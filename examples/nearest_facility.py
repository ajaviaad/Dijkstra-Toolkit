"""Find travel TO the closest facility on a directed network."""
from dijkstra_toolkit import (
    Arc, make_graph, multi_source_dijkstra, recover, reverse_graph,
    verify_distances, verify_route,
)


def main() -> None:
    # Vertex 0 is home; facilities 3 and 4 have different directed access costs.
    labels = ["Home", "Junction", "Bridge", "Clinic", "Hospital"]
    rows = [(0, 1, 2), (1, 3, 5), (0, 2, 1), (2, 4, 3),
            (3, 0, 1), (4, 0, 10)]
    graph = make_graph(5, [Arc(i, *row) for i, row in enumerate(rows)],
                       version="facilities-v1", weight_unit="minutes")
    reversed_graph = reverse_graph(graph)
    result = multi_source_dijkstra(reversed_graph, [3, 4])
    assert verify_distances(reversed_graph, result)
    backward_path = recover(result, reversed_graph, 0)
    assert backward_path is not None and backward_path
    destination = backward_path[0].tail
    original_ids = [arc.edge_id for arc in reversed(backward_path)]
    assert verify_route(graph, 0, destination, original_ids, result.distance[0])
    assert destination == 4 and result.distance[0] == 4
    print("Closest facility from Home:", labels[destination])
    print("Travel time:", result.distance[0], "minutes")
    print("Original edge IDs:", original_ids)
    # Searching outward from facilities answers a different question.
    outward = multi_source_dijkstra(graph, [3, 4])
    assert outward.distance[0] == 1
    print("Best facility-to-Home time:", outward.distance[0], "minute")


if __name__ == "__main__":
    main()
