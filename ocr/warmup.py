from make_scan_pdf import main
import sys
import os

main("/tmp/w.pdf" if len(sys.argv) < 2 else sys.argv[1])

from app import get_ocr_converter

get_ocr_converter().convert("/tmp/w.pdf")
print("warmup selesai")
