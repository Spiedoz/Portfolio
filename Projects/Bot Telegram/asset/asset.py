import sqlite3

# second database used to store information of items, monsters, classes
database = "asset.db"

def connect_db():
    conn = sqlite3.connect(database)
    return conn


# Classes
def get_first_class():
    conn = connect_db()
    c = conn.cursor()
    name = c.execute("SELECT name FROM CLASSES WHERE id = 1;").fetchone()[0]
    hp = c.execute("SELECT hp FROM CLASSES WHERE id = 1;").fetchone()[0]
    atk = c.execute("SELECT atk FROM CLASSES WHERE id = 1;").fetchone()[0]
    defence = c.execute("SELECT def FROM CLASSES WHERE id = 1;").fetchone()[0]
    vel = c.execute("SELECT vel FROM CLASSES WHERE id = 1;").fetchone()[0]
    crit = c.execute("SELECT crit FROM CLASSES WHERE id = 1;").fetchone()[0]
    conn.close()
    return name, hp, atk, defence, vel, crit


def getClass_info(className):
    conn = connect_db()
    c = conn.cursor()
    classID = c.execute("SELECT id FROM CLASSES WHERE name LIKE ?", (className,)).fetchone()[0]
    name = c.execute("SELECT name FROM CLASSES WHERE id = ?", (classID,)).fetchone()[0]
    hp = c.execute("SELECT hp FROM CLASSES WHERE id = ?", (classID,)).fetchone()[0]
    atk = c.execute("SELECT atk FROM CLASSES WHERE id = ?", (classID,)).fetchone()[0]
    defe = c.execute("SELECT def FROM CLASSES WHERE id = ?", (classID,)).fetchone()[0]
    vel = c.execute("SELECT vel FROM CLASSES WHERE id = ?", (classID,)).fetchone()[0]
    crit = c.execute("SELECT crit FROM CLASSES WHERE id = ?", (classID,)).fetchone()[0]
    conn.close()
    return name, hp, atk, defe, vel, crit


def get_evolution_info(className):
    conn = connect_db()
    c = conn.cursor()
    classID = c.execute("SELECT id FROM CLASSES WHERE name LIKE ?", (className,)).fetchone()[0]
    evolutionName = c.execute("SELECT name FROM CLASSES WHERE id = ?", (classID+1,)).fetchone()[0]
    evolutionHP = c.execute("SELECT hp FROM CLASSES WHERE id = ?", (classID+1,)).fetchone()[0]
    evolutionAtk = c.execute("SELECT atk FROM CLASSES WHERE id = ?", (classID+1,)).fetchone()[0]
    evolutionDef = c.execute("SELECT def FROM CLASSES WHERE id = ?", (classID+1,)).fetchone()[0]
    evolutionVel = c.execute("SELECT vel FROM CLASSES WHERE id = ?", (classID+1,)).fetchone()[0]
    evolutionCrit = c.execute("SELECT crit FROM CLASSES WHERE id = ?", (classID+1,)).fetchone()[0]
    conn.close()
    return evolutionName, evolutionHP, evolutionAtk, evolutionDef, evolutionVel, evolutionCrit


# Regions
def fetch_regions():
    conn = connect_db()
    c = conn.cursor()
    regions = c.execute("SELECT id, name, min_lvl, callback FROM Regions").fetchall()
    conn.close()
    return regions

def get_region_info(regionID):
    conn = connect_db()
    c = conn.cursor()
    region = c.execute("SELECT id, name, min_lvl, callback FROM Regions WHERE id = ?", (regionID,)).fetchall()
    conn.close()
    return region

# Areas
def fetch_areas(regionID=0):
    conn = connect_db()
    c = conn.cursor()
    if regionID == 0:
        areas = c.execute("SELECT id, name, min_lvl, callback FROM Areas").fetchall()
    else:
        areas = c.execute("SELECT id, name, min_lvl, callback FROM Areas WHERE regionID = ?", (regionID,)).fetchall()
    conn.close()
    return areas

def get_area_info(regionID, areaID):
    conn = connect_db()
    c = conn.cursor()
    area = c.execute("SELECT id, name, type, min_lvl, callback FROM Areas WHERE id = ? AND regionID = ?", (areaID, regionID,)).fetchone()
    conn.close()
    return area


# Items
def fetch_itemID(regionID, areaID, rarity):
    conn = connect_db()
    c = conn.cursor()
    items = c.execute("SELECT id FROM Items WHERE regionID = ? AND areaID = ? AND rarity = ?",
                      (regionID, areaID, rarity)).fetchall()
    conn.close()
    return items


def get_item_info(itemID):
    conn = connect_db()
    c = conn.cursor()
    itemName = c.execute("SELECT name FROM Items WHERE id = ?", (itemID,)).fetchone()[0]
    itemRarity = c.execute("SELECT rarity FROM Items WHERE id = ?", (itemID,)).fetchone()[0]
    itemType = c.execute("SELECT type FROM Items WHERE id = ?", (itemID,)).fetchone()[0]
    conn.close()
    return itemName, itemRarity, itemType


def get_item_id(itemName):
    conn = connect_db()
    c = conn.cursor()
    itemID = c.execute("SELECT id FROM Items WHERE name = ?", (itemName,)).fetchone()[0]
    conn.close()
    return itemID


