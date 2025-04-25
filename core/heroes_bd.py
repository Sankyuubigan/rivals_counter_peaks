# File: core/heroes_bd.py

# Словарь контрпиков: ключ - герой, значение - список тех, кого он контрит
heroes_counters = {
    "Hulk": ["Iron Man", "Psylocke", "Storm", "Punisher", "Namor", "Thor", "Peni Parker", "Wolverine", "Mantis",
             "Luna Snow", "Bucky", "Adam Warlock","Emma Frost"],
    "Groot": ["Punisher", "Hulk", "Venom", "Storm", "Wolverine", "Iron Man", "Bucky", "Hela", "Cloak and Dagger", # <<< ИЗМЕНЕНО
              "Captain America", "Thor", "Rocket Racoon", "Luna Snow", "Mantis", "Invisible Woman", "Psylocke",
              "StarLord", "SpiderMan", "Emma Frost"],
    "Thor": ["Peni Parker", "Iron Man", "Storm", "Wolverine", "Punisher", "StarLord", "Witch", "Mantis",
             "Psylocke", "Bucky", "Luna Snow",
             "Adam Warlock", "Witch", "Namor", "Squirrel Girl","Emma Frost"],
    "Doctor Strange": ["Wolverine", "Black Panther", "Hulk", "Magik", "Punisher", "Psylocke",
                       "Invisible Woman", "Mantis", "Luna Snow", "Mr Fantastic", "Bucky"], # <<< ИЗМЕНЕНО
    "The Thing": ["Groot", "Iron Man", "Squirrel Girl", "Storm", "Hela", "Adam Warlock", "Witch", "Moon Knight",
                  "Doctor Strange", "StarLord", "Peni Parker", "Punisher", "Psylocke", "Hawkeye",
                  "Widow", "Namor", "Human Torch", "Loki", "Jeff", "Rocket Racoon", "Cloak and Dagger","Emma Frost"], # <<< ИЗМЕНЕНО
    "Venom": ["Wolverine", "Punisher", "Storm", "Iron Man", "Bucky", "Peni Parker", "Adam Warlock",
              "Witch", "Squirrel Girl", "Namor", "Luna Snow", "Mantis", "The Thing","Emma Frost"],
    "Peni Parker": ["Iron Man", "Storm", "Punisher", "StarLord", "Doctor Strange", "Namor", "Groot", "Loki",
                    "Bucky", "Hela", "Moon Knight", "Psylocke", "Adam Warlock", "Invisible Woman"],
    "Captain America": ["Groot", "Namor", "Hela", "Storm", "Witch", "Loki", "Peni Parker", "Iron Man",
                        "Human Torch", "Jeff", "Rocket Racoon", "Adam Warlock", "Witch", "The Thing","Emma Frost"],
    "Magneto": ["Storm", "Groot", "Magik", "Loki", "Adam Warlock",
                "Luna Snow", "Mr Fantastic", "Bucky", "SpiderMan", "The Thing"], # <<< ИЗМЕНЕНО
    "Emma Frost": ["Punisher", "Hela",  "Hawkeye", "Widow"],


    "Punisher": ["Hela", "Hawkeye", "Fister", "Magik", "Black Panther",
                 "Magneto", "Moon Knight", "Loki","Squirrel Girl"],
    "Hela": ["Punisher", "Magik", "Doctor Strange", "Luna Snow", "Loki", "Venom", "Captain America", "Black Panther",
             "Invisible Woman", "Rocket Racoon"],
    "Moon Knight": ["Storm", "Black Panther", "Iron Man", "SpiderMan", "Magneto", "Psylocke", "Magik",
                    "Venom", "StarLord", "Captain America", "Thor", "Hulk"],
    "Iron Man": [
        "Doctor Strange", "Fister", "Rocket Racoon", "Namor", "StarLord",
        "Punisher", "Psylocke", "SpiderMan", "Widow", "Hela", "Hawkeye", "Adam Warlock", "Mantis", "Luna Snow",
        "Hulk", "Witch", "Bucky"
    ],
    "Bucky": ["Hela", "Hawkeye", "Namor", "Fister"],
    "Psylocke": ["StarLord", "Invisible Woman", "Namor", "Punisher", "Luna Snow", "Mantis",
                 "Captain America", "Magneto", "Rocket Racoon", "Loki", "Cloak and Dagger"], # <<< ИЗМЕНЕНО
    "Mr Fantastic": ["Groot", "Storm", "Punisher", "Iron Man", "Hawkeye", "Hela", "Bucky", "Widow", # <<< ИЗМЕНЕНО (ключ)
                      "Squirrel Girl", "Mantis", "Luna Snow", "Adam Warlock", "Cloak and Dagger", "Jeff", "Peni Parker", # <<< ИЗМЕНЕНО
                      "Witch","Emma Frost"],
    "Storm": [
        "Doctor Strange", "Punisher", "Hela", "Namor", "Fister", "Psylocke",
        "Widow", "SpiderMan", "StarLord",
        "Cloak and Dagger", "Hulk", "Witch", "Bucky" # <<< ИЗМЕНЕНО
    ],
    "Black Panther": [
        "The Thing", "Human Torch", "StarLord", "Peni Parker", "Iron Man", "Storm", "Namor", "Cloak and Dagger", # <<< ИЗМЕНЕНО
        "Magneto",
        "Punisher", "Psylocke", "Mantis", "Bucky", "Jeff", "Adam Warlock", "Luna Snow", "Rocket Racoon",
        "Witch"
    ],
    "Squirrel Girl": ["Groot", "Captain America", "Hawkeye", "Storm", "StarLord",
                      "Iron Man", "Witch", "Human Torch", "Magneto", "Hulk", "Hela", "Widow"],
    "SpiderMan": ["Namor", "Hela", "Hawkeye", "Luna Snow", "Cloak and Dagger", # <<< ИЗМЕНЕНО
                   "Adam Warlock", "Rocket Racoon", "Jeff",
                   "Squirrel Girl", "Peni Parker", "Captain America", "Witch", "Bucky", "Punisher","The Thing","Emma Frost"],
    "StarLord": ["Magneto", "Luna Snow", "Loki", "Doctor Strange", "Hela", "Punisher", "Hawkeye", "Namor", "Mantis",
                  "Invisible Woman", "Hulk", "Witch"],
    "Wolverine": ["Peni Parker", "Iron Man", "Namor", "Storm", "Invisible Woman", "Captain America", "Psylocke",
                  "Mantis", "Luna Snow", "Magneto", "Hela", "Adam Warlock", "Witch", "The Thing",
                  "Cloak and Dagger","Mr Fantastic"], # <<< ИЗМЕНЕНО
    "Hawkeye": ["Psylocke", "Groot", "SpiderMan", "Hela", "Doctor Strange", "Black Panther", "Fister",
                "Rocket Racoon", "Loki"],
    "Magik": ["Iron Man", "Namor", "Storm", "Doctor Strange", "Luna Snow", "Peni Parker", "Magneto", "Thor",
              "Bucky", "Adam Warlock", "Cloak and Dagger", "Jeff", "Rocket Racoon", "Witch", "The Thing","Emma Frost"], # <<< ИЗМЕНЕНО
    "Widow": ["Psylocke", "Magik", "Black Panther", "Doctor Strange", "Venom", "Captain America",
                    "Witch"],
    "Witch": ["Punisher", "Hawkeye", "Hela", "Peni Parker", "Mantis", "Luna Snow"],
    "Namor": ["Moon Knight", "Hela", "Hawkeye", "Magneto", "Doctor Strange", "Punisher", "Bucky",
              "Loki", "Cloak and Dagger", "Adam Warlock"], # <<< ИЗМЕНЕНО
    "Fister": ["Namor", "Captain America", "Invisible Woman", "Rocket Racoon", "Loki", "Storm",
                  "Luna Snow", "Bucky", "Punisher", "Mantis", "Hulk", "Peni Parker", "Witch",
                  "Squirrel Girl", "Magik", "Hela", "Adam Warlock","Emma Frost"],
    "Human Torch": ["Hela", "Hawkeye", "Punisher", "Psylocke", "SpiderMan", "Luna Snow", "Hulk", "Witch"],


    "Loki": ["Moon Knight", "Iron Man", "Punisher", "Bucky", "Wolverine", "Adam Warlock", "SpiderMan",
             "Mr Fantastic", "Captain America", "Thor", "The Thing", "Storm", "Hela", "Jeff", "Moon Knight"], # <<< ИЗМЕНЕНО
    "Cloak and Dagger": ["Magneto", "Magik", "Hela", "Hawkeye", "Psylocke", "Wolverine", "Jeff", "Squirrel Girl", # <<< ИЗМЕНЕНО (ключ)
                       "Moon Knight", "Rocket Racoon","Emma Frost","Witch","Iron Man"],
    "Jeff": ["Iron Man", "Storm", "Psylocke", "Peni Parker", "Squirrel Girl", "Magneto", "Hela",
             "Cloak and Dagger", "Fister", "Luna Snow", "Mantis", "The Thing", "Namor","Emma Frost"], # <<< ИЗМЕНЕНО
    "Mantis": ["Iron Man", "Punisher", "Fister", "Captain America", "Psylocke", "Jeff", "Magneto", "Hela", "Magik",
               "Black Panther", "Moon Knight", "Squirrel Girl", "The Thing", "Wolverine", "StarLord", "Rocket Racoon",
               "Storm","Witch"],
    "Luna Snow": ["Iron Man", "Punisher", "Psylocke", "Witch", "Captain America", "Loki", "Magneto",
                  "The Thing", "Magik", "Black Panther", "Mr Fantastic", "Moon Knight", "Venom", "Thor", # <<< ИЗМЕНЕНО
                  "Hulk", "Rocket Racoon", "Storm"],
    "Rocket Racoon": ["StarLord", "Black Panther", "Iron Man", "Psylocke", "Venom", "Magneto", "Fister",
                      "Captain America", "Punisher", "Wolverine","Witch"],
    "Invisible Woman": ["Punisher", "Moon Knight", "Squirrel Girl", "Magik", "SpiderMan", "Jeff", "Iron Man",
                        "Magneto", "Namor", "The Thing", "Rocket Racoon", "Mr Fantastic", "Storm", "Black Panther","Emma Frost","Witch"], # <<< ИЗМЕНЕНО
    "Adam Warlock": ["Black Panther", "Magneto", "Doctor Strange", "Hela", "Widow",
                     "Bucky", "Squirrel Girl", "Storm"],
}

