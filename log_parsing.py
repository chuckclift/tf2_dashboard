from typing import List, Dict, Tuple, Set, NamedTuple, Optional
import socket
from collections import defaultdict
import re
import a2s # type: ignore
import networkx as nx

server_re = r"^Connected to \d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}.:\d{1,5}$"
KillEvent = NamedTuple("KillEvent", [("killer", str),
                                     ("victim", str),
                                     ("weapon", str)])

ObjectiveEvent = NamedTuple("ObjectiveEvent", [("players", Set[str]),
                                               ("objective", str),
                                               ("team", str)])

def read_connections(lines: List[str]) -> Set[str]:
    """
    Reads the player event connection events from
    the log to get the usernames.
    """
    usernames = set()
    for line in lines:
        if line.strip().endswith("connected"):
            usernames.add(line.strip()[:-10])
    return usernames


def explained_points(lines:List[str], users:Set[str]) -> Dict[str, int]:
    """
    estimates the player points based on kills and capture/defense
    events in the game log.  This does not capture event points like
    assists, ubers, healing, or pushing the payload cart for 10 seconds.  

    https://wiki.teamfortress.com/wiki/Scoreboard
    """
    user_points: Dict[str, int] = defaultdict(lambda: 0)
    for line in lines:
        kill_event = parse_kill_line(line, users)
        if kill_event:
            user_points[kill_event.killer] += 1
            continue
        objective_event = parse_objective_line(line, users)
        if objective_event:
            for player in objective_event.players:
                user_points[player] += 1
    return user_points
                


def calculate_elo(killer_elo, victim_elo, k=30) -> Tuple[float, float]:
    """
    Calculates the elo when a player kills another
    """
    killer_expected_score = 1 / (1 + 10 ** ( (victim_elo - killer_elo) / 400))
    victim_expected_score = 1 / (1 + 10 ** ( (killer_elo - victim_elo) / 400))

    new_killer_elo = killer_elo + k * (1 - killer_expected_score)
    new_victim_elo = victim_elo + k * (0 - victim_expected_score)
    return (new_killer_elo, new_victim_elo)

def sort_descending(d: Dict) -> List[Tuple]:
    """
    Sorts a dictionary by its keys in a descending order
    """
    return sorted([(v, k) for k, v in d.items()], reverse=True)


def latest_game_lines(lines: List[str], user: str) -> List[str]:
    """
    gets the game lines for the most recent or currently running game.
    """
    game_lines: List[str] = []
    for l in lines:
        if f"{user} connected" == l.strip():
            game_lines = [l]
        else:
            game_lines.append(l)
    return game_lines

def get_killstreak(user: str, kill_events: List[KillEvent]) -> int:
    """
    returns the killstreak for the given user in the kill event list
    """
    streak_kills = 0
    for ke in kill_events[::-1]:
        if ke.killer == user:
            streak_kills += 1
        elif ke.victim == user:
            return streak_kills
    return streak_kills

def get_killstreaks(kill_events: List[KillEvent]) -> Dict[str, List[int]]:
    """
    Returns each killstreak 
    """
    killstreaks: Dict[str, List[int]]= defaultdict(lambda: [0])
    
    for ke in kill_events:
        killstreaks[ke.killer][-1] += 1
        killstreaks[ke.victim].append(0)
    return killstreaks


def get_teams(user: str, kill_events: List[KillEvent]):
    """
    gets the ally and enemy teams of the given user by viewing the kill_event
    list
    """
    g = nx.Graph()
    g.add_node(user)

    # older kill events will have higher weights so newer
    # events will be prioritized.  This is done because
    # players can change teams
    weights = range( (len(kill_events)-1) * 100, 0, -100)

    for w, ke in zip(weights, kill_events):
        g.add_edge(ke.killer, ke.victim, weight=w)


    allies = set()
    enemies = set()
    for n in g.nodes:
        try:
            _, path = nx.bidirectional_dijkstra(g, user, n)
            if len(path) == 1 or len(path) % 2 == 1:
                allies.add(n)
            elif len(path) % 2 == 0:
                enemies.add(n)
        except nx.NetworkXNoPath:
            pass
    return (allies, enemies)


def read_server_usernames(lines: List[str]) -> Set:
    """
    connects to the latest server and returns the users connected to it
    """
    latest_connection: str = [a for a in lines if re.match(server_re, a)][-1]
    server_str = latest_connection.split()[-1].split(":")
    server = (server_str[0], int(server_str[1]))

    names = set()
    try:
        names.update({p.name for p in a2s.players(server)})
    except socket.timeout:
        print("tf2 server connection timeout")
    return names

def parse_objective_line(line:str, names: Set[str]) -> Optional[ObjectiveEvent]:
    pat = r"^(?P<users>.*) (defended|captured) (?P<objective>.*) for team #(?P<team>[23])\s+$"
    teams = {"3": "blue", "2":"red"}
    match = re.search(pat, line)
    if not match:
        return None
    
    users = set()
    user_str = match.group("users")
    for _ in range(len(names) * len(names)):
        if not user_str:
            break
        
        for n in names:
            if user_str.startswith(n + ", "):
                users.add(n)
                user_str = user_str[len(n) + 2:]
            elif user_str == n:
                users.add(n)
                user_str = ""
                break

    return ObjectiveEvent(users, match.group("objective"), teams[match.group("team")])

def parse_kill_line(line: str, names) -> Optional[KillEvent]:
    """
    Parses the lines of a log.  If it is a valid kill event, it
    returns a kill event.  Otherwise, it returns None.
    """
    pat = r"(?P<users>.*) with (?P<weapon>\w+)\.( \(crit\))?\s*$"
    # line[:-7] removes the " (crit)" at the end of the line
    nocrit = line[:-7] if line.strip().endswith(" (crit)") else line
    if " killed " not in nocrit:
        return None
    if " with " not in nocrit:
        return None
    if not nocrit.strip().endswith("."):
        return None

    weapon = nocrit.split()[-1]
    weapon_index = line.rfind(" with ")
    user_line = line[:weapon_index]
    if len(user_line.split(" killed ")) == 2:
        killer, victim = user_line.split(" killed ")
        return KillEvent(killer, victim, weapon)


    potential_killers = [n for n in names if user_line.strip().startswith(n + " killed ")]
    potential_victims = [n for n in names if user_line.strip().endswith(" killed " + n)]

    for pk in potential_killers:
        for pv in potential_victims:
            if user_line == f"{pk} killed {pv}":
                return KillEvent(pk, pv, weapon)
    return None
