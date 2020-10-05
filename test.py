import unittest
from log_parsing import *


d1 = [
    "foo killed bar with baz.",
    "foo killed bar with bizz.",
    "foo killed bar with haz.",
    "bar killed foo with haz.",
    "foo killed bar with haz."
    ]

class TestStringMethods(unittest.TestCase):

    def test_upper(self):
        names = {"foo", "bar"}
        kill_events = [parse_kill_line(l, names) for l in d1[:3]]
        self.assertEqual(3, get_killstreak("foo", kill_events))
        self.assertEqual(0, get_killstreak("bar", kill_events))

        kill_events = [parse_kill_line(l, names) for l in d1]
        self.assertEqual(1, get_killstreak("foo", kill_events))
        self.assertEqual(0, get_killstreak("bar", kill_events))



if __name__ == '__main__':
    unittest.main()