def inspect_item(itemID):
    conn = connect_db()
    c = conn.cursor()
    itemName = c.execute("SELECT name FROM Items WHERE id = ?", (itemID,)).fetchone()[0]
    itemRarity = c.execute("SELECT rarity FROM Items WHERE id = ?", (itemID,)).fetchone()[0]
    itemPrice = c.execute("SELECT price FROM Items WHERE id = ?", (itemID,)).fetchone()[0]
    itemType = c.execute("SELECT type FROM Items WHERE id = ?", (itemID,)).fetchone()[0]
    conn.close()
    return itemName, itemRarity, itemPrice, itemType


# Potions
def get_potion_ingredients(potion_id: int) -> list[tuple[int, int, str]]:
    conn = connect_db()
    c = conn.cursor()
    ingredients = c.execute("""
        SELECT p.ingredientID, p.ingredientQt, i.name 
        FROM Potions p 
        JOIN Items i ON p.ingredientID = i.id 
        WHERE p.id = ?
    """, (potion_id,)).fetchall()
    conn.close()
    return ingredients


def get_potion_info(potion_id: int) -> tuple[str, str, str, int, list[tuple[str, int]]]:
    conn = connect_db()
    c = conn.cursor()
    potion_info = c.execute("SELECT name, rarity, type, bonus FROM Potions WHERE id = ?", (potion_id,)).fetchone()
    ingredients = get_potion_ingredients(potion_id)
    conn.close()
    return (*potion_info, [(name, qty) for _, qty, name in ingredients])


def get_potion(potionID):
    conn = connect_db()
    c = conn.cursor()
    result = c.execute("SELECT name, rarity, type, price FROM Potions WHERE id = ?", (potionID,)).fetchone()
    conn.close()
    return result


def get_potion_bonus(potionName):
    conn = connect_db()
    c = conn.cursor()
    result = c.execute("SELECT bonus FROM Potions WHERE name = ?", (potionName,)).fetchone()[0]
    conn.close()
    return result


# Weapons
def fetch_weapons(table, regionID=0):
    conn = connect_db()
    c = conn.cursor()
    if regionID == 0:
        weapons = c.execute("SELECT id, name, price, classes, rarity, atk FROM '{}'".format(table)).fetchall()
    else:
        weapons = c.execute("SELECT id, name, price, classes, rarity, atk FROM '{}' WHERE regionID = ?".format(table),
                            (regionID,)).fetchall()
    conn.close()
    return [{'id': w[0], 'name': w[1], 'price': w[2], 'classes': w[3], 'rarity': w[4], 'attack': w[5]} for w in weapons]


def fetch_shields(regionID=0):
    conn = connect_db()
    c = conn.cursor()
    if regionID == 0:
        shields = c.execute("SELECT id, name, price, rarity, def FROM Shields",).fetchall()
    else:
        shields = c.execute("SELECT id, name, price, rarity, def FROM Shields WHERE regionID = ?", (regionID,)).fetchall()
    conn.close()
    return [{'id': s[0], 'name': s[1], 'price': s[2], 'rarity': s[3], 'defense': s[4]} for s in shields]


# Monsters
def fetch_monsterID(regionID, areaID, rarity):
    conn = connect_db()
    c = conn.cursor()
    monsters = c.execute("SELECT id FROM Monsters WHERE regionID = ? AND areaID = ? AND rarity = ?",
                         (regionID, areaID, rarity)).fetchall()
    conn.close()
    return monsters


def get_monster_info(monsterID):
    conn = connect_db()
    c = conn.cursor()
    monsterName = c.execute("SELECT name FROM Monsters WHERE id = ?", (monsterID,)).fetchone()[0]
    monsterPhoto = c.execute("SELECT photo FROM Monsters WHERE id = ?", (monsterID,)).fetchone()[0]
    monsterLvl = c.execute("SELECT min_lvl, max_lvl FROM Monsters WHERE id = ?", (monsterID,)).fetchone()
    monsterRarity = c.execute("SELECT rarity FROM Monsters WHERE id = ?", (monsterID,)).fetchone()[0]
    monsterHP = c.execute("SELECT min_hp, max_hp FROM Monsters WHERE id = ?", (monsterID,)).fetchone()
    monsterAtk = c.execute("SELECT min_atk, max_atk FROM Monsters WHERE id = ?", (monsterID,)).fetchone()
    monsterDef = c.execute("SELECT min_def, max_def FROM Monsters WHERE id = ?", (monsterID,)).fetchone()
    monsterVel = c.execute("SELECT min_vel, max_vel FROM Monsters WHERE id = ?", (monsterID,)).fetchone()
    monsterCrit = c.execute("SELECT min_crit, max_crit FROM Monsters WHERE id = ?", (monsterID,)).fetchone()
    monsterRegion = c.execute("SELECT regionID FROM Monsters WHERE id = ?", (monsterID,)).fetchone()[0]
    monsterArea = c.execute("SELECT areaID FROM Monsters WHERE id = ?", (monsterID,)).fetchone()[0]
    conn.close()
    return (monsterName, monsterPhoto, monsterLvl, monsterRarity, monsterHP, monsterAtk,
            monsterDef, monsterVel, monsterCrit, monsterRegion, monsterArea)


