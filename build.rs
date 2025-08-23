fn main() {
    // Просто собираем ресурсы, без автоматической сборки кастомных операций
    // Иконка будет установлена через Cargo.toml
    println!("cargo:rerun-if-changed=resources/logo.png");
}