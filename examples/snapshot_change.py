"""An unused edge becomes cheaper: an old feasible route is no longer optimal."""
from dijkstra_toolkit import Arc, dijkstra, make_graph, recover, verify_route


def main() -> None:
    # IDs: S=0, A=1, T=2, X=3, Y=4.
    old_arcs = [Arc(0, 0, 1, 5), Arc(1, 1, 2, 5), Arc(2, 0, 3, 4),
                Arc(3, 3, 4, 20), Arc(4, 4, 2, 4)]
    old = make_graph(5, old_arcs, version="before")
    cached = dijkstra(old, 0, 2)
    old_route = recover(cached, old, 2)
    assert old_route is not None and cached.distance[2] == 10
    new_arcs = [Arc(e.edge_id, e.tail, e.head, 1 if e.edge_id == 3 else e.weight)
                for e in old_arcs]
    current = make_graph(5, new_arcs, version="after")
    try:
        recover(cached, current, 2)
    except ValueError:
        print("Recovery correctly rejected an old result on a new snapshot.")
    else:
        raise AssertionError("Snapshot binding failed")
    # Without claiming old snapshot identity, the old edge sequence is feasible.
    assert verify_route(current, 0, 2, [e.edge_id for e in old_route], 10)
    fresh = dijkstra(current, 0, 2)
    assert fresh.distance[2] == 9
    print("Old route remains feasible at cost 10; the new optimum is 9.")
    print("An edge outside the old route changed, so route-membership invalidation misses it.")


if __name__ == "__main__":
    main()
