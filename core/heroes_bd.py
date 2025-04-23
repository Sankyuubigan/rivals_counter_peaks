# File: core/heroes_bd.py

# Словарь контрпиков: ключ - герой, значение - список тех, кого он контрит
heroes_counters = {
    "Hulk": ["Iron Man", "Psylocke", "Storm", "Punisher", "Namor", "Thor", "Peni Parker", "Wolverine", "Mantis",
             "Luna Snow", "Winter Soldier", "Adam Warlock"],
    "Groot": ["Punisher", "Hulk", "Venom", "Storm", "Wolverine", "Iron Man", "Winter Soldier", "Hela", "Cloak and Dagger", # <<< ИЗМЕНЕНО
              "Captain America", "Thor", "Rocket Racoon", "Luna Snow", "Mantis", "Invisible Woman", "Psylocke",
              "Star-Lord", "Spider-Man", "Emma Frost"],
    "Thor": ["Peni Parker", "Iron Man", "Storm", "Wolverine", "Punisher", "Star-Lord", "Scarlet Witch", "Mantis",
             "Psylocke", "Winter Soldier", "Luna Snow",
             "Adam Warlock", "Scarlet Witch", "Namor", "Squirrel Girl"],
    "Doctor Strange": ["Wolverine", "Black Panther", "Hulk", "Magik", "Punisher", "Psylocke",
                       "Invisible Woman", "Mantis", "Luna Snow", "Mr Fantastic", "Winter Soldier"], # <<< ИЗМЕНЕНО
    "The Thing": ["Groot", "Iron Man", "Squirrel Girl", "Storm", "Hela", "Adam Warlock", "Scarlet Witch", "Moon Knight",
                  "Doctor Strange", "Star-Lord", "Peni Parker", "Punisher", "Psylocke", "Hawkeye",
                  "Black Widow", "Namor", "Human Torch", "Loki", "Jeff", "Rocket Racoon", "Cloak and Dagger"], # <<< ИЗМЕНЕНО
    "Venom": ["Wolverine", "Punisher", "Storm", "Iron Man", "Winter Soldier", "Peni Parker", "Adam Warlock",
              "Scarlet Witch", "Squirrel Girl", "Namor", "Luna Snow", "Mantis", "The Thing"],
    "Peni Parker": ["Iron Man", "Storm", "Punisher", "Star-Lord", "Doctor Strange", "Namor", "Groot", "Loki",
                    "Winter Soldier", "Hela", "Moon Knight", "Psylocke", "Adam Warlock", "Invisible Woman"],
    "Captain America": ["Groot", "Namor", "Hela", "Storm", "Scarlet Witch", "Loki", "Peni Parker", "Iron Man",
                        "Human Torch", "Jeff", "Rocket Racoon", "Adam Warlock", "Scarlet Witch", "The Thing"],
    "Magneto": ["Storm", "Groot", "Magik", "Loki", "Adam Warlock",
                "Luna Snow", "Mr Fantastic", "Winter Soldier", "Spider-Man", "The Thing"], # <<< ИЗМЕНЕНО
    "Emma Frost": [],


    "Punisher": ["Hela", "Hawkeye", "Iron Fist", "Magik", "Black Panther",
                 "Magneto", "Moon Knight", "Loki","Squirrel Girl"],
    "Hela": ["Punisher", "Magik", "Doctor Strange", "Luna Snow", "Loki", "Venom", "Captain America", "Black Panther",
             "Invisible Woman", "Rocket Racoon"],
    "Moon Knight": ["Storm", "Black Panther", "Iron Man", "Spider-Man", "Magneto", "Psylocke", "Magik",
                    "Venom", "Star-Lord", "Captain America", "Thor", "Hulk"],
    "Iron Man": [
        "Doctor Strange", "Iron Fist", "Rocket Racoon", "Namor", "Star-Lord",
        "Punisher", "Psylocke", "Spider-Man", "Black Widow", "Hela", "Hawkeye", "Adam Warlock", "Mantis", "Luna Snow",
        "Hulk", "Scarlet Witch", "Winter Soldier"
    ],
    "Winter Soldier": ["Hela", "Hawkeye", "Namor", "Iron Fist"],
    "Psylocke": ["Star-Lord", "Invisible Woman", "Namor", "Punisher", "Luna Snow", "Mantis",
                 "Captain America", "Magneto", "Rocket Racoon", "Loki", "Cloak and Dagger"], # <<< ИЗМЕНЕНО
    "Mr Fantastic": ["Groot", "Storm", "Punisher", "Iron Man", "Hawkeye", "Hela", "Winter Soldier", "Black Widow", # <<< ИЗМЕНЕНО (ключ)
                      "Squirrel Girl", "Mantis", "Luna Snow", "Adam Warlock", "Cloak and Dagger", "Jeff", "Peni Parker", # <<< ИЗМЕНЕНО
                      "Scarlet Witch"],
    "Storm": [
        "Doctor Strange", "Punisher", "Hela", "Namor", "Iron Fist", "Psylocke",
        "Black Widow", "Spider-Man", "Star-Lord",
        "Cloak and Dagger", "Hulk", "Scarlet Witch", "Winter Soldier" # <<< ИЗМЕНЕНО
    ],
    "Black Panther": [
        "The Thing", "Human Torch", "Star-Lord", "Peni Parker", "Iron Man", "Storm", "Namor", "Cloak and Dagger", # <<< ИЗМЕНЕНО
        "Magneto",
        "Punisher", "Psylocke", "Mantis", "Winter Soldier", "Jeff", "Adam Warlock", "Luna Snow", "Rocket Racoon",
        "Scarlet Witch"
    ],
    "Squirrel Girl": ["Groot", "Captain America", "Hawkeye", "Storm", "Star-Lord",
                      "Iron Man", "Scarlet Witch", "Human Torch", "Magneto", "Hulk", "Hela", "Black Widow"],
    "Spider-Man": ["Namor", "Hela", "Hawkeye", "Luna Snow", "Cloak and Dagger", # <<< ИЗМЕНЕНО
                   "Adam Warlock", "Rocket Racoon", "Jeff",
                   "Squirrel Girl", "Peni Parker", "Captain America", "Scarlet Witch", "Winter Soldier", "Punisher"],
    "Star-Lord": ["Magneto", "Luna Snow", "Loki", "Doctor Strange", "Hela", "Punisher", "Hawkeye", "Namor", "Mantis",
                  "Invisible Woman", "Hulk", "Scarlet Witch"],
    "Wolverine": ["Peni Parker", "Iron Man", "Namor", "Storm", "Invisible Woman", "Captain America", "Psylocke",
                  "Mantis", "Luna Snow", "Magneto", "Hela", "Adam Warlock", "Scarlet Witch", "The Thing",
                  "Cloak and Dagger","Mr Fantastic"], # <<< ИЗМЕНЕНО
    "Hawkeye": ["Psylocke", "Groot", "Spider-Man", "Hela", "Doctor Strange", "Black Panther", "Iron Fist",
                "Rocket Racoon", "Loki"],
    "Magik": ["Iron Man", "Namor", "Storm", "Doctor Strange", "Luna Snow", "Peni Parker", "Magneto", "Thor",
              "Winter Soldier", "Adam Warlock", "Cloak and Dagger", "Jeff", "Rocket Racoon", "Scarlet Witch"], # <<< ИЗМЕНЕНО
    "Black Widow": ["Psylocke", "Magik", "Black Panther", "Doctor Strange", "Venom", "Captain America",
                    "Scarlet Witch"],
    "Scarlet Witch": ["Punisher", "Hawkeye", "Hela", "Peni Parker", "Mantis", "Luna Snow"],
    "Namor": ["Moon Knight", "Hela", "Hawkeye", "Magneto", "Doctor Strange", "Punisher", "Winter Soldier",
              "Loki", "Cloak and Dagger", "Adam Warlock"], # <<< ИЗМЕНЕНО
    "Iron Fist": ["Namor", "Captain America", "Invisible Woman", "Rocket Racoon", "Loki", "Storm",
                  "Luna Snow", "Winter Soldier", "Punisher", "Mantis", "Hulk", "Peni Parker", "Scarlet Witch",
                  "Squirrel Girl", "Magik", "Hela", "Adam Warlock"],
    "Human Torch": ["Hela", "Hawkeye", "Punisher", "Psylocke", "Spider-Man", "Luna Snow", "Hulk", "Scarlet Witch"],


    "Loki": ["Moon Knight", "Iron Man", "Punisher", "Winter Soldier", "Wolverine", "Adam Warlock", "Spider-Man",
             "Mr Fantastic", "Captain America", "Thor", "The Thing", "Storm", "Hela", "Jeff", "Moon Knight"], # <<< ИЗМЕНЕНО
    "Cloak and Dagger": ["Magneto", "Magik", "Hela", "Hawkeye", "Psylocke", "Wolverine", "Jeff", "Squirrel Girl", # <<< ИЗМЕНЕНО (ключ)
                       "Moon Knight", "Rocket Racoon","Emma Frost","Scarlet Witch","Iron Man"],
    "Jeff": ["Iron Man", "Storm", "Psylocke", "Peni Parker", "Squirrel Girl", "Magneto", "Hela",
             "Cloak and Dagger", "Iron Fist", "Luna Snow", "Mantis", "The Thing", "Namor","Emma Frost"], # <<< ИЗМЕНЕНО
    "Mantis": ["Iron Man", "Punisher", "Iron Fist", "Captain America", "Psylocke", "Jeff", "Magneto", "Hela", "Magik",
               "Black Panther", "Moon Knight", "Squirrel Girl", "The Thing", "Wolverine", "Star-Lord", "Rocket Racoon",
               "Storm","Scarlet Witch"],
    "Luna Snow": ["Iron Man", "Punisher", "Psylocke", "Scarlet Witch", "Captain America", "Loki", "Magneto",
                  "The Thing", "Magik", "Black Panther", "Mr Fantastic", "Moon Knight", "Venom", "Thor", # <<< ИЗМЕНЕНО
                  "Hulk", "Rocket Racoon", "Storm"],
    "Rocket Racoon": ["Star-Lord", "Black Panther", "Iron Man", "Psylocke", "Venom", "Magneto", "Iron Fist",
                      "Captain America", "Punisher", "Wolverine","Scarlet Witch"],
    "Invisible Woman": ["Punisher", "Moon Knight", "Squirrel Girl", "Magik", "Spider-Man", "Jeff", "Iron Man",
                        "Magneto", "Namor", "The Thing", "Rocket Racoon", "Mr Fantastic", "Storm", "Black Panther","Emma Frost","Scarlet Witch"], # <<< ИЗМЕНЕНО
    "Adam Warlock": ["Black Panther", "Magneto", "Doctor Strange", "Hela", "Black Widow",
                     "Winter Soldier", "Squirrel Girl", "Storm"],
}

