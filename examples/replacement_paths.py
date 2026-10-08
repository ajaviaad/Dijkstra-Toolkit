"""Recompute routes when each edge on a critical corridor closes."""
from dijkstra_toolkit import Arc, dijkstra, make_graph, recover, verify_route


def main() -> None:
    labels = ["S", "A", "B", "T", "C", "D"]
    rows = [(0, 1, 2), (1, 2, 2), (2, 3, 2), (0, 4, 3),
            (4, 2, 2), (1, 5, 2), (5, 3, 3), (4, 5, 2)]
    arcs = [Arc(i, *row) for i, row in enumerate(rows)]
    graph = make_graph(6, arcs, version="corridor-v1")
    base = dijkstra(graph, 0, 3)
    corridor = recover(base, graph, 3)
    assert corridor is not None and base.distance[3] == 6
    print("Baseline cost:", base.distance[3])
    for closed in corridor:
        updated = make_graph(6, [e for e in arcs if e.edge_id != closed.edge_id],
                             version=f"closed-{closed.edge_id}")
        answer = dijkstra(updated, 0, 3)
        route = recover(answer, updated, 3)
        assert route is not None and answer.distance[3] == 7
        assert verify_route(updated, 0, 3, [e.edge_id for e in route], 7)
        path = " -> ".join(labels[v] for v in [0] + [e.head for e in route])
        print(f"Close {labels[closed.tail]}->{labels[closed.head]}: {path}; cost 7")
    print("Each closure uses full recomputation on a new snapshot.")


if __name__ == "__main__":
    main()
