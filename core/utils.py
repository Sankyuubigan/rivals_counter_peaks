# File: core/utils.py
import os
import sys
from core.database.heroes_bd import heroes_counters, heroes 
import logging
import re

def _get_root_path():
    if hasattr(sys, '_MEIPASS'): 
        return sys._MEIPASS
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def resource_path(relative_path):
    base_path = _get_root_path()
    return os.path.join(base_path, relative_path.replace('/', os.sep))

def normalize_hero_name(name: str) -> str:
    if not name: return ""
    
    normalized = name.lower()
    normalized = re.sub(r'[_ ]*v\d+$', '', normalized)
    normalized = re.sub(r'_\d+$', '', normalized)
    
    suffixes =["_icon", "_template", "_small", "_left", "_right", "_horizontal", "_adv", "_padded"]
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
            
    normalized = re.sub(r'[-_]+', ' ', normalized).strip()
    for hero_canonical in heroes:
        if hero_canonical.lower() == normalized:
            return hero_canonical
            
    capitalized_attempt = " ".join(p.capitalize() for p in normalized.split(' ') if p)
    for hero_canonical in heroes:
        if hero_canonical == capitalized_attempt:
            return hero_canonical
    
    final_name = capitalized_attempt if capitalized_attempt else name 
    return final_name

def validate_heroes():
    logging.info("[VALIDATION] Validating hero data structures...")
    errors =[]
    heroes_set = set(heroes) 
    for hero, counters in heroes_counters.items():
        if hero not in heroes_set:
            errors.append(f"Unknown hero '{hero}' as key in heroes_counters.")
            continue 
        if not isinstance(counters, dict):
            errors.append(f"Invalid data for '{hero}': expected dict, got {type(counters)}.")
            continue
        for counter_type in ["hard", "soft"]:
            if counter_type in counters:
                if not isinstance(counters[counter_type], list):
                    errors.append(f"For '{hero}' -> '{counter_type}', expected list, got {type(counters[counter_type])}.")
                    continue
                for counter_hero in counters[counter_type]:
                    if counter_hero not in heroes_set:
                        errors.append(f"Unknown hero '{counter_hero}' in '{counter_type}' list for '{hero}'.")
    
    unique_errors = sorted(list(set(errors)))
    if unique_errors:
        logging.error(f"[VALIDATION FAILED] Found errors:\n" + "\n".join(unique_errors))
    else:
        logging.info("[VALIDATION] Validation successful.")
    return unique_errors