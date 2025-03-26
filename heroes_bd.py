# Пример данных о контрпиках (каждый герой имеет список контрпиков из того же списка героев)
heroes_counters = {
    "Hulk": ["Iron Man", "Psylocke", "Storm", "Punisher", "Namor", "Thor", "Peni Parker", "Wolverine", "Mantis",
             "Luna Snow", "Winter Soldier", "Adam Warlock"],
    "Groot": ["Punisher", "Hulk", "Venom", "Storm", "Wolverine", "Iron Man", "Winter Soldier", "Hela", "Cloak & Dagger",
              "Captain America", "Thor", "Rocket Racoon", "Luna Snow", "Mantis", "Invisible Woman", "Psylocke",
              "Star-Lord", "Spider-Man"],
    "Thor": ["Peni Parker", "Iron Man", "Storm", "Wolverine", "Punisher", "Star-Lord", "Scarlet Witch", "Mantis",
             "Psylocke", "Winter Soldier", "Luna Snow",
             "Adam Warlock", "Scarlet Witch", "Namor", "Squirrel Girl"],
    "Doctor Strange": ["Wolverine", "Black Panther", "Venom", "Hulk", "Magik", "Punisher", "Psylocke",
                       "Invisible Woman", "Mantis", "Luna Snow", "Mr. Fantastic"],
    "The Thing": ["Groot", "Iron Man", "Squirrel Girl", "Storm", "Hela", "Adam Warlock", "Scarlet Witch", "Moon Knight",
                  "Doctor Strange", "Star-Lord", "Peni Parker", "Punisher", "Psylocke", "Hawkeye",
                  "Black Widow", "Namor", "Human Torch", "Loki", "Jeff", "Rocket Racoon", "Cloak & Dagger"],
    "Venom": ["Punisher", "Wolverine", "Storm", "Magneto", "Iron Man", "Winter Soldier", "Peni Parker", "Adam Warlock",
              "Scarlet Witch", "Squirrel Girl", "Namor", "Luna Snow", "Mantis", "The Thing"],
    "Peni Parker": ["Iron Man", "Storm", "Punisher", "Star-Lord", "Doctor Strange", "Namor", "Groot", "Loki",
                    "Winter Soldier", "Hela", "Moon Knight", "Psylocke", "Adam Warlock", "Invisible Woman"],
    "Captain America": ["Groot", "Namor", "Hela", "Storm", "Scarlet Witch", "Loki", "Peni Parker", "Iron Man",
                        "Human Torch", "Jeff", "Rocket Racoon", "Adam Warlock", "Scarlet Witch", "The Thing"],
    "Magneto": ["Punisher", "Wolverine", "Venom", "Black Panther", "Storm", "Groot", "Magik", "Loki", "Adam Warlock",
                "Luna Snow", "Mr. Fantastic", "Winter Soldier", "Spider-Man"],

    "Punisher": ["Captain America", "Hela", "Hawkeye", "Iron Fist", "Magik", "Cloak & Dagger", "Black Panther", "Storm",
                 "Magneto", "Moon Knight", "Squirrel Girl", "Loki"],
    "Hela": ["Punisher", "Magik", "Doctor Strange", "Luna Snow", "Loki", "Venom", "Captain America", "Black Panther",
             "Invisible Woman", "Rocket Racoon"],
    "Moon Knight": ["Storm", "Black Panther", "Iron Man", "Spider-Man", "Magneto", "Psylocke", "Magik", "Iron Fist",
                    "Venom", "Star-Lord", "Captain America", "Thor", "Hulk"],
    "Iron Man": [
        "Doctor Strange", "Iron Fist", "Rocket Racoon", "Namor", "Star-Lord",
        "Punisher", "Psylocke", "Spider-Man", "Black Widow", "Hela", "Hawkeye", "Adam Warlock", "Mantis", "Luna Snow",
        "Hulk", "Scarlet Witch"
    ],
    "Winter Soldier": ["Psylocke", "Hela", "Hawkeye", "Doctor Strange", "Magneto", "Storm", "Namor", "Iron Fist"],
    "Psylocke": ["Star-Lord", "Scarlet Witch", "Venom", "Invisible Woman", "Namor", "Punisher", "Luna Snow", "Mantis",
                 "Captain America", "Magneto", "Winter Soldier", "Rocket Racoon", "Loki"],
    "Mr. Fantastic": ["Groot", "Storm", "Punisher", "Iron Man", "Hawkeye", "Hela", "Winter Soldier", "Black Widow",
                      "Squirrel Girl", "Mantis", "Luna Snow", "Adam Warlock", "Cloak & Dagger", "Jeff", "Peni Parker",
                      "Scarlet Witch"],
    "Storm": [
        "Doctor Strange", "Punisher", "Hela", "Namor", "Iron Fist", "Psylocke",
        "Black Widow", "Luna Snow", "Rocket Racoon", "Spider-Man", "Star-Lord", "Winter Soldier", "Mantis",
        "Invisible Woman", "Cloak & Dagger", "Hulk", "Scarlet Witch"
    ],
    "Black Panther": [
        "The Thing", "Human Torch", "Star-Lord", "Peni Parker", "Iron Man", "Storm", "Namor", "Loki", "Cloak & Dagger",
        "Magneto",
        "Punisher", "Psylocke", "Mantis", "Winter Soldier", "Jeff", "Adam Warlock", "Luna Snow", "Rocket Racoon",
        "Scarlet Witch"
    ],
    "Squirrel Girl": ["Groot", "Captain America", "Spider-Man", "Hawkeye", "Black Panther", "Storm", "Star-Lord",
                      "Iron Man", "Scarlet Witch", "Human Torch", "Magneto", "Hulk"],
    "Spider-Man": ["Namor", "Iron Fist", "Doctor Strange", "Hela", "Hawkeye", "Luna Snow", "Cloak & Dagger",
                   "Adam Warlock", "Rocket Racoon", "Jeff",
                   "Squirrel Girl", "Peni Parker", "Captain America", "Scarlet Witch", "Winter Soldier"],
    "Star-Lord": ["Magneto", "Luna Snow", "Loki", "Doctor Strange", "Hela", "Punisher", "Hawkeye", "Namor", "Mantis",
                  "Invisible Woman", "Hulk", "Scarlet Witch"],
    "Wolverine": ["Peni Parker", "Iron Man", "Namor", "Storm", "Invisible Woman", "Captain America", "Spider-Man",
                  "Mantis", "Luna Snow", "Magneto", "Hela", "Adam Warlock", "Scarlet Witch", "The Thing"],
    "Hawkeye": ["Psylocke", "Groot", "Spider-Man", "Hela", "Doctor Strange", "Black Panther", "Iron Fist",
                "Rocket Racoon", "Loki"],
    "Magik": ["Iron Man", "Namor", "Storm", "Doctor Strange", "Luna Snow", "Peni Parker", "Magneto", "Thor",
              "Winter Soldier", "Adam Warlock", "Cloak & Dagger", "Jeff", "Rocket Racoon", "Scarlet Witch"],
    "Black Widow": ["Psylocke", "Magik", "Black Panther", "Doctor Strange", "Venom", "Captain America",
                    "Scarlet Witch"],
    "Scarlet Witch": ["Psylocke", "Punisher", "Doctor Strange", "Hawkeye", "Hela", "Peni Parker", "Mantis",
                      "Luna Snow"],
    "Namor": ["Moon Knight", "Hela", "Hawkeye", "Venom", "Magneto", "Doctor Strange", "Punisher", "Winter Soldier",
              "Loki", "Cloak & Dagger", "Invisible Woman", "Adam Warlock"],
    "Iron Fist": ["Namor", "Captain America", "Invisible Woman", "Rocket Racoon", "Loki", "Moon Knight", "Storm",
                  "Luna Snow", "Winter Soldier", "Punisher", "Mantis", "Hulk", "Peni Parker", "Scarlet Witch",
                  "Squirrel Girl", "Magik", "Hela", "Adam Warlock"],
    "Human Torch": ["Hela", "Hawkeye", "Punisher", "Psylocke", "Spider-Man", "Luna Snow", "Hulk", "Scarlet Witch"],

    "Loki": ["Moon Knight", "Iron Man", "Punisher", "Winter Soldier", "Wolverine", "Adam Warlock", "Spider-Man",
             "Mr. Fantastic", "Captain America", "Thor", "The Thing", "Storm", "Hela", "Jeff","Moon Knight"],
    "Cloak & Dagger": ["Magneto", "Magik", "Hela", "Hawkeye", "Psylocke", "Wolverine", "Jeff", "Squirrel Girl",
                       "Moon Knight", "Rocket Racoon"],
    "Jeff": ["Iron Man", "Storm", "Spider-Man", "Psylocke", "Peni Parker", "Squirrel Girl", "Magneto", "Hela",
             "Cloak & Dagger", "Iron Fist", "Luna Snow", "Mantis", "The Thing", "Namor"],  # подбрасывание
    "Mantis": ["Iron Man", "Punisher", "Iron Fist", "Captain America", "Psylocke", "Jeff", "Magneto", "Hela", "Magik",
               "Black Panther", "Moon Knight", "Squirrel Girl", "The Thing", "Wolverine", "Star-Lord", "Rocket Racoon","Storm"],
    "Luna Snow": ["Iron Man", "Punisher", "Psylocke", "Scarlet Witch", "Captain America", "Loki", "Magneto",
                  "The Thing", "Magik", "Spider-Man", "Black Panther", "Mr. Fantastic", "Moon Knight", "Venom", "Thor",
                  "Hulk", "Rocket Racoon","Storm"],
    "Rocket Racoon": ["Star-Lord", "Black Panther", "Iron Man", "Psylocke", "Venom", "Magneto", "Iron Fist",
                      "Captain America", "Punisher", "Wolverine","Storm"],
    "Invisible Woman": ["Punisher", "Moon Knight", "Squirrel Girl", "Magik", "Spider-Man", "Jeff", "Iron Man",
                        "Magneto", "Namor", "The Thing", "Rocket Racoon", "Mr. Fantastic","Storm"],
    "Adam Warlock": ["Spider-Man", "Psylocke", "Black Panther", "Magneto", "Doctor Strange", "Hela", "Black Widow",
                     "Winter Soldier", "Squirrel Girl","Storm"],
}

