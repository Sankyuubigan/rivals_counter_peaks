use anyhow::Result;
use image::{imageops, DynamicImage, GenericImageView, ImageBuffer, Rgba, RgbaImage};
use ndarray::{Array4};
use crate::utils::Rect;
const TARGET_SIZE: u32 = 224;
pub fn preprocess_image_batch(rois: &[(RgbaImage, Rect)]) -> Result<Array4<f32>> {
    let mut tensors = Vec::new();
    for (roi, _) in rois {
        let dynamic_img = DynamicImage::ImageRgba8(roi.clone());
        // Используем метод crop_to_target_size как в Python-скрипте
        let processed_img = crop_image_to_target_size(dynamic_img);
        // Преобразуем DynamicImage в RgbaImage для передачи в image_to_tensor
        let rgba_img = processed_img.to_rgba8();
        let tensor = image_to_tensor(&rgba_img);
        tensors.push(tensor);
    }
    let views: Vec<_> = tensors.iter().map(|t| t.view()).collect();
    Ok(ndarray::concatenate(ndarray::Axis(0), &views)?)
}
// Аналог функции crop_image_to_target_size из Python-скрипта
fn crop_image_to_target_size(image: DynamicImage) -> DynamicImage {
    // Предобработка изображения - улучшение качества
    let img_pil_preprocessed = enhance_image(image);
    
    // Resize до кратного размера
    let (width, height) = img_pil_preprocessed.dimensions();
    let (new_width, new_height) = if width < height {
        (256, (height * 256 / width))
    } else {
        ((width * 256 / height), 256)
    };
    
    let img_resized = img_pil_preprocessed.resize(new_width, new_height, imageops::FilterType::Lanczos3);
    
    // Center crop
    let left = (new_width - TARGET_SIZE) / 2;
    let top = (new_height - TARGET_SIZE) / 2;
    
    img_resized.crop_imm(left, top, TARGET_SIZE, TARGET_SIZE)
}
// Улучшение качества изображения как в Python-скрипте
fn enhance_image(image: DynamicImage) -> DynamicImage {
    let mut image = image;
    
    // Улучшаем контрастность
    image = image.adjust_contrast(1.5);
    
    // Улучшаем резкость с использованием правильного метода
    // Второй параметр должен быть i32, а не f32
    image = image.unsharpen(1.2, 1);
    
    // Небольшая коррекция яркости
    image = image.brighten(10);
    
    image
}
// Старая функция для паддинга, оставлена как запасной вариант
fn pad_to_square(img: DynamicImage) -> DynamicImage {
    let (width, height) = img.dimensions();
    if width == height { return img; }
    let max_dim = width.max(height);
    let mut square_img = DynamicImage::new_rgba8(max_dim, max_dim);
    let paste_x = (max_dim - width) / 2;
    let paste_y = (max_dim - height) / 2;
    imageops::overlay(&mut square_img, &img, paste_x as i64, paste_y as i64);
    square_img
}
fn image_to_tensor(img: &ImageBuffer<Rgba<u8>, Vec<u8>>) -> Array4<f32> {
    let height = img.height() as usize;
    let width = img.width() as usize;
    let mut tensor = Array4::<f32>::zeros((1, 3, height, width));
    
    // Используем те же параметры нормализации, что и в Python-скрипте
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