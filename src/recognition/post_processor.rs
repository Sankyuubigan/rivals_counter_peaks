use crate::utils::Rect;
const NMS_IOU_THRESHOLD: f32 = 0.4;
#[derive(Debug, Clone)]
pub struct Detection {
    pub name: String,
    pub score: f32,
    pub rect: Rect,
}
/// Фильтрует предварительные результаты с помощью Non-Maximum Suppression.
pub fn non_maximum_suppression(mut detections: Vec<Detection>) -> Vec<String> {
    // 1. Сортируем все обнаружения по убыванию уверенности (score)
    detections.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
    let mut final_detections = Vec::new();
    while !detections.is_empty() {
        // 2. Берем лучшее из оставшихся обнаружений
        let best_detection = detections.remove(0);
        // 3. Добавляем его в итоговый список
        final_detections.push(best_detection.clone());
        // 4. Удаляем все остальные обнаружения, которые сильно пересекаются с лучшим
        detections.retain(|other_detection| {
            // Не удаляем обнаружения других героев
            if other_detection.name != best_detection.name {
                return true;
            }
            // Вычисляем IoU и удаляем, если оно выше порога
            let iou = best_detection.rect.iou(&other_detection.rect);
            iou < NMS_IOU_THRESHOLD
        });
    }
    // Возвращаем только имена уникальных героев
    final_detections.into_iter().map(|d| d.name).collect()
}