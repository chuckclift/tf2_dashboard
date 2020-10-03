import time
from typing import List, Dict, Tuple, Set, NamedTuple, Optional
import re
import threading
import socket
import tkinter as tk
from collections import defaultdict
import sqlite3
from PIL import ImageTk, Image # type: ignore

import a2s # type: ignore


KillEvent = NamedTuple("KillEvent", [("killer", str),
                                     ("victim", str),
                                     ("weapon", str)])


fpath = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Team Fortress 2\\tf\\logs.txt"
server_re = r"^Connected to \d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}.:\d{1,5}$"
class_icons = {"demoman", "spy", "medic", "soldier", "heavyweapons", "sniper",
               "pyro", "scout", "many", "engineer"}

conn = sqlite3.connect("tf2_weapons.db")
cur = conn.cursor()
q: str = "select name, tf2_class, damage_type from weapon"
weapon_class = {}
weapon_dmg = {}
for name, tf2_class, damage_type in cur.execute(q):
    weapon_class[name] = tf2_class
    weapon_dmg[name] = damage_type
conn.close()

master = tk.Tk()
master.title("TF2 Dashboard")
tk_kills = tk.StringVar()
tk_deaths = tk.StringVar()
tk_kd = tk.StringVar()
tk_streak = tk.StringVar()
tk_elo = tk.StringVar()

# top row 
tk.Label(master, text="stats", width=10, anchor="e").grid(row=1, column=1, sticky=tk.E)
tk.Label(master, text="victims", width=15, anchor="e").grid(row=1, column=2)
tk.Label(master, text="rivals", width=15, anchor="e").grid(row=1, column=3, sticky=tk.E)
tk.Label(master, text="", width=3, anchor="e").grid(row=1, column=4, sticky=tk.E)
tk.Label(master, text="classes", width=15, anchor="e").grid(row=1, column=5, sticky=tk.E)
tk.Label(master, text="dmg type  ", width=15, anchor="e").grid(row=1, column=6, sticky=tk.E)

tk_ize = lambda c: ImageTk.PhotoImage(Image.open(f"tf2_icons/{c}.png").resize((16,16)))
class_tk_imgs = {cn: tk_ize(cn) for cn in class_icons}


tk.Label(master, textvariable=tk_kills).grid(row=2, column=1, sticky=tk.E)
tk.Label(master, textvariable=tk_deaths).grid(row=3, column=1, sticky=tk.E)
tk.Label(master, textvariable=tk_kd).grid(row=4, column=1, sticky=tk.E)
tk.Label(master, textvariable=tk_streak).grid(row=5, column=1, sticky=tk.E)
tk.Label(master, textvariable=tk_elo).grid(row=5, column=1, sticky=tk.E)

victim_vars = [tk.StringVar() for _ in range(5)]
rival_vars = [tk.StringVar() for _ in range(5)]
rival_class_vars = [tk.StringVar() for _ in range(5)]
rival_dmg_type_vars = [tk.StringVar() for _ in range(5)]

rival_class_icons = [tk.Label(master ) for i in range(2, 7)]
for i, r in zip(range(2, 7), rival_class_icons):
    r.grid(row=i, column=4, sticky=tk.W)

for i in range(2, 7):
    tk.Label(master, textvariable=victim_vars[i-2]).grid(row=i, column=2, sticky=tk.E)
    tk.Label(master, textvariable=rival_vars[i-2]).grid(row=i, column=3, sticky=tk.E)    
    tk.Label(master, textvariable=rival_class_vars[i-2]).grid(row=i, column=5, sticky=tk.E)
    tk.Label(master, textvariable=rival_dmg_type_vars[i-2]).grid(row=i, column=6, sticky=tk.E)

def calculate_elo(killer_elo, victim_elo, k=30) -> Tuple[float, float]:
    killer_expected_score = 1 / (1 + 10 ** ( (victim_elo - killer_elo) / 400))
    victim_expected_score = 1 / (1 + 10 ** ( (killer_elo - victim_elo) / 400))

    new_killer_elo = killer_elo + k * (1 - killer_expected_score)
    new_victim_elo = victim_elo + k * (0 - victim_expected_score)
    return (new_killer_elo, new_victim_elo)

def sort_descending(d: Dict) -> List[Tuple]:
    return sorted([(v, k) for k, v in d.items()], reverse=True)


