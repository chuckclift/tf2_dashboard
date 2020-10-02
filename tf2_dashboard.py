import time
from typing import List, Dict, Tuple, Set
import re
import threading
import socket
import tkinter as tk
from collections import defaultdict
import sqlite3
from PIL import ImageTk, Image

import a2s

fpath = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Team Fortress 2\\tf\\logs.txt"
server_re = r"^Connected to \d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}.:\d{1,5}$"

def log_unknown_weapon(weapon):
    with open("unknown_tf2_weapon.txt", "a", encoding="utf-8") as f:
        f.write(f"{weapon}\n")

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

# top rowp
tk.Label(master, text="stats", width=10, anchor="e").grid(row=1, column=1, sticky=tk.E)
tk.Label(master, text="victims", width=15, anchor="e").grid(row=1, column=2)
tk.Label(master, text="rivals", width=15, anchor="e").grid(row=1, column=3, sticky=tk.E)
tk.Label(master, text="", width=3, anchor="e").grid(row=1, column=4, sticky=tk.E)
tk.Label(master, text="weapons", width=15, anchor="e").grid(row=1, column=5, sticky=tk.E)
tk.Label(master, text="classes", width=15, anchor="e").grid(row=1, column=6, sticky=tk.E)
tk.Label(master, text="dmg type  ", width=15, anchor="e").grid(row=1, column=7, sticky=tk.E)

tk_ize = lambda c: ImageTk.PhotoImage(Image.open(f"tf2_icons/{c}.png").resize((16,16)))
class_tk_imgs = {cn: tk_ize(cn) for cn in class_icons}


tk.Label(master, textvariable=tk_kills).grid(row=2, column=1, sticky=tk.E)
tk.Label(master, textvariable=tk_deaths).grid(row=3, column=1, sticky=tk.E)
tk.Label(master, textvariable=tk_kd).grid(row=4, column=1, sticky=tk.E)
tk.Label(master, textvariable=tk_streak).grid(row=5, column=1, sticky=tk.E)

victim_vars = [tk.StringVar() for _ in range(5)]
rival_vars = [tk.StringVar() for _ in range(5)]
rival_weapon_vars = [tk.StringVar() for _ in range(5)]
rival_class_vars = [tk.StringVar() for _ in range(5)]
rival_dmg_type_vars = [tk.StringVar() for _ in range(5)]

rival_class_icons = [tk.Label(master ) for i in range(2, 7)]
for i, r in zip(range(2, 7), rival_class_icons):
    r.grid(row=i, column=4, sticky=tk.W)
# [r.grid(row=i, column=4, sticky=tk.W) for i, r in zip(range(2, 7), rival_class_icons)]



for i in range(2, 7):
    tk.Label(master, textvariable=victim_vars[i-2]).grid(row=i, column=2, sticky=tk.E)
    tk.Label(master, textvariable=rival_vars[i-2]).grid(row=i, column=3, sticky=tk.E)    
    tk.Label(master, textvariable=rival_weapon_vars[i-2] ).grid(row=i, column=5, sticky=tk.E)
    tk.Label(master, textvariable=rival_class_vars[i-2]).grid(row=i, column=6, sticky=tk.E)
    tk.Label(master, textvariable=rival_dmg_type_vars[i-2]).grid(row=i, column=7, sticky=tk.E)

def sort_descending(d):
    return sorted([ (v, k) for k, v in d.items()], reverse=True)


def latest_game_lines(lines: List[str], user: str) -> List[str]:
    game_lines: List[str] = []
    for l in lines:
        if f"{user} connected" == l.strip(): # re.match(server_re, l):
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

def parse_kill_line(line: str, names) -> Tuple:
    nocrit = line[:-7] if line.strip().endswith(" (crit)") else line
    if " killed " not in nocrit:
        return ()
    if " with " not in nocrit:
        return ()
    if not nocrit.strip().endswith("."):
        return ()

    weapon = nocrit.split()[-1]
    weapon_index = line.rfind(" with ")
    user_line = line[:weapon_index]
    if len(user_line.split(" killed ")) == 2:
        killer, victim = user_line.split(" killed ")
        return (killer, victim, weapon)


    potential_killers = [n for n in names if user_line.strip().startswith(n + " killed ")]
    potential_victims = [n for n in names if user_line.strip().endswith(" killed " + n)]

    for pk in potential_killers:
        for pv in potential_victims:
            if user_line == f"{pk} killed {pv}":
                return (pk, pv, weapon)

    
    return ()

