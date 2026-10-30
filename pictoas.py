import os
import math
from PIL import Image, ImageOps, ImageEnhance, ImageDraw, ImageFont

# Включаем поддержку ANSI-цветов в стандартном CMD Windows
os.system("")

# Палитра от темного к яркому
ASCII_CHARS = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"

def get_aspect_ratio_str(width, height):
    """Автоматически вычисляет и возвращает красивое соотношение сторон (например, 16:9, 4:3, 1:1)"""
    gcd = math.gcd(width, height)
    rw = width // gcd
    rh = height // gcd
    
    # Если числа получились слишком большими (нестандартная обрезка), показываем отношение к 1
    if rw > 50 or rh > 50:
        return f"~{width/height:.2f}:1"
    return f"{rw}:{rh}"

def resize_keep_aspect(image, target_width, is_square_pixel=True):
    """
    Универсальное сжатие с идеальным сохранением пропорций исходного фото.
    Если is_square_pixel=True (для двойных символов '@@' или '██'), пропорции пикселей 1:1.
    Если False (для одиночных символов в консоли), высота компенсируется на 0.55 из-за вытянутости шрифта.
    """
    orig_w, orig_h = image.size
    if target_width >= orig_w and is_square_pixel:
        return image
        
    # Вычисляем точную высоту по формуле пропорции: H_new = H_orig * (W_new / W_orig)
    scale_factor = target_width / orig_w
    font_correction = 1.0 if is_square_pixel else 0.55
    
    new_h = max(1, int(round(orig_h * scale_factor * font_correction)))
    # Используем LANCZOS для максимально четкого сжатия без мыла
    return image.resize((target_width, new_h), Image.Resampling.LANCZOS)

def adjust_image_size(image, mode="1"):
    """Изменяет размер в зависимости от выбранного режима"""
    orig_w, orig_h = image.size
    
    if mode in ["2", "4", "5"]:
        # Для попиксельных режимов спрашиваем, нужно ли пропорционально сжать, если картинка огромная
        if orig_w > 120:
            ratio_str = get_aspect_ratio_str(orig_w, orig_h)
            print(f"\n[!] Исходная картинка большая ({orig_w}x{orig_h}, пропорции {ratio_str}).")
            custom_w = input("Введите желаемую ширину для пропорционального сжатия (или Enter для 100% оригинала): ").strip()
            if custom_w.isdigit() and int(custom_w) > 0:
                new_w = int(custom_w)
                resized = resize_keep_aspect(image, new_w, is_square_pixel=True)
                rw, rh = resized.size
                print(f"-> Пропорции {ratio_str} сохранены! Новое разрешение сетки: {rw}x{rh}")
                return resized
        return image
    elif mode == "3":
        # Оригинальная ширина, но скорректированная под одиночный шрифт высота
        return resize_keep_aspect(image, orig_w, is_square_pixel=False)
    else:
        # Стандартный режим 1 (сжатие до 120 символов с сохранением визуальных пропорций на экране)
        return resize_keep_aspect(image, 120, is_square_pixel=False)

def prepare_pixels(image):
    """Готовит цветные и ЧБ пиксели из картинки"""
    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        rgba_img = image.convert('RGBA')
        bg = Image.new('RGB', image.size, (0, 0, 0))
        # Берем 4-й канал (альфа-маску) с индексом 3
        bg.paste(rgba_img, mask=rgba_img.split()[3])
        image = bg
    else:
        image = image.convert('RGB')

    # 1. Цветная версия (делаем цвета сочнее)
    color_img = ImageEnhance.Color(image).enhance(1.3)
    color_img = ImageEnhance.Brightness(color_img).enhance(1.1)
    rgb_pixels = list(color_img.getdata())

    # 2. ЧБ-версия для выбора символов по яркости
    gray_img = image.convert("L")
    gray_img = ImageOps.autocontrast(gray_img, cutoff=2)
    gray_img = ImageEnhance.Contrast(gray_img).enhance(1.5)
    gray_img = ImageEnhance.Sharpness(gray_img).enhance(2.0)
    gray_pixels = list(gray_img.getdata())

    return rgb_pixels, gray_pixels

