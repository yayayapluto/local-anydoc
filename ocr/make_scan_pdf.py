from PIL import Image, ImageDraw, ImageFont
import sys


def main(path):
    img = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=48)
    draw.text((100, 200), "Halo dunia. Ini tes OCR anydoc lokal.", fill="black", font=font)
    img.save(path, "PDF")


if __name__ == "__main__":
    main(sys.argv[1])
