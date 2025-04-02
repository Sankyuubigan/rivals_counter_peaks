from heroes_bd import heroes_counters, heroes

def validate_heroes():
    invalid_heroes = []
    for hero, counters in heroes_counters.items():
        if hero not in heroes:
            invalid_heroes.append(hero)
        for counter in counters:
            if counter not in heroes:
                invalid_heroes.append(counter)

    if invalid_heroes:
        error_message = f"Ошибка: В hero_counters найдены герои, которых нет в списке heroes:\n{', '.join(set(invalid_heroes))}"
        print(error_message)