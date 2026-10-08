"""Use (previous location, current location) states to price turns correctly."""
from dijkstra_toolkit import Arc, dijkstra, make_graph, recover, verify_distances


def main() -> None:
    # S-A-X-T takes 3 travel units but the A-X-T turn costs 10 more.
    # S-B-X-T takes 5 units and avoids that turn.
    roads = [("S", "A", 1), ("A", "X", 1), ("S", "B", 2),
             ("B", "X", 2), ("X", "T", 1)]
    turns = {("A", "X", "T"): 10}
    states = [(None, "S")] + sorted({(u, v) for u, v, _ in roads})
    index = {state: i for i, state in enumerate(states)}
    arcs = []
    for previous, current in states:
        for tail, head, weight in roads:
            if tail == current:
                cost = weight + turns.get((previous, current, head), 0)
                arcs.append(Arc(len(arcs), index[previous, current],
                                index[current, head], cost))
    graph = make_graph(len(states), arcs, version="turn-state-v1", weight_unit="cost-unit")
    answer = dijkstra(graph, index[None, "S"])
    assert verify_distances(graph, answer)
    arrivals = [i for i, (_, current) in enumerate(states) if current == "T"]
    best = min(arrivals, key=lambda i: answer.distance[i])
    route = recover(answer, graph, best)
    assert route is not None and answer.distance[best] == 5
    locations = ["S"] + [states[e.head][1] for e in route]
    assert locations == ["S", "B", "X", "T"]
    print("Route:", " -> ".join(locations))
    print("Cost including turns:", answer.distance[best])
    print("A location alone would lose the incoming-road information.")


if __name__ == "__main__":
    main()