def latest_game_lines(lines: List[str], user: str) -> List[str]:
    game_lines: List[str] = []
    for l in lines:
        if f"{user} connected" == l.strip():
            game_lines = [l]
        else:
            game_lines.append(l)
    return game_lines


def read_connections(lines: List[str]) -> Set[str]:
    usernames = set()
    for line in lines:
        if line.strip().endswith("connected"):
            usernames.add(line.strip()[:-10])
    return usernames

def parse_kill_line(line: str, names) -> Optional[KillEvent]:
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

def read_server_usernames(lines: List[str]) -> Set:
    latest_connection: str = [a for a in lines if re.match(server_re, a)][-1]
    server_str = latest_connection.split()[-1].split(":")
    server = (server_str[0], int(server_str[1]))

    names = set()
    try:
        names.update({p.name for p in a2s.players(server)})
    except socket.timeout:
        print("tf2 server connection timeout")
    return names

def get_killstreak(user: str, kill_events: List[KillEvent]) -> int:
    streak_kills = 0
    for ke in kill_events[::-1]:
        if ke.killer == user:
            streak_kills += 1
        elif ke.victim == user:
            streak_kills = 0
    return streak_kills
    
def render() -> None:
    user = ""
    with open("tf2_user.txt", encoding="utf-8") as f:
        user = f.read().strip()

    gamer_names = set()
    with open(fpath, encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    gamer_names.update(read_connections(lines[-1000:]))

    while True:
        victims: Dict = defaultdict(lambda: 0)
        rivals: Dict = defaultdict(lambda: 0)
        class_deaths: Dict = defaultdict(lambda: 0)
        dmg_type_deaths: Dict = defaultdict(lambda: 0)
        player_elo: Dict[str, float] = defaultdict(lambda: 1600.0)
        player_class: Dict = {}


        lines = []
        with open(fpath, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        game_lines = latest_game_lines(lines, user)

        opt_kill_events = [parse_kill_line(l, gamer_names) for l in game_lines]
        kill_events: List[KillEvent] = [a for a in opt_kill_events if a]


        gamer_names.update(read_server_usernames(lines))
        gamer_names.update(read_connections(game_lines))

        
        kills = sum(1 for k, _,_ in kill_events if k == user)
        deaths: int = len([line for line in game_lines
                          if f"killed {user}" in line or line == f"{user} died."])

        for killer, victim, weapon in kill_events:
            (k_elo, v_elo) = calculate_elo(player_elo[killer], player_elo[victim])
            player_elo[killer] = k_elo
            player_elo[victim] = v_elo
            
            if weapon_class.get(weapon) not in {None, "many"}:
                player_class[killer] = weapon_class.get(weapon)
                
            if killer == user:
                victims[victim] += 1
            elif victim == user:
                rivals[killer] += 1
                class_deaths[weapon_class.get(weapon, "many")] += 1
                dmg_type_deaths[weapon_dmg.get(weapon, "melee")] += 1

        tk_kills.set(f"kills: {kills}")
        tk_deaths.set(f"deaths: {deaths}")
        kd_ratio = kills / deaths if deaths else 0
        tk_kd.set(f"k/d: {kd_ratio:.2f}")
        tk_streak.set(f"streak: {get_killstreak(user, kill_events)}")
        tk_elo.set(f"elo: {player_elo[user]:.1f}")
        
        
        # sorting columns into descending order
        for (vkills, vname), vv in zip(sort_descending(victims), victim_vars ):
            vv.set(f"{vname}: {vkills}")

        for (rdeaths, rname), rv, rci in zip(sort_descending(rivals),
                                             rival_vars,
                                             rival_class_icons):
            rv.set(f"{rname} ({player_elo[rname]:.1f} ) : {rdeaths}")
            rci.configure(image=class_tk_imgs[player_class.get(rname, "many")])

        for (cdeaths, cname), rcv in zip(sort_descending(class_deaths), rival_class_vars):
            rcv.set(f"{cname}: {cdeaths}")
            
        for (dtdeaths, dtname), rdtv in zip(sort_descending(dmg_type_deaths), rival_dmg_type_vars):
            rdtv.set(f"{dtname}: {dtdeaths}   ")
        time.sleep(3)

x = threading.Thread(target=render, daemon=True)
x.start()
master.mainloop()