def render() -> None:
    user = ""
    with open("tf2_user.txt", encoding="utf-8") as f:
        user = f.read().strip()

    kills = 0
    streak_kills = 0
    # deaths = 0
    gamer_names = set()
    with open(fpath, encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    gamer_names.update(read_connections(lines[-1000:]))

    weapon_deaths: Dict = defaultdict(lambda: 0)
    victims: Dict = defaultdict(lambda: 0)
    rivals: Dict = defaultdict(lambda: 0)
    class_deaths: Dict = defaultdict(lambda: 0)
    dmg_type_deaths: Dict = defaultdict(lambda: 0)
    player_class: Dict = {}

    server = ("", 0)
    while True:
        time.sleep(3)


        lines = []
        with open(fpath, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        game_lines = latest_game_lines(lines, user)



        latest_connection = [a for a in lines if re.match(server_re, a)][-1]
        server_str = latest_connection.split()[-1].split(":")
        server = (server_str[0], int(server_str[1]))
        kill_events = [parse_kill_line(l, gamer_names) for l in game_lines]
        try:
            gamer_names.update({p.name for p in a2s.players(server)})
        except socket.timeout:
            print("tf2 server connection timeout") 
            
        gamer_names.update(read_connections(game_lines))
        kill_events = [a for a in kill_events if a]
        kills = sum(1 for k, _,_ in kill_events if k == user)
        deaths: int = len([line for line in game_lines
                          if f"killed {user}" in line or line == f"{user} died."])

        streak_kills = 0
        for killer, victim, weapon in kill_events[::-1]:
            if killer == user:
                streak_kills += 1
            elif victim == user:
                streak_kills = 0

        with open(fpath, encoding="utf-8", errors="ignore") as f:
            for l in f:

                    
                if l.startswith(f"{user} killed"):
                    victim_start = len(f"{user} killed")
                    victim_end = l.rfind("with ")
            
                    victim = l[victim_start:victim_end]
                    victim = victim if len(victim) < 15 else victim[:15]
                    victims[victim] += 1
                elif f"killed {user}" in l:
                    weapon = l.split()[-1]
                    if "(crit)" in weapon:
                        weapon = l.split()[-2]

                    rival = l.split("killed")[0]
                    rival = rival[:15] if len(rival) > 15 else rival
                    rivals[rival] += 1

                    if weapon_class.get(weapon) not in {None, "many"}:
                        player_class[rival] = weapon_class.get(weapon)

                    weapon_deaths[weapon] += 1
                    if weapon not in weapon_class:
                        log_unknown_weapon(weapon)
                    else:
                        class_deaths[weapon_class[weapon]] += 1
                        dmg_type_deaths[weapon_dmg[weapon]] += 1
                elif l.endswith(f"{user} died.") or l.endswith(f"{user} suicided"):
                    weapon = l.split()[-1]
                    if "(crit)" in weapon:
                        weapon = l.split()[-2]

                    weapon_deaths[weapon] += 1
                elif f"{user} connected" == l.strip():
                    weapon_deaths = defaultdict(lambda: 0)
                    victims = defaultdict(lambda: 0)
                    rivals = defaultdict(lambda: 0)
                    class_deaths = defaultdict(lambda: 0)
                    dmg_type_deaths = defaultdict(lambda: 0)
                    player_class = {}

        tk_kills.set(f"kills: {kills}")
        tk_deaths.set(f"deaths: {deaths}")
        kd_ratio = kills / deaths if deaths else 0
        tk_kd.set(f"k/d: {kd_ratio:.2f}")
        tk_streak.set(f"streak: {streak_kills}")
        
        # sorting columns into descending order
        for (vkills, vname), vv in zip(sort_descending(victims), victim_vars ):
            vv.set(f"{vname}: {vkills}")

        for (rdeaths, rname), rv, rci in zip(sort_descending(rivals), rival_vars, rival_class_icons):
            rv.set(f"{rname} : {rdeaths}")              # {ci(rname)}
            rci.configure(image=class_tk_imgs[player_class.get(rname, "many")])

        for (wdeaths, wname), wv in zip(sort_descending(weapon_deaths), rival_weapon_vars):
            wv.set(f"{wname}: {wdeaths}")

        for (cdeaths, cname), rcv in zip(sort_descending(class_deaths), rival_class_vars):
            rcv.set(f"{cname}: {cdeaths}")
            
        for (dtdeaths, dtname), rdtv in zip(sort_descending(dmg_type_deaths), rival_dmg_type_vars):
            rdtv.set(f"{dtname}: {dtdeaths}   ")




 
x = threading.Thread(target=render, daemon=True)
x.start()


master.mainloop()