def save_ascii_as_png(image, original_path, use_blocks=False):
    """Рисует цветной ASCII-арт или блочный пиксель-арт на новом PNG-холсте со 100% сохранением пропорций"""
    orig_w, orig_h = image.size
    ratio_str = get_aspect_ratio_str(orig_w, orig_h)
    
    print(f"\nИсходник: {orig_w}x{orig_h} (Соотношение сторон: {ratio_str})")
    
    # Предлагаем выбрать ширину в "символьных пикселях" с автоматическим подсчетом высоты по пропорции
    default_w = min(orig_w, 320)
    default_h = int(round(orig_h * (default_w / orig_w)))
    
    user_w = input(
        f"Введите ширину в пикселях-символах (Enter для {default_w}x{default_h} [{ratio_str}] или '0' для {orig_w}x{orig_h}): "
    ).strip()
    
    if user_w == "0":
        target_w = orig_w
    elif user_w.isdigit() and int(user_w) > 0:
        target_w = int(user_w)
    else:
        target_w = default_w

    # Сжимаем строго по формуле пропорций оригинала
    image = resize_keep_aspect(image, target_w, is_square_pixel=True)
    work_w, work_h = image.size
    new_ratio_str = get_aspect_ratio_str(work_w, work_h)
    print(f"-> Размер сетки символов: {work_w}x{work_h} (Пропорции: {new_ratio_str})")

    rgb_pixels, gray_pixels = prepare_pixels(image)
    num_chars = len(ASCII_CHARS)

    # Загружаем моноширинный шрифт Windows
    font_size = 12
    try:
        font = ImageFont.truetype("consola.ttf", font_size)
    except IOError:
        try:
            font = ImageFont.truetype("cour.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()

    # Вычисляем размер квадратной ячейки по двум символам (getbbox возвращает [left, top, right, bottom])
    sample_chars = "██" if use_blocks else "@@"
    bbox = font.getbbox(sample_chars)
    text_w = bbox[2] - bbox[0]
    cell_size = max(text_w, font_size)

    out_w = work_w * cell_size
    out_h = work_h * cell_size
    out_ratio_str = get_aspect_ratio_str(out_w, out_h)

    mode_label = "блоками '██'" if use_blocks else "буквами '@@'"
    print(f"Генерация PNG-холста ({mode_label}): {out_w}x{out_h} пикс. (Пропорции {out_ratio_str}). Подождите...")

    # Создаем черный холст
    out_img = Image.new("RGB", (out_w, out_h), (0, 0, 0))
    draw = ImageDraw.Draw(out_img)

    # Отрисовываем каждый пиксель в строго квадратной ячейке
    for i in range(len(rgb_pixels)):
        r, g, b = rgb_pixels[i]
        brightness = gray_pixels[i]
        
        if use_blocks:
            # Для сплошных блоков пропускаем только абсолютно черные пиксели RGB
            if r == 0 and g == 0 and b == 0:
                continue
            char = "██"
        else:
            if brightness == 0:
                continue
            char = ASCII_CHARS[int(brightness / 256 * num_chars)] * 2
        
        col = i % work_w
        row = i // work_w
        
        x = col * cell_size
        y = row * cell_size
        
        draw.text((x, y), char, fill=(r, g, b), font=font)

    base_name, _ = os.path.splitext(original_path)
    suffix = "blocks" if use_blocks else "ascii"
    out_path = f"{base_name}_{suffix}_{work_w}x{work_h}.png"
    out_img.save(out_path)
    
    print(f"✅ Готово! Картинка сохранена по пути:\n{out_path}")
    
    try:
        os.startfile(out_path)
    except Exception:
        pass

def image_to_color_ascii(image, mode="1"):
    """Создает цветной ASCII-арт или пиксель-арт для вывода в консоль"""
    target_img = adjust_image_size(image, mode)
    width, height = target_img.size

    char_width = width * 2 if mode in ["4", "5"] else width

    print(f"\nРазрешение сетки: {width}x{height} пикс. | Ширина строки в консоли: {char_width} симв.")
    if char_width > 150:
        print("ВНИМАНИЕ: Ширина большая! Уменьшите шрифт (Ctrl + колесико вниз), чтобы строки не ломались.")

    rgb_pixels, gray_pixels = prepare_pixels(target_img)
    num_chars = len(ASCII_CHARS)

    ascii_lines = []
    current_line = []

    for i in range(len(rgb_pixels)):
        r, g, b = rgb_pixels[i]

        if mode == "4":
            char = "██"
        elif mode == "5":
            brightness = gray_pixels[i]
            char = ASCII_CHARS[int(brightness / 256 * num_chars)] * 2
        else:
            brightness = gray_pixels[i]
            char = ASCII_CHARS[int(brightness / 256 * num_chars)]

        colored_char = f"\033[38;2;{r};{g};{b}m{char}"
        current_line.append(colored_char)

        if (i + 1) % width == 0:
            ascii_lines.append("".join(current_line) + "\033[0m")
            current_line = []

    return "\n".join(ascii_lines)

def main():
    print("--- ЦВЕТНОЙ КОНВЕРТЕР КАРТИНОК В ASCII (КОНСОЛЬ + PNG) ---")
    print("Для выхода введите 'выход' или 'q'.\n")
    
    while True:
        path = input("Перетащите картинку сюда: ").strip().strip('"').strip("'")
        
        if path.lower() in ['q', 'quit', 'exit', 'выход']:
            print("Выход из программы...")
            break
            
        if not path:
            continue
        
        try:
            image = Image.open(path)
        except Exception as e:
            print(f"Ошибка при открытии изображения: {e}\nПопробуйте еще раз.\n")
            continue

        orig_w, orig_h = image.size
        ratio_str = get_aspect_ratio_str(orig_w, orig_h)
        
        print(f"\nИсходное разрешение: {orig_w}x{orig_h} пикс. | Авто-пропорции: [{ratio_str}]")
        print("Выберите режим:")
        print("  1 - В консоль: Стандартный под размер окна (ширина 120 симв.) — по умолчанию")
        print(f"  2 - В консоль: 1 символ = 1 пиксель ({orig_w}x{orig_h}) — вытянется вверх")
        print(f"  3 - В консоль: Оригинальная ширина с коррекцией высоты ({orig_w}x{int(orig_h*0.55)})")
        print("  4 - В консоль: КВАДРАТНЫЕ ПИКСЕЛИ — Сплошные блоки '██' (с выбором сжатия)")
        print("  5 - В консоль: КВАДРАТНЫЕ ПИКСЕЛИ — Двойные буквы '@@' (с выбором сжатия)")
        print("  6 - СОХРАНИТЬ В PNG: Цветной ASCII-арт из двойных букв '@@' (с сохранением пропорций)")
        print("  7 - СОХРАНИТЬ В PNG: Пиксель-арт из сплошных блоков '██' (с сохранением пропорций)")
        
        
        mode = input("Ваш выбор (введите цифру от 1 до 7 или Enter для 1): ").strip()
        if mode not in ["1", "2", "3", "4", "5", "6", "7"]:
            mode = "1"

        if mode == "6":
            save_ascii_as_png(image, path, use_blocks=False)
        elif mode == "7":
            save_ascii_as_png(image, path, use_blocks=True)
        else:
            ascii_art = image_to_color_ascii(image, mode)
            print("\n" + ascii_art + "\n")
            
        print("-" * 50)

if __name__ == "__main__":
    main()