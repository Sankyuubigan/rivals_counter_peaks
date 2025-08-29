use serde::Deserialize;
use std::collections::HashMap;

#[derive(Deserialize, Debug, Clone)]
pub struct OpponentStats {
    pub opponent: String,
    // win_rate и matches не используются, убираем их, чтобы избавиться от предупреждений
    // pub win_rate: String,
    pub difference: String,
    // pub matches: String,
}

#[derive(Deserialize, Debug, Clone)]
pub struct HeroData {
    #[serde(rename = "win_rate")]
    pub win_rate: String,
    // pick_rate и matches не используются
    // #[serde(rename = "pick_rate")]
    // pub pick_rate: String,
    // pub matches: String,
    pub opponents: Vec<OpponentStats>,
}

pub type AllHeroesData = HashMap<String, HeroData>;

#[derive(Debug, PartialEq, Eq, Hash, Clone, Copy)]
pub enum Role {
    Tank,
    Dd, // Damage Dealer
    Support,
    Unknown,
}

#[derive(Debug, Default, Clone)]
pub struct HeroRoles {
    pub roles: HashMap<String, Role>,
}