# Основной список всех героев
heroes = [
    "Hulk", "Groot", "Thor", "Doctor Strange", "The Thing", "Venom", "Peni Parker", "Captain America",
    "Magneto","Emma Frost",
    "Punisher", "Hela", "Moon Knight","Iron Man", "Winter Soldier", "Psylocke", "Mr Fantastic", "Storm", # <<< ИЗМЕНЕНО
    "Black Panther", "Squirrel Girl", "Spider-Man", "Star-Lord", "Wolverine", "Hawkeye", "Magik", "Black Widow",
    "Scarlet Witch", "Namor", "Iron Fist", "Human Torch",
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
    "Magneto": ["Scarlet Witch"],

    "Punisher": ["Doctor Strange", "Rocket Racoon"],
    "Hela": [],
    "Moon Knight": ["Cloak and Dagger"], # <<< ИЗМЕНЕНО
    "Iron Man": ["Hulk", "Groot"],
    "Winter Soldier": ["Rocket Racoon"],
    "Psylocke": ["Doctor Strange", "Magik"],
    "Mr Fantastic": ["Invisible Woman", "Captain America", "Thor", "Hulk", "Venom", "Doctor Strange", "The Thing"], # <<< ИЗМЕНЕНО (ключ и значение)
    "Storm": ["Thor", "Invisible Woman", "Human Torch"],
    "Black Panther": ["Magik"],
    "Squirrel Girl": ["Spider-Man"],
    "Spider-Man": ["Venom"],
    "Star-Lord": ["Adam Warlock"],
    "Wolverine": ["Hulk", "The Thing"],
    "Hawkeye": [],
    "Magik": [],
    "Black Widow": ["Hawkeye"],
    "Scarlet Witch": ["Doctor Strange", "Jeff"],
    "Namor": ["Luna Snow"],
    "Iron Fist": [],
    "Human Torch": ["Invisible Woman"],

    "Loki": ["Hela"],
    "Cloak and Dagger": [], # <<< ИЗМЕНЕНО (ключ)
    "Jeff": ["Luna Snow", "Groot"],
    "Mantis": ["Captain America", "Adam Warlock"],
    "Luna Snow": ["Hulk", "The Thing", "Groot", "Iron Fist"],
    "Rocket Racoon": ["Captain America"],
    "Invisible Woman": [],
    "Adam Warlock": [],
}

