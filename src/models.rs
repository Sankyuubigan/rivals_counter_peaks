use serde::Deserialize;
use std::collections::HashMap;

#[derive(Deserialize, Debug, Clone)]
pub struct OpponentStats {
    pub opponent: String,
    #[serde(rename = "win_rate")]
    pub win_rate: String,
    pub difference: String,
    pub matches: String,
}

#[derive(Deserialize, Debug, Clone)]
pub struct HeroData {
    #[serde(rename = "win_rate")]
    pub win_rate: String,
    #[serde(rename = "pick_rate")]
    pub pick_rate: String,
    pub matches: String,
    pub opponents: Vec<OpponentStats>,
    // tier, ban_rate, role из JSON игнорируются, так как они не используются в логике
}

pub type AllHeroesData = HashMap<String, HeroData>;

#[derive(Debug, PartialEq, Eq, Hash, Clone, Copy)]
pub enum Role {
    Tank,
    Dd, // Damage Dealer
    Support,
    Unknown,
}

#[derive(Debug, Default)]
pub struct HeroRoles {
    pub roles: HashMap<String, Role>,
}