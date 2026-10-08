"""Minimize latency after enforcing a per-edge capacity requirement."""
from dijkstra_toolkit import Arc, dijkstra, make_graph, recover, verify_route


def main() -> None:
    labels = ["S", "A", "B", "C", "D", "T"]
    # tail, head, latency_ms, capacity_units
    rows = [(0, 1, 4, 25), (1, 5, 5, 25), (0, 2, 3, 60),
            (2, 3, 3, 60), (3, 5, 5, 60), (0, 4, 7, 45), (4, 5, 6, 45)]
    required = 40
    allowed = [Arc(i, u, v, latency) for i, (u, v, latency, capacity)
               in enumerate(rows) if capacity >= required]
    graph = make_graph(6, allowed, version=f"capacity-min-{required}-v1",
                       weight_unit="milliseconds")
    result = dijkstra(graph, 0, 5)
    route = recover(result, graph, 5)
    assert route is not None and result.distance[5] == 11
    assert verify_route(graph, 0, 5, [e.edge_id for e in route], 11)
    print("Required capacity:", required)
    print("Route:", " -> ".join(labels[v] for v in [0] + [e.head for e in route]))
    print("Latency:", result.distance[5], "ms")
    print("The 9 ms S-A-T route is excluded because its capacity is only 25.")


if __name__ == "__main__":
    main()
