import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import threading
import tempfile
from fastapi import FastAPI, Request, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

PROGRESS: dict = {}

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8080", "http://localhost:8080"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_converter = None
OCR_LOCK = threading.Lock()


def get_ocr_converter():
    global _converter
    if _converter is None:
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
        opts = PdfPipelineOptions()
        opts.do_ocr = True
        opts.do_table_structure = True
        opts.ocr_options = EasyOcrOptions(lang=["id", "en"], force_full_page_ocr=True)
        _converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    return _converter


@app.get("/health")
def health():
    return {"status": "ok"}


def make_progress_cb(job_id):
    def cb(ev):
        k = ev.kind.value
        if k == "document_started":
            PROGRESS[job_id] = {"pct": 5, "text": "Dokumen diterima"}
        elif k == "phase_started":
            ph = ev.phase.value
            if ph == "initialize":
                PROGRESS[job_id] = {"pct": 10, "text": "Menyiapkan model OCR…"}
            elif ph == "build":
                PROGRESS[job_id] = {"pct": 20, "text": "Membaca halaman PDF…"}
            elif ph == "assemble":
                PROGRESS[job_id] = {"pct": 92, "text": "Menyusun dokumen…"}
            elif ph == "enrich":
                PROGRESS[job_id] = {"pct": 90, "text": "Analisis lanjutan…"}
        elif k == "page_completed":
            tot = ev.total_pages or 1
            pct = 20 + int(70 * ev.completed_pages / tot)
            PROGRESS[job_id] = {"pct": pct, "text": f"OCR halaman {ev.completed_pages}/{tot}…"}
        elif k == "enrichment_progress":
            if ev.total_items:
                pct = 90 + int(5 * ev.completed_items / ev.total_items)
                PROGRESS[job_id] = {"pct": pct, "text": f"{ev.label}: {ev.completed_items}/{ev.total_items}…"}
        elif k == "document_completed":
            PROGRESS[job_id] = {"pct": 100, "text": "Selesai"}
    return cb


@app.get("/progress/{job_id}")
def progress(job_id: str):
    return PROGRESS.get(job_id, {"pct": 0, "text": ""})


@app.post("/ocr")
def ocr(file: UploadFile, request: Request):
    job_id = request.headers.get("x-job-id")
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Hanya PDF")
    data = file.file.read()
    if len(data) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Terlalu besar")
    try:
        cb = make_progress_cb(job_id) if job_id else None
        with OCR_LOCK:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(data)
                path = f.name
            try:
                conv = get_ocr_converter().convert(path, progress_callback=cb) if cb else get_ocr_converter().convert(path)
                md = conv.document.export_to_markdown()
            finally:
                os.unlink(path)
        return {"filename": file.filename, "markdown": md, "chars": len(md)}
    except Exception as e:
        raise HTTPException(status_code=500, detail="OCR gagal: " + str(e)[:500])
    finally:
        if job_id:
            PROGRESS.pop(job_id, None)
