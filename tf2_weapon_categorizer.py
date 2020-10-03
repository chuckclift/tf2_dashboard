
import sqlite3

conn = sqlite3.connect("tf2_weapons.db")
cur = conn.cursor()

fpath = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Team Fortress 2\\tf\\logs.txt"
tf2_class = {"medic", "scout", "spy", "sniper", "heavyweapons", "engineer", "demoman", "pyro", "soldier", "many"}
dmg_type = {"bullet", "explosive", "fire", "bleed", "melee", "critical", "fall", "crush", "drowning"}

def weapon_in_db(weapon):
    cur.execute("select * from weapon where name=:name", {"name": weapon})
    return cur.fetchone()

with open(fpath, errors="ignore") as f:
    for i, line in enumerate(f):
        if "killed" not in line:
            continue
        if not line.strip().endswith(".") and not line.strip().endswith(". (crit)"):
            continue
        one, two = line.split()[-2:]
        weapon = two if two != "(crit)" else one
        
        if weapon_in_db(weapon):
            continue

        print(i, weapon)
        wc = input("  class: ").strip()
        if wc not in tf2_class:
            print("invalid class")
            continue

        
        wt = input("  type: ").strip()
        if wt not in dmg_type:
            print("invalid dmg type")
            continue

        info = {"name":weapon,
                "tf2_class": wc,
                "dmg_type": wt
            }

        cur.execute("insert into weapon values (:name, :tf2_class, :dmg_type)", info)
        conn.commit()
conn.close()
            




