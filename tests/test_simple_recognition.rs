use anyhow::Result;
use image::io::Reader as ImageReader;
use std::fs;
use std::path::Path;
use rust_rivals::recognition::simple_recognition_engine::SimpleRecognitionEngine;

#[tokio::test]
async fn test_simple_recognition_engine() -> Result<()> {
    println!("=== ТЕСТИРОВАНИЕ ПРОСТОГО ДВИЖКА РАСПОЗНАВАНИЯ ===");

    // Инициализация движка
    let mut engine = SimpleRecognitionEngine::new()?;
    println!("✓ Движок успешно инициализирован");

    // Тестирование на всех доступных скриншотах
    let screenshots_dir = Path::new("tests/for_recogn/screenshots");
    let mut total_time = std::time::Duration::new(0, 0);

    for i in 1..=7 {
        let screenshot_path = screenshots_dir.join(format!("{}.png", i));
        if !screenshot_path.exists() {
            println!("Скриншот {}.png не найден, пропуск", i);
            continue;
        }

        println!("\n--- ТЕСТИРОВАНИЕ СКРИНШОТА {} ---", i);

        // Загрузка изображения
        let img = ImageReader::open(&screenshot_path)?
            .decode()?
            .to_rgba8();

        // Замер времени
        let start_time = std::time::Instant::now();
        let result = engine.recognize_heroes(&img).await?;
        let elapsed = start_time.elapsed();

        total_time += elapsed;

        println!("Результат: {:?}", result);
        println!("Время: {:.3} сек", elapsed.as_secs_f32());
        println!("Количество героев: {}", result.len());
    }

    // Вывод сводной статистики
    let avg_time = total_time / 7;
    println!("\n=== СВОДНАЯ СТАТИСТИКА ===");
    println!("Общее время: {:.3} сек", total_time.as_secs_f32());
    println!("Среднее время на скриншот: {:.3} сек", avg_time.as_secs_f32());

    Ok(())
}

#[test]
fn test_recognition_engine_creation() -> Result<()> {
    println!("=== ТЕСТ СОЗДАНИЯ ДВИЖКА РАСПОЗНАВАНИЯ ===");

    let engine = SimpleRecognitionEngine::new()?;
    println!("✓ Движок успешно создан");

    // Проверяем, что движок инициализирован корректно
    // (Здесь можно добавить дополнительные проверки)

    Ok(())
}