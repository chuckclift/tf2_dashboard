"""
A gui dashboard that reads the Team Fortress 2 log and shows stats
about the game
"""


import time
from typing import List, Dict 
from statistics import mean
import threading
import tkinter as tk
from collections import defaultdict
import sqlite3
from PIL import ImageTk, Image # type: ignore
from log_parsing import * #pylint: disable=unused-import,unused-wildcard-import

fpath = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Team Fortress 2\\tf\\logs.txt"

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


labels = [ [tk.Label(master, anchor="e") for column in range(6)]
           for row in range(23)]
headings = {
    (0,0): "Allies",
    (0,3): "Enemies",
    (1,0): "Name",
    (1, 1): "Elo",
    (1, 3): "Name",
    (1, 4): "Elo",
    (9, 0): "Team Kills",
    (9, 3): "Team Kills",
    (10, 0): "Dmg Type",
    (10, 3): "Dmg Type",
    (17, 0): "Player Stats",
    (17, 3): "Rivals (kills)",
    (17, 4): "Elo",
    (18, 0): "Kills:",
    (19, 0): "Deaths",
    (20, 0): "K/D",
    (21, 0): "Streak",
    (22, 0): "Elo"
    }



tk_kills = tk.IntVar()
tk_deaths = tk.IntVar()
tk_kd = tk.StringVar()
tk_streak = tk.StringVar()
tk_elo = tk.StringVar()
tk_ally_kills = tk.IntVar()
tk_enemy_kills = tk.IntVar()

labels[9][1].configure(textvariable=tk_ally_kills)
labels[9][4].configure(textvariable=tk_enemy_kills)

labels[18][1].configure(textvariable=tk_kills)
labels[19][1].configure(textvariable=tk_deaths)
labels[20][1].configure(textvariable=tk_kd)
labels[21][1].configure(textvariable=tk_streak)
labels[22][1].configure(textvariable=tk_elo)

rival_vars = [tk.StringVar() for _ in range(4)]
rival_elo_vars = [tk.StringVar() for _ in range(4)]
rival_class_icons = []

ally_labels = [labels[row][0] for row in range(2, 8)]
ally_elo_labels = [labels[row][1] for row in range(2, 8)]
ally_class_labels = [labels[row][2] for row in range(2, 8)]


for row, var, elo_var in zip(range(18, 22), rival_vars, rival_elo_vars ):
    labels[row][3].configure(textvariable=var)
    labels[row][4].configure(textvariable=elo_var)
    rival_class_icons.append(labels[row][5])
  


for row in range(23):
    for column in range(6):
        labels[row][column].grid(row=row, column=column,
                                 sticky=tk.W if column in {2, 5} else tk.E)
        if headings.get( (row, column)):
            labels[row][column].configure(text=headings[(row, column)],
                                          font=('Helvetica', 12, 'bold'))

tk_ize = lambda c: ImageTk.PhotoImage(Image.open(f"tf2_icons/{c}.png").resize((16,16)))
class_tk_imgs = {cn: tk_ize(cn) for cn in class_icons}


def update_avg_team_elo(cells, allies, enemies, player_elo):
    if allies and enemies:
        ally_avg_elo = int(mean(player_elo.get(a) for a in allies))
        enemy_avg_elo = int(mean(player_elo.get(a) for a in enemies))
    else:
        ally_avg_elo = 1600
        enemy_avg_elo = 1600

    cells[0].configure(text="Team Elo", font=('Helvetica', 12, 'bold'))
    cells[1].configure(text=ally_avg_elo)
    cells[3].configure(text="Team Elo", font=('Helvetica', 12, 'bold'))
    cells[4].configure(text=enemy_avg_elo)
    if ally_avg_elo > enemy_avg_elo:
        cells[1].configure(fg="green")
        cells[4].configure(fg="red")
    elif ally_avg_elo < enemy_avg_elo:
        cells[1].configure(fg="red")
        cells[4].configure(fg="green")

# ^(.*)(defended|captured).*for team #([23])$ use for extra info, game state, and spawn info 

def render() -> None:
    """
    Updates the stats in the tkinter gui
    """
    user = ""
    with open("tf2_user.txt", encoding="utf-8") as f:
        user = f.read().strip()

    gamer_names = set()
    with open(fpath, encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    gamer_names.update(read_connections(lines[-1000:]))

    while True:
        player_elo: Dict[str, float] = defaultdict(lambda: 1600.0)
        rivals: Dict = defaultdict(lambda: 0)
        class_deaths: Dict = defaultdict(lambda: 0)
        dmg_type_deaths: Dict = defaultdict(lambda: 0)
        player_class: Dict = {}

        lines = []
        with open(fpath, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        game_lines = latest_game_lines(lines, user)
        opt_kill_events = [parse_kill_line(l, gamer_names) for l in game_lines]
        kill_events: List[KillEvent] = [a for a in opt_kill_events if a]
        allies, enemies = get_teams(user, kill_events)


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
                
            if victim == user:
                rivals[killer] += 1
                class_deaths[weapon_class.get(weapon, "many")] += 1
                dmg_type_deaths[weapon_dmg.get(weapon, "melee")] += 1

        tk_kills.set(kills)
        tk_deaths.set(deaths)
        kd_ratio = kills / deaths if deaths else 0
        tk_kd.set(round(kd_ratio, 2))
        tk_streak.set(get_killstreak(user, kill_events))
        tk_elo.set(round(player_elo[user], 1))

        ally_info = sorted([(player_elo[a], a, player_class.get(a, "many"))
                            for a in allies], reverse=True)

        enemy_info = sorted([(player_elo[a], a, player_class.get(a, "many"))
                             for a in enemies], reverse=True)

        top_player_rows = list(range(2, 8))
        update_avg_team_elo(labels[8], allies, enemies, player_elo)
        tk_ally_kills.set(sum(1 for a in kill_events if a.killer in allies))
        tk_enemy_kills.set(sum(1 for a in kill_events if a.killer in enemies))

        for i, (elo, uname, utf2_class) in zip(top_player_rows, ally_info):
            labels[i][0].configure(text=uname)
            labels[i][1].configure(text=round(elo, 1))
            labels[i][2].configure(image=class_tk_imgs[utf2_class])


        for i, (elo, uname, utf2_class) in zip(top_player_rows, enemy_info):
            labels[i][3].configure(text=uname)
            labels[i][4].configure(text=round(elo, 1))
            labels[i][5].configure(image=class_tk_imgs[utf2_class])
        

        for (rdeaths, rname), rv, rev, rci in zip(sort_descending(rivals),
                                             rival_vars,
                                             rival_elo_vars,
                                             rival_class_icons):
            rv.set(f"{rname} ({rdeaths})")
            rev.set(round(player_elo[rname], 1))
            rci.configure(image=class_tk_imgs[player_class.get(rname, "many")])

        time.sleep(3)

x = threading.Thread(target=render, daemon=True)
x.start()
master.mainloop()
