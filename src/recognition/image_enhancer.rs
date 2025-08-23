use image::{DynamicImage, GenericImageView, imageops};
use image::imageops::FilterType;
/// Улучшение качества изображения, аналогичное функции enhance_image из Python-скрипта
/// Применяет нерезкое маскирование для улучшения деталей
pub fn enhance_image(image: DynamicImage) -> DynamicImage {
    let mut image = image;
    
    // В Python-версии используется UnsharpMask с параметрами (radius=1, percent=120, threshold=3)
    // В Rust метод unsharpen имеет сигнатуру unsharpen(sigma: f32, threshold: i32)
    // sigma примерно соответствует radius, а threshold - threshold из Python
    // Для percent=120 в Python используем sigma=1.2 в Rust
    
    // Применяем нерезкое маскирование как в Python
    image = image.unsharpen(1.0, 3);
    
    image
}
/// Обрезка изображения до целевого размера с сохранением пропорций
/// Аналогично crop_image_to_target_size из Python
pub fn crop_to_target_size(image: DynamicImage, target_size: u32) -> DynamicImage {
    // Предобработка изображения
    let img_pil_preprocessed = enhance_image(image);
    
    // Resize до кратного размера (256 для DINOv2)
    let (width, height) = img_pil_preprocessed.dimensions();
    let (new_width, new_height) = if width < height {
        (target_size, (height * target_size / width))
    } else {
        ((width * target_size / height), target_size)
    };
    
    let img_resized = img_pil_preprocessed.resize(new_width, new_height, FilterType::Lanczos3);
    
    // Center crop
    let left = (new_width - target_size) / 2;
    let top = (new_height - target_size) / 2;
    
    img_resized.crop_imm(left, top, target_size, target_size)
}
/// Добавление отступов до целевого размера
/// Аналогично pad_image_to_target_size из Python
pub fn pad_to_target_size(image: DynamicImage, target_size: u32, _padding_color: [u8; 3]) -> DynamicImage {
    let (width, height) = image.dimensions();
    
    if width == target_size && height == target_size {
        return image;
    }
    
    // Рассчитываем новые размеры с сохранением пропорций
    let target_aspect = target_size as f32 / target_size as f32;
    let original_aspect = width as f32 / height as f32;
    
    let (new_width, new_height) = if original_aspect > target_aspect { 
        (target_size, (target_size as f32 / original_aspect) as u32)
    } else { 
        ((target_size as f32 * original_aspect) as u32, target_size)
    };
        
    if new_width == 0 || new_height == 0 {
        return DynamicImage::new_rgb8(target_size, target_size);
    }
        
    let resized_image = image.resize(new_width, new_height, FilterType::Lanczos3);
    
    // Центрируем изображение
    let mut padded_image = DynamicImage::new_rgb8(target_size, target_size);
    let paste_x = (target_size - new_width) / 2;
    let paste_y = (target_size - new_height) / 2;
    
    imageops::overlay(&mut padded_image, &resized_image, paste_x as i64, paste_y as i64);
    
    padded_image
}