heroes = [
    "Hulk", "Groot", "Thor", "Doctor Strange", "The Thing", "Venom", "Peni Parker", "Captain America", "Magneto",
    "Punisher", "Hela", "Moon Knight",
    "Iron Man", "Winter Soldier", "Psylocke", "Mr. Fantastic", "Storm", "Black Panther", "Squirrel Girl",
    "Spider-Man", "Star-Lord", "Wolverine", "Hawkeye", "Magik", "Black Widow", "Scarlet Witch", "Namor",
    "Iron Fist", "Human Torch", "Loki", "Cloak & Dagger", "Jeff", "Mantis", "Luna Snow",
    "Rocket Racoon", "Invisible Woman", "Adam Warlock",
]

futures = ["Quicksilver", "Doctor Doom", "Cyclops", "Jean Grey", "Rogue", "Gambit", "Beast", "Iceman", "Colossus",
           "Nightcrawler",
           "Shadowcat", "Cable", "Deadpool", "Emma Frost", "Juggernaut", "Mystique", "Sabretooth",
           "Silver Surfer", "Vision", ]




heroes_compositions = {
    "Hulk": [],
    "Groot": ["Invisible Woman", "Jeff", "Cloak & Dagger", "Luna Snow"],
    "Thor": ["Hela", "Doctor Strange", "Magneto"],
    "Doctor Strange": ["Hulk"],
    "The Thing": ["Invisible Woman", "Mr. Fantastic", "Captain America", "Thor", "Hulk", "Venom", "Doctor Strange",
                  "Cloak & Dagger", "Jeff", "Magneto"],
    "Venom": [],
    "Peni Parker": ["Venom", "Groot", "Luna Snow", "Invisible Woman", "Cloak & Dagger"],
    "Captain America": ["Thor"],
    "Magneto": ["Scarlet Witch"],

    "Punisher": ["Doctor Strange", "Rocket Racoon"],
    "Hela": [],
    "Moon Knight": ["Cloak & Dagger"],
    "Iron Man": ["Hulk"],  # дайверы и фланкеры?
    "Winter Soldier": ["Rocket Racoon"],
    "Psylocke": ["Doctor Strange", "Magik"],
    "Mr. Fantastic": ["Invisible Woman", "Captain America", "Thor", "Hulk", "Venom", "Doctor Strange", "The Thing"],
    "Storm": ["Thor", "Invisible Woman", "Human Torch"],
    "Black Panther": ["Magik"],
    "Squirrel Girl": ["Spider-Man"],
    "Spider-Man": ["Venom"],
    "Star-Lord": ["Adam Warlock"],
    "Wolverine": ["Hulk", "The Thing"],
    "Hawkeye": [],
    "Magik": [],
    "Black Widow": ["Hawkeye"],
    "Scarlet Witch": [],
    "Namor": ["Luna Snow"],
    "Iron Fist": [],
    "Human Torch": ["Invisible Woman"],

    "Loki": ["Hela"],
    "Cloak & Dagger": [],
    "Jeff": ["Luna Snow"],
    "Mantis": ["Captain America", "Adam Warlock"],
    "Luna Snow": ["Hulk", "The Thing", "Groot", "Iron Fist"],
    "Rocket Racoon": ["Captain America"],
    "Invisible Woman": [],
    "Adam Warlock": [],
}


