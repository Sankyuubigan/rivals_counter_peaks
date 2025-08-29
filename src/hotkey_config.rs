use global_hotkey::hotkey::{Code, HotKey, Modifiers};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Action {
    RecognizeHeroes,
    ToggleTabMode,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SerializableHotkey {
    pub mods: Vec<String>,
    pub key: String,
}

impl From<&HotKey> for SerializableHotkey {
    fn from(hotkey: &HotKey) -> Self {
        let mut mods_vec = Vec::new();
        
        if hotkey.matches(&Modifiers::CONTROL, &Code::Unidentified) {
            mods_vec.push("control".to_string());
        }
        if hotkey.matches(&Modifiers::SHIFT, &Code::Unidentified) {
            mods_vec.push("shift".to_string());
        }
        if hotkey.matches(&Modifiers::ALT, &Code::Unidentified) {
            mods_vec.push("alt".to_string());
        }
        if hotkey.matches(&Modifiers::SUPER, &Code::Unidentified) {
            mods_vec.push("super".to_string());
        }
        
        let hotkey_debug = format!("{:?}", hotkey);
        let mut key = "KeyX".to_string(); // Значение по умолчанию

        if let Some(key_section) = hotkey_debug.split("key: ").nth(1) {
            if let Some(key_value) = key_section.split(|c| c == ',' || c == '}').next() {
                key = key_value.trim().to_string();
            }
        }
        
        Self {
            mods: mods_vec,
            key,
        }
    }
}

impl TryFrom<&SerializableHotkey> for HotKey {
    type Error = anyhow::Error;
    fn try_from(s_hotkey: &SerializableHotkey) -> Result<Self, Self::Error> {
        let mut mods = Modifiers::empty();
        for m_str in &s_hotkey.mods {
            match m_str.as_str() {
                "control" => mods.insert(Modifiers::CONTROL),
                "shift" => mods.insert(Modifiers::SHIFT),
                "alt" => mods.insert(Modifiers::ALT),
                "super" => mods.insert(Modifiers::SUPER),
                _ => {}
            }
        }
        let key: Code = serde_json::from_str(&format!("\"{}\"", s_hotkey.key))?;
        Ok(HotKey::new(Some(mods), key))
    }
}

#[derive(Debug, Clone)]
pub struct HotkeyInfo {
    pub hotkey: HotKey,
    // description убран, так как он не использовался
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HotkeyConfig {
    #[serde(with = "hashmap_as_vec")]
    pub actions: HashMap<Action, SerializableHotkey>,
}

mod hashmap_as_vec {
    use super::{Action, SerializableHotkey};
    use serde::{de::{self, Deserializer, Visitor}, ser::{SerializeSeq, Serializer}};
    use std::collections::HashMap;
    use std::fmt;
    pub fn serialize<S>(map: &HashMap<Action, SerializableHotkey>, serializer: S) -> Result<S::Ok, S::Error>
    where S: Serializer,
    {
        let mut seq = serializer.serialize_seq(Some(map.len()))?;
        for (k, v) in map { seq.serialize_element(&(k, v))?; }
        seq.end()
    }
    pub fn deserialize<'de, D>(deserializer: D) -> Result<HashMap<Action, SerializableHotkey>, D::Error>
    where D: Deserializer<'de>,
    {
        struct HashMapVisitor;
        impl<'de> Visitor<'de> for HashMapVisitor {
            type Value = HashMap<Action, SerializableHotkey>;
            fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
                formatter.write_str("a sequence of (Action, SerializableHotkey) pairs")
            }
            fn visit_seq<A>(self, mut seq: A) -> Result<Self::Value, A::Error>
            where A: de::SeqAccess<'de>,
            {
                let mut map = HashMap::with_capacity(seq.size_hint().unwrap_or(0));
                while let Some((key, value)) = seq.next_element()? { map.insert(key, value); }
                Ok(map)
            }
        }
        deserializer.deserialize_seq(HashMapVisitor)
    }
}

impl Default for HotkeyConfig {
    fn default() -> Self {
        let mut actions = HashMap::new();
        let default_recognize_hotkey = HotKey::new(Some(Modifiers::CONTROL | Modifiers::SHIFT), Code::KeyX);
        let tab_hotkey = HotKey::new(None, Code::Tab);

        actions.insert(Action::RecognizeHeroes, SerializableHotkey::from(&default_recognize_hotkey));
        actions.insert(Action::ToggleTabMode, SerializableHotkey::from(&tab_hotkey));
        Self { actions }
    }
}

impl HotkeyConfig {
    pub fn get_hotkey_info(&self) -> HashMap<Action, HotkeyInfo> {
        let mut info_map = HashMap::new();
        for (action, s_hotkey) in &self.actions {
            let hotkey = HotKey::try_from(s_hotkey).unwrap_or_else(|_| {
                HotKey::new(Some(Modifiers::CONTROL | Modifiers::SHIFT), Code::KeyX)
            });
            info_map.insert(action.clone(), HotkeyInfo { hotkey });
        }
        info_map
    }
}