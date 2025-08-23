use anyhow::Result;
use image::{DynamicImage, ImageBuffer, Rgba, RgbaImage};
use ndarray::{Array4};
use crate::utils::Rect;
use crate::recognition::image_enhancer::crop_to_target_size;
const TARGET_SIZE: u32 = 224;
/// Предобработка изображения для модели DINOv3
/// Применяет улучшение качества и нормализацию как в Python-скрипте
pub fn preprocess_image_batch(rois: &[(RgbaImage, Rect)]) -> Result<Array4<f32>> {
    let mut tensors = Vec::new();
    for (roi, _) in rois {
        let dynamic_img = DynamicImage::ImageRgba8(roi.clone());
        // Используем метод crop_to_target_size как в Python-скрипте
        let processed_img = crop_to_target_size(dynamic_img, TARGET_SIZE);
        // Преобразуем DynamicImage в RgbaImage для передачи в image_to_tensor
        let rgba_img = processed_img.to_rgba8();
        let tensor = image_to_tensor(&rgba_img);
        tensors.push(tensor);
    }
    let views: Vec<_> = tensors.iter().map(|t| t.view()).collect();
    Ok(ndarray::concatenate(ndarray::Axis(0), &views)?)
}
/// Преобразование изображения в тензор с нормализацией
/// Использует те же параметры нормализации, что и в Python-скрипте
fn image_to_tensor(img: &ImageBuffer<Rgba<u8>, Vec<u8>>) -> Array4<f32> {
    let height = img.height() as usize;
    let width = img.width() as usize;
    let mut tensor = Array4::<f32>::zeros((1, 3, height, width));
    
    // Параметры нормализации для DINOv2
    let mean = [0.485, 0.456, 0.406];
    let std = [0.229, 0.224, 0.225];
    
    for (x, y, pixel) in img.enumerate_pixels() {
        let [r, g, b, _] = pixel.0;
        tensor[[0, 0, y as usize, x as usize]] = (r as f32 / 255.0 - mean[0]) / std[0];
        tensor[[0, 1, y as usize, x as usize]] = (g as f32 / 255.0 - mean[1]) / std[1];
        tensor[[0, 2, y as usize, x as usize]] = (b as f32 / 255.0 - mean[2]) / std[2];
    }
    tensor
}