# Основной список всех героев
heroes = [
    "Hulk", "Groot", "Thor", "Doctor Strange", "The Thing", "Venom", "Peni Parker", "Captain America",
    "Magneto","Emma Frost",
    "Punisher", "Hela", "Moon Knight","Iron Man", "Bucky", "Psylocke", "Mr Fantastic", "Storm", # <<< ИЗМЕНЕНО
    "Black Panther", "Squirrel Girl", "SpiderMan", "StarLord", "Wolverine", "Hawkeye", "Magik", "Widow",
    "Witch", "Namor", "Fister", "Human Torch",
    "Loki", "Cloak and Dagger", "Jeff", "Mantis", "Luna Snow", # <<< ИЗМЕНЕНО
    "Rocket Racoon", "Invisible Woman", "Adam Warlock",
]

# Герои, которые пока не реализованы (для информации)
futures = ["Quicksilver", "Doctor Doom", "Cyclops", "Jean Grey", "Rogue", "Gambit", "Beast", "Iceman", "Colossus",
           "Nightcrawler",
           "Shadowcat", "Cable", "Deadpool", "Juggernaut", "Mystique", "Sabretooth",
           "Silver Surfer", "Vision", ]

# Возможные синергии между героями (не используется в текущей логике подсчета рейтинга, но может быть полезно)
heroes_compositions = {
    "Hulk": [],
    "Groot": ["Invisible Woman", "Jeff", "Cloak and Dagger", "Luna Snow"], # <<< ИЗМЕНЕНО
    "Thor": ["Hela", "Doctor Strange", "Magneto"],
    "Doctor Strange": ["Hulk"],
    "The Thing": ["Invisible Woman", "Mr Fantastic", "Captain America", "Thor", "Hulk", "Venom", "Doctor Strange", # <<< ИЗМЕНЕНО
                  "Cloak and Dagger", "Jeff", "Magneto"], # <<< ИЗМЕНЕНО
    "Venom": [],
    "Peni Parker": ["Venom", "Groot", "Luna Snow", "Invisible Woman", "Cloak and Dagger"], # <<< ИЗМЕНЕНО
    "Captain America": ["Thor"],
    "Magneto": [],

    "Punisher": ["Doctor Strange", "Rocket Racoon"],
    "Hela": [],
    "Moon Knight": ["Cloak and Dagger"], # <<< ИЗМЕНЕНО
    "Iron Man": ["Hulk", "Groot"],
    "Bucky": ["Rocket Racoon"],
    "Psylocke": ["Doctor Strange", "Magik"],
    "Mr Fantastic": ["Invisible Woman", "Captain America", "Thor", "Hulk", "Venom", "Doctor Strange", "The Thing"], # <<< ИЗМЕНЕНО (ключ и значение)
    "Storm": ["Thor", "Invisible Woman", "Human Torch"],
    "Black Panther": ["Magik"],
    "Squirrel Girl": ["SpiderMan"],
    "SpiderMan": ["Venom"],
    "StarLord": ["Adam Warlock"],
    "Wolverine": ["Hulk", "The Thing"],
    "Hawkeye": [],
    "Magik": [],
    "Widow": ["Hawkeye"],
    "Witch": ["Doctor Strange", "Jeff"],
    "Namor": ["Luna Snow"],
    "Fister": [],
    "Human Torch": ["Invisible Woman"],

    "Loki": ["Hela"],
    "Cloak and Dagger": [], # <<< ИЗМЕНЕНО (ключ)
    "Jeff": ["Luna Snow", "Groot"],
    "Mantis": ["Captain America", "Adam Warlock"],
    "Luna Snow": ["Hulk", "The Thing", "Groot", "Fister"],
    "Rocket Racoon": ["Captain America"],
    "Invisible Woman": [],
    "Adam Warlock": [],
}

