"""
generate_icon.py — Genera icon.ico e icon.png per Agent Ordinatore.

Due cartelle affiancate con frecce di scambio, verde fosforescente su nero.
"""

from PIL import Image, ImageDraw

SIZE = 256
BG = "#0a0f0a"
FG = "#00ff41"
FG_DIM = (0, 255, 65, 128)  # 50% opacity
STROKE = 6
RADIUS = 20
FOLDER_R = 8


def draw_rounded_rect(draw, xy, radius, outline=None, fill=None, width=1):
    """Rettangolo con angoli arrotondati."""
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, outline=outline, fill=fill, width=width)


def draw_folder(draw, x, y, w, h, tab_w, tab_h):
    """Disegna una cartella con tab e file interni."""
    # Tab della cartella
    draw_rounded_rect(draw, (x, y - tab_h, x + tab_w, y + 4), FOLDER_R, outline=FG, width=STROKE)
    # Corpo della cartella
    draw_rounded_rect(draw, (x, y, x + w, y + h), FOLDER_R, outline=FG, width=STROKE)

    # File interni (barrette orizzontali, semi-trasparenti)
    file_margin_x = 14
    file_h = 5
    file_y1 = y + int(h * 0.30)
    file_y2 = y + int(h * 0.55)
    file_w = w - file_margin_x * 2

    # Creiamo le barrette su un layer separato per l'opacita'
    for fy in (file_y1, file_y2):
        draw.rounded_rectangle(
            (x + file_margin_x, fy, x + file_margin_x + file_w, fy + file_h),
            radius=2, fill=FG_DIM
        )


def draw_arrow_right(draw, x_start, y, x_end, head_size):
    """Freccia verso destra con punta."""
    draw.line([(x_start, y), (x_end, y)], fill=FG, width=STROKE, joint="curve")
    # Punta della freccia
    draw.polygon([
        (x_end, y),
        (x_end - head_size, y - head_size // 2),
        (x_end - head_size, y + head_size // 2),
    ], fill=FG)


def draw_arrow_left(draw, x_start, y, x_end, head_size):
    """Freccia verso sinistra con punta."""
    draw.line([(x_start, y), (x_end, y)], fill=FG, width=STROKE, joint="curve")
    # Punta della freccia
    draw.polygon([
        (x_end, y),
        (x_end + head_size, y - head_size // 2),
        (x_end + head_size, y + head_size // 2),
    ], fill=FG)


def generate():
    # Immagine RGBA per supportare trasparenza nelle barrette
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Sfondo con angoli arrotondati
    draw_rounded_rect(draw, (0, 0, SIZE - 1, SIZE - 1), RADIUS, fill=BG)

    # Dimensioni cartelle
    folder_w = 88
    folder_h = 72
    tab_w = 38
    tab_h = 20

    # Posizioni verticali (centrate)
    folder_y = (SIZE - folder_h) // 2 + 8

    # Cartella sinistra
    folder_lx = 22
    draw_folder(draw, folder_lx, folder_y, folder_w, folder_h, tab_w, tab_h)

    # Cartella destra
    folder_rx = SIZE - 22 - folder_w
    draw_folder(draw, folder_rx, folder_y, folder_w, folder_h, tab_w, tab_h)

    # Frecce centrali
    arrow_gap = 16
    center_y = folder_y + folder_h // 2
    arrow_x_left = folder_lx + folder_w + 8
    arrow_x_right = folder_rx - 8
    head = 16

    # Freccia superiore: → (sinistra verso destra)
    arrow_y_top = center_y - arrow_gap
    draw_arrow_right(draw, arrow_x_left, arrow_y_top, arrow_x_right, head)

    # Freccia inferiore: ← (destra verso sinistra)
    arrow_y_bot = center_y + arrow_gap
    draw_arrow_left(draw, arrow_x_right, arrow_y_bot, arrow_x_left, head)

    # Salva PNG 256x256
    img_png = img.copy()
    img_png.save("icon.png", "PNG")
    print("Salvato: icon.png (256x256)")

    # Genera risoluzioni per ICO
    sizes = [16, 32, 48, 64, 128, 256]
    ico_images = []
    for s in sizes:
        resized = img.resize((s, s), Image.LANCZOS)
        ico_images.append(resized)

    # Salva ICO con tutte le risoluzioni
    ico_images[0].save(
        "icon.ico",
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=ico_images[1:],
    )
    print(f"Salvato: icon.ico ({', '.join(str(s) for s in sizes)})")


if __name__ == "__main__":
    generate()