# Распределение героев по ролям (для расчета эффективной команды)
hero_roles = {
    "tanks": ["Hulk", "Groot", "Thor", "Doctor Strange", "The Thing", "Venom", "Peni Parker", "Captain America",
              "Magneto","Emma Frost"],
    "attackers": ["Punisher", "Hela", "Moon Knight", "Iron Man", "Winter Soldier", "Psylocke", "Mr Fantastic", "Storm", # <<< ИЗМЕНЕНО
                  "Black Panther", "Squirrel Girl", "Spider-Man", "Star-Lord", "Wolverine", "Hawkeye", "Magik",
                  "Black Widow", "Scarlet Witch", "Namor", "Iron Fist", "Human Torch"],
    "supports": ["Loki", "Cloak and Dagger", "Jeff", "Mantis", "Luna Snow", "Rocket Racoon", "Invisible Woman", # <<< ИЗМЕНЕНО
                 "Adam Warlock"]
}

# Информационные списки (не используются в логике напрямую)
teammates_healers_noobs = {
    "Spider-Man", "Jeff", "Iron Fist", "Scarlet Witch", "Psylocke", "Captain America"
}
need_defend_healers={
# грут стрендж пени магнето 3хила "Winter Soldier" "Punisher" "Hela" "Psylocke" "Storm" "Hawkeye" "Scarlet Witch" "Namor"
}