вот код моей программы прикрепил. я бы хотел добавить функционал. нужно поменять местами левую и правую области в программе, так чтобы выбор героев противников был справа а не слева.
В области где рейтинг героев выводится и их баллы, иконки справа (которые меньшего размера) которые контрит данный герой, нужно этим иконкам сделать толстую рамку зеленого цвета.
и затем после них такого же размера продолжить список иконок героев но уже в рамке красного цвета (это будут те герои, которые контрят данного героя и являются выбранными героями
вражеской команды, то есть за них как раз высчитываются сейчас баллы при подсчете).
также нужно в файле heroes_bd определить роли персонажей. ["Hulk", "Groot", "Thor", "Doctor Strange", "The Thing", "Venom", "Peni Parker", "Captain America", "Magneto"] - это танки то есть упитанные.
["Punisher", "Hela", "Moon Knight",
    "Iron Man", "Winter Soldier", "Psylocke", "Mr. Fantastic", "Storm", "Black Panther", "Squirrel Girl",
    "Spider-Man", "Star-Lord", "Wolverine", "Hawkeye", "Magik", "Black Widow", "Scarlet Witch", "Namor",
    "Iron Fist", "Human Torch"] - это атакующие персонажи.
["Loki", "Cloak & Dagger", "Jeff", "Mantis", "Luna Snow",
    "Rocket Racoon", "Invisible Woman", "Adam Warlock"] - а это саппорты то есть те кто лечат.
