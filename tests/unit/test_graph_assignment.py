import unittest

from common.graph import DirectedGraph, Edge
from traffic.assignment import assign_user_equilibrium


def make_graph():
    graph = DirectedGraph()
    graph.add_edge(Edge("ab", "a", "b", 1, 60, 100))
    graph.add_edge(Edge("bc", "b", "c", 1, 60, 100))
    graph.add_edge(Edge("ac", "a", "c", 3, 60, 100))
    return graph


class AssignmentTests(unittest.TestCase):
    def test_assignment_and_closure_are_deterministic(self):
        graph = make_graph()
        od = [("a", "c", 50)]
        baseline = assign_user_equilibrium(graph, od)
        closed = assign_user_equilibrium(graph, od, disabled={"bc"})
        self.assertGreater(baseline.volumes["ab"], 0)
        self.assertGreater(closed.volumes["ac"], baseline.volumes["ac"])
        self.assertEqual(closed.unreachable_demand, 0)
