# код файла heroes_bd.py

heroes = [
    "The Thing", "Human Torch", "Storm", "Invisible Woman", "Mr. Fantastic",
    "Venom", "Black Panther", "Cloak & Dagger", "Groot", "Hela",
    "Luna Snow", "Magik", "Iron Fist", "Peni Parker", "Hulk",
    "Hawkeye", "Psylocke", "Captain America", "Moon Knight", "Loki",
    "Mantis", "Spider-Man", "Rocket Racoon", "Wolverine", "Thor",
    "Squirrel Girl", "Namor", "Punisher", "Jeff", "Scarlet Witch",
    "Black Widow", "Adam Warlock", "Winter Soldier", "Magneto", "Doctor Strange",
    "Star-Lord", "Iron Man"
]

futures=["Quicksilver", "Doctor Doom","Cyclops", "Jean Grey", "Rogue", "Gambit", "Beast", "Iceman", "Colossus", "Nightcrawler",
    "Shadowcat", "Cable", "Deadpool", "Emma Frost", "Juggernaut", "Mystique", "Sabretooth",
    "Silver Surfer", "Vision",]

# Пример данных о контрпиках (каждый герой имеет список контрпиков из того же списка героев)
hero_counters = {
    "Hulk": ["Iron Man", "Psylocke", "Storm", "Punisher", "Namor", "Thor", "Peni Parker", "Wolverine", "Mantis", "Luna Snow","Winter Soldier","Adam Warlock"],
    "Groot": ["Punisher", "Hulk", "Venom", "Storm", "Wolverine", "Iron Man", "Winter Soldier", "Hela", "Cloak & Dagger",
              "Captain America","Thor","Rocket Racoon","Luna Snow","Mantis","Invisible Woman","Psylocke","Star-Lord"],
    "Thor": ["Peni Parker", "Iron Man", "Storm", "Wolverine", "Punisher", "Star-Lord", "Scarlet Witch", "Mantis","Psylocke","Winter Soldier","Luna Snow",
             "Adam Warlock","Scarlet Witch","Namor","Squirrel Girl"],
    "Doctor Strange": ["Wolverine", "Black Panther", "Venom", "Hulk","Magik","Punisher","Psylocke","Invisible Woman","Mantis", "Luna Snow","Mr. Fantastic"],
    "The Thing": ["Groot", "Iron Man", "Squirrel Girl", "Storm", "Hela","Adam Warlock","Scarlet Witch"],
    "Venom": ["Punisher", "Wolverine", "Storm", "Magneto", "Iron Man","Winter Soldier","Peni Parker","Adam Warlock","Scarlet Witch","Squirrel Girl"],
    "Peni Parker": ["Iron Man", "Storm", "Punisher", "Star-Lord", "Doctor Strange", "Namor", "Groot", "Loki","Winter Soldier","Hela","Moon Knight","Psylocke","Adam Warlock","Invisible Woman"],
    "Captain America": ["Groot", "Namor", "Hela", "Storm", "Scarlet Witch", "Loki","Peni Parker","Iron Man","Human Torch","Jeff","Rocket Racoon","Adam Warlock","Scarlet Witch"],
    "Magneto": ["Punisher", "Wolverine", "Venom", "Black Panther", "Storm","Groot","Magik","Loki","Adam Warlock","Luna Snow","Mr. Fantastic"],

    "Punisher": ["Captain America", "Hela", "Hawkeye", "Iron Fist", "Magik", "Cloak & Dagger", "Black Panther", "Storm","Magneto","Moon Knight","Squirrel Girl","Loki"],
    "Hela": ["Punisher", "Magik", "Doctor Strange", "Luna Snow", "Loki","Venom","Captain America","Black Panther","Invisible Woman","Rocket Racoon"],
    "Moon Knight": ["Storm", "Black Panther", "Iron Man", "Spider-Man", "Magneto", "Psylocke", "Magik", "Iron Fist","Venom","Star-Lord","Captain America","Thor","Hulk"],
    "Iron Man": [
        "Doctor Strange", "Iron Fist", "Rocket Racoon", "Namor", "Star-Lord",
        "Punisher", "Psylocke", "Spider-Man", "Black Widow", "Hela", "Hawkeye","Adam Warlock","Mantis","Luna Snow", "Hulk","Scarlet Witch"
    ],
    "Winter Soldier": ["Psylocke", "Hela", "Hawkeye", "Doctor Strange", "Magneto", "Storm","Namor","Iron Fist"],
    "Psylocke": ["Star-Lord", "Scarlet Witch", "Venom", "Invisible Woman", "Namor", "Punisher", "Luna Snow", "Mantis","Captain America","Magneto","Winter Soldier","Rocket Racoon","Loki"],
    "Mr. Fantastic": ["Groot", "Storm", "Punisher", "Iron Man", "Hawkeye", "Hela","Winter Soldier","Black Widow",
                      "Squirrel Girl", "Mantis", "Luna Snow","Adam Warlock","Cloak & Dagger","Jeff","Peni Parker","Scarlet Witch"],
    "Storm": [
        "Doctor Strange", "Punisher", "Hela", "Namor", "Iron Fist", "Psylocke",
        "Black Widow", "Luna Snow", "Rocket Racoon", "Spider-Man", "Star-Lord", "Winter Soldier","Mantis","Invisible Woman","Cloak & Dagger", "Hulk","Scarlet Witch"
    ],
    "Black Panther": [
        "The Thing", "Human Torch", "Star-Lord", "Peni Parker", "Iron Man","Storm", "Namor", "Loki", "Cloak & Dagger", "Magneto",
        "Punisher", "Psylocke", "Mantis","Winter Soldier","Jeff","Adam Warlock","Luna Snow","Rocket Racoon","Scarlet Witch"
    ],
    "Squirrel Girl": ["Groot", "Captain America", "Spider-Man", "Hawkeye", "Black Panther","Storm","Star-Lord","Iron Man","Scarlet Witch","Human Torch","Magneto","Hulk"],
    "Spider-Man": ["Namor", "Iron Fist", "Doctor Strange", "Hela", "Hawkeye", "Luna Snow","Cloak & Dagger","Adam Warlock","Rocket Racoon","Jeff",
                   "Squirrel Girl","Peni Parker","Captain America","Scarlet Witch"],
    "Star-Lord": ["Magneto", "Luna Snow", "Loki", "Doctor Strange", "Hela", "Punisher", "Hawkeye", "Namor","Mantis","Invisible Woman","Hulk","Scarlet Witch"],
    "Wolverine": ["Peni Parker", "Iron Man", "Namor", "Storm", "Invisible Woman", "Captain America", "Spider-Man", "Mantis", "Luna Snow","Magneto","Hela","Adam Warlock","Scarlet Witch"],
    "Hawkeye": ["Psylocke", "Groot", "Spider-Man", "Hela","Doctor Strange","Black Panther","Iron Fist","Rocket Racoon","Loki"],
    "Magik": ["Iron Man", "Namor", "Storm", "Doctor Strange", "Luna Snow","Peni Parker","Magneto","Thor","Winter Soldier","Adam Warlock","Cloak & Dagger","Jeff","Rocket Racoon","Scarlet Witch"],
    "Black Widow": ["Psylocke", "Magik", "Black Panther", "Doctor Strange","Venom","Captain America","Scarlet Witch"],
    "Scarlet Witch": ["Psylocke", "Punisher", "Doctor Strange", "Hawkeye", "Hela","Peni Parker","Mantis","Luna Snow"],
    "Namor": ["Moon Knight", "Hela", "Hawkeye", "Venom","Magneto","Doctor Strange","Punisher","Winter Soldier","Loki","Cloak & Dagger","Invisible Woman","Adam Warlock"],
    "Iron Fist": ["Namor", "Captain America", "Invisible Woman", "Rocket Racoon", "Loki", "Moon Knight", "Storm", "Luna Snow", "Winter Soldier",
                  "Mantis", "Hulk","Peni Parker","Scarlet Witch","Squirrel Girl","Magik","Hela","Adam Warlock"],
    "Human Torch": ["Hela", "Hawkeye", "Punisher", "Psylocke", "Spider-Man", "Luna Snow","Hulk","Scarlet Witch"],

    "Loki": ["Moon Knight", "Iron Man", "Punisher","Winter Soldier","Wolverine","Adam Warlock"],
    "Cloak & Dagger": ["Magneto", "Magik", "Hela", "Hawkeye", "Psylocke","Wolverine","Jeff"],
    "Jeff": ["Iron Man", "Storm", "Spider-Man", "Psylocke","Peni Parker","Squirrel Girl","Magneto", "Hela","Cloak & Dagger"],
    "Mantis": ["Iron Man", "Punisher", "Iron Fist", "Captain America", "Psylocke","Jeff","Magneto", "Hela","Magik","Black Panther"],
    "Luna Snow": ["Iron Man", "Punisher", "Psylocke", "Scarlet Witch", "Captain America", "Loki","Magneto"],
    "Rocket Racoon": ["Star-Lord", "Black Panther", "Iron Man", "Psylocke", "Venom","Magneto","Iron Fist","Captain America"],
    "Invisible Woman": ["Punisher", "Moon Knight", "Squirrel Girl", "Magik", "Spider-Man","Jeff","Iron Man","Magneto","Namor"],
    "Adam Warlock": ["Spider-Man", "Psylocke", "Black Panther","Magneto","Doctor Strange", "Hela","Black Widow","Winter Soldier","Squirrel Girl"],
}