# Распределение героев по ролям (для расчета эффективной команды)
hero_roles = {
    "tanks": ["Hulk", "Groot", "Thor", "Doctor Strange", "The Thing", "Venom", "Peni Parker", "Captain America",
              "Magneto","Emma Frost"],
    "attackers": ["Punisher", "Hela", "Moon Knight", "Iron Man", "Bucky", "Psylocke", "Mr Fantastic", "Storm", # <<< ИЗМЕНЕНО
                  "Black Panther", "Squirrel Girl", "SpiderMan", "StarLord", "Wolverine", "Hawkeye", "Magik",
                  "Widow", "Witch", "Namor", "Fister", "Human Torch"],
    "supports": ["Loki", "Cloak and Dagger", "Jeff", "Mantis", "Luna Snow", "Rocket Racoon", "Invisible Woman", # <<< ИЗМЕНЕНО
                 "Adam Warlock"]
}

flunkers={
"Hulk" "Thor" "The Thing" "Venom" "Captain America" "Psylocke" "Mr Fantastic" "Black Panther" "SpiderMan" "Magik" "Witch" "Fister" "Jeff"
}

range ={
"Punisher" "Hela" "Bucky" "Hawkeye" "Widow"
}

# Информационные списки (не используются в логике напрямую)
if_teammates_healers_noobs = {
    "SpiderMan", "Jeff", "Fister", "Witch", "Psylocke", "Captain America"
}
if_need_defend_healers={
# грут стрендж пени магнето 3хила "Bucky" "Punisher" "Hela" "Psylocke" "Storm" "Hawkeye" "Witch" "Namor"
}