эти роли нужны для того чтобы программа автоматически по рейтингу составляла наиболее удачный состав команды против выбранной вражеской команды
(можно назвать такой состав "эффективной командой сопротивления"), учитывая все факторы,
такие как контр пики и удачные тим апы.
в списке heroes_compositions находятся удачные тим апы по аналогии с контр пиками. то есть возможные желательные герои для конкретного героя.
при составлении эффективной команды сопротивления должно соблюдаться правило: минимум 1 танк, минимум 1 хиллер и максимум 3 хиллера. желательно 2 танка и 2 хиллера,
потому что чаще всего это более стабильно. команда должна состоять из 6 героев. нужно набирать в эффективную команду сопротивления героев с максимальным количеством баллов, чтобы команда набрала как можно больше баллов в сумме по итогу,
но при этом предпочтительно комбинировать героев по списку heroes_compositions, возможно стоит как то накидывать баллы сверху за удачные связки (например по пол балла), но их лучше учитывать лишь при составлении
эффективной команды сопротивления, то есть нынешний подсчет баллов в списке рейтинга героев должен остаться как есть и отображаться без изменений.
результат нужно выводить всё в той же области рейтинга, где сейчас и выводятся баллы, просто давай обводить толстой рамкой синего цвета всю строчку в этом рейтинге,
если данный герой выбран в качестве эффективной команды сопротивления.
теперь кнопка "копировать рейтинг" должна копировать не весь рейтинг а лишь эффективную команду сопротивления.
также давай в верхнюю панель добавим кнопку, по которой отображается окно со списком рейтинга всех героев, где в самом низу будут герои с наибольшим количеством контр пиков,
а в самом верху будут герои с наименьшим количеством контр пиков. и после имени в скобках будет указано количество. эту кнопку можно назвать "Рейтинг героев".
в этом окне заголовок такой будет "Рейтинг наименее контрящихся персонажей".
