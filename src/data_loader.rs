use crate::utils::get_absolute_path_string;
use crate::models::{AllHeroesData, HeroRoles, Role};
use anyhow::{Context, Result};
use std::collections::HashMap;
use std::fs;
pub fn load_matchups_from_json(path: &str) -> Result<AllHeroesData> {
    let absolute_path = get_absolute_path_string(path);
    let data = fs::read_to_string(&absolute_path).with_context(|| format!("Не удалось прочитать файл {}", absolute_path))?;
    let heroes_data: AllHeroesData =
        serde_json::from_str(&data).context("Не удалось распарсить JSON данные")?;
    Ok(heroes_data)
}
pub fn load_roles_from_python_file(path: &str) -> Result<HeroRoles> {
    let absolute_path = get_absolute_path_string(path);
    let content = fs::read_to_string(&absolute_path).with_context(|| format!("Не удалось прочитать файл ролей Python по пути {}", absolute_path))?;
    let mut roles_map = HashMap::new();
    if let Some(dict_content_match) = content.find("hero_roles = {") {
        let start = dict_content_match;
        if let Some(end) = content[start..].find('}') {
            let dict_content = &content[start..start + end];
            let re = regex::Regex::new(r#""(\w+)":\s*\[([^\]]+)\]"#).unwrap();
            for cap in re.captures_iter(dict_content) {
                let role_str = cap.get(1).map_or("", |m| m.as_str());
                let heroes_list_str = cap.get(2).map_or("", |m| m.as_str());
                let role = match role_str {
                    "tank" => Role::Tank,
                    "dd" => Role::Dd,
                    "support" => Role::Support,
                    _ => Role::Unknown,
                };
                if role != Role::Unknown {
                    let heroes: Vec<String> = heroes_list_str
                        .split(',')
                        .map(|s| s.trim().replace('"', ""))
                        .filter(|s| !s.is_empty())
                        .collect();
                    
                    for hero_name in heroes {
                        let name_mapping = match hero_name.as_str() {
                            "Widow" => "Black Widow".to_string(),
                            "Fister" => "Iron Fist".to_string(),
                            "Jeff" => "Jeff The Land Shark".to_string(),
                            "The Punisher" => "Punisher".to_string(),
                            "Winter Soldier" => "Bucky".to_string(),
                            "Mister Fantastic" => "Mr Fantastic".to_string(),
                            "Scarlet Witch" => "Witch".to_string(),
                            "Spider Man" => "SpiderMan".to_string(),
                            _ => hero_name,
                        };
                        roles_map.insert(name_mapping, role);
                    }
                }
            }
        } else {
             return Err(anyhow::anyhow!("Не удалось найти закрывающую скобку '}}' для словаря 'hero_roles'."));
        }
    } else {
        return Err(anyhow::anyhow!("Не удалось найти словарь 'hero_roles' в файле python."));
    }
    if roles_map.is_empty() {
        return Err(anyhow::anyhow!("Не удалось распарсить ни одной роли из файла python. Карта ролей пуста."));
    }
    
    Ok(HeroRoles { roles: roles_map })
}