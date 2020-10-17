import unittest
from log_parsing import *


d1 = [
    "foo killed bar with baz.",
    "foo killed bar with bizz.",
    "foo killed bar with haz.",
    "bar killed foo with haz.",
    "foo killed bar with haz."
    ]

d2 = ["foo, bar captured house for team #3 ",
      "foo captured house for team #2 ",
      "foo, bar captured hay stack for team #3 ",
      "foo bar, bar defended hay stack for team #2 "
      ]
d2a = [ObjectiveEvent({"foo", "bar"}, "house", "blue"),
       ObjectiveEvent({"foo"}, "house", "red"),
       ObjectiveEvent({"foo", "bar"}, "hay stack", "blue"),
       ObjectiveEvent({"foo bar", "bar"}, "hay stack", "red")
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


    def test_objective_line(self):
        names = {"foo", "bar", "foo bar"}
        for q, a in zip(d2, d2a):
            self.assertEqual(parse_objective_line(q, names), a)
 
        
        



if __name__ == '__main__':
    unittest.main()
