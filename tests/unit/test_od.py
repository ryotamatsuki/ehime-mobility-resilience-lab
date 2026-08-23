import unittest

from od.synthetic import InfeasibleConstraints, constrained_ipf, gravity_seed, ipf


class ODTests(unittest.TestCase):
    def test_ipf_preserves_margins_and_is_deterministic(self):
        origins = ["a", "b"]
        destinations = ["x", "y"]
        seed = gravity_seed(
            origins,
            destinations,
            [5, 3],
            [4, 4],
            {("a", "x"): 1, ("a", "y"): 2, ("b", "x"): 2, ("b", "y"): 1},
            beta=0.2,
        )
        first = ipf(origins, destinations, [5, 3], [4, 4], seed)
        second = ipf(origins, destinations, [5, 3], [4, 4], seed)
        self.assertEqual(first, second)
        for actual, expected in zip(
            [sum(first[(origin, destination)] for destination in destinations) for origin in origins],
            [5, 3],
            strict=True,
        ):
            self.assertAlmostEqual(actual, expected, places=8)
        for actual, expected in zip(
            [sum(first[(origin, destination)] for origin in origins) for destination in destinations],
            [4, 4],
            strict=True,
        ):
            self.assertAlmostEqual(actual, expected, places=8)

    def test_constrained_ipf_preserves_group_pair_totals(self):
        origins = ["a1", "a2", "b1"]
        destinations = ["a1", "a2", "b1"]
        origin_groups = {"a1": "A", "a2": "A", "b1": "B"}
        destination_groups = origin_groups.copy()
        targets = {("A", "A"): 3, ("A", "B"): 2, ("B", "A"): 2, ("B", "B"): 2}
        seed = {(origin, destination): 1.0 for origin in origins for destination in destinations}
        result = constrained_ipf(
            origins,
            destinations,
            [2, 3, 4],
            [2, 3, 4],
            origin_groups,
            destination_groups,
            targets,
            seed,
        )
        for pair, target in targets.items():
            actual = sum(
                value
                for (origin, destination), value in result.items()
                if origin_groups[origin] == pair[0] and destination_groups[destination] == pair[1]
            )
            self.assertLessEqual(abs(actual - target), 1e-9)

    def test_infeasible_od_raises_instead_of_silent_normalization(self):
        with self.assertRaises(InfeasibleConstraints):
            ipf(["a"], ["x"], [1], [2], {("a", "x"): 1})

    def test_target_length_mismatch_is_rejected(self):
        with self.assertRaises(InfeasibleConstraints):
            ipf(["a", "b"], ["x"], [1], [1], {("a", "x"): 1, ("b", "x"): 1})
