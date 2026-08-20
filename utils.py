"""
Fonctions de traitement PDF pour PDF Toolbox.
Tout se passe en mémoire (io.BytesIO) : aucun fichier n'est jamais envoyé
à un service externe, tout tourne dans le processus Streamlit.
"""

import io
import zipfile
from typing import List, Tuple

from pypdf import PdfReader, PdfWriter
from PIL import Image, ImageOps


# --------------------------------------------------------------------------- #
# Utilitaires généraux
# --------------------------------------------------------------------------- #

def human_size(num_bytes: int) -> str:
    """Formate une taille en octets en chaîne lisible (Ko / Mo)."""
    size = float(num_bytes)
    for unit in ("o", "Ko", "Mo", "Go"):
        if size < 1024 or unit == "Go":
            return f"{size:.1f} {unit}" if unit != "o" else f"{int(size)} {unit}"
        size /= 1024
    return f"{size:.1f} Go"


def pdf_page_count(pdf_bytes: bytes) -> int:
    return len(PdfReader(io.BytesIO(pdf_bytes)).pages)


# --------------------------------------------------------------------------- #
# 1) Fusionner des PDF
# --------------------------------------------------------------------------- #

def merge_pdfs(files_in_order: List[bytes]) -> bytes:
    """Fusionne une liste de PDF (bytes) dans l'ordre donné."""
    writer = PdfWriter()
    for pdf_bytes in files_in_order:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# --------------------------------------------------------------------------- #
# 2) Réduire la taille d'un PDF
# --------------------------------------------------------------------------- #

def _compress_once(pdf_bytes: bytes, quality: int, scale: float) -> bytes:
    """Recompresse toutes les images d'un PDF avec une qualité JPEG et un
    facteur d'échelle donnés, puis compresse les flux de contenu."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()

    for page in reader.pages:
        try:
            for img in page.images:
                try:
                    image = Image.open(io.BytesIO(img.data))
                    if image.mode not in ("RGB", "L"):
                        image = image.convert("RGB")
                    if scale < 1.0:
                        new_w = max(1, int(image.width * scale))
                        new_h = max(1, int(image.height * scale))
                        image = image.resize((new_w, new_h), Image.LANCZOS)
                    img.replace(image, quality=quality)
                except Exception:
                    # Une image illisible/exotique : on la laisse telle quelle
                    continue
        except Exception:
            pass
        writer.add_page(page)

    try:
        writer.compress_content_streams()
    except Exception:
        pass

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


PRESETS = {
    "Légère": dict(quality=80, scale=1.0),
    "Moyenne": dict(quality=55, scale=0.85),
    "Forte": dict(quality=30, scale=0.6),
}


def compress_pdf_preset(pdf_bytes: bytes, preset: str) -> bytes:
    params = PRESETS[preset]
    return _compress_once(pdf_bytes, quality=params["quality"], scale=params["scale"])


def compress_pdf_to_target(
    pdf_bytes: bytes, target_bytes: int, quality: int = 50, max_iters: int = 7
) -> Tuple[bytes, bool]:
    """
    Recherche par dichotomie du facteur d'échelle des images qui permet de
    se rapprocher au mieux de `target_bytes`, sans le dépasser si possible.
    Retourne (pdf_compresse, objectif_atteint).
    """
    original_size = len(pdf_bytes)
    if original_size <= target_bytes:
        return pdf_bytes, True

    low, high = 0.1, 1.0
    best_result = None
    best_size = None

    for _ in range(max_iters):
        mid = (low + high) / 2
        candidate = _compress_once(pdf_bytes, quality=quality, scale=mid)
        size = len(candidate)

        if best_size is None or (
            size <= target_bytes and size > (best_size if best_size <= target_bytes else 0)
        ) or (best_size > target_bytes and size < best_size):
            best_result = candidate
            best_size = size

        if size > target_bytes:
            high = mid
        else:
            low = mid

    achieved = best_size is not None and best_size <= target_bytes
    return (best_result if best_result is not None else pdf_bytes), achieved


# --------------------------------------------------------------------------- #
# 3) Convertir des images en PDF
# --------------------------------------------------------------------------- #

PAGE_SIZES_MM = {
    "A4": (210, 297),
    "Letter": (216, 279),
}


def _fit_to_page(image: Image.Image, page_size_mm, dpi: int = 200) -> Image.Image:
    page_w = int(page_size_mm[0] / 25.4 * dpi)
    page_h = int(page_size_mm[1] / 25.4 * dpi)
    canvas = Image.new("RGB", (page_w, page_h), "white")

    # On ne rétrécit que si l'image est plus grande que la page.
    # On ne l'agrandit jamais (ça la rendrait floue).
    scale = min(page_w / image.width, page_h / image.height, 1.0)
    new_w = max(1, int(image.width * scale))
    new_h = max(1, int(image.height * scale))

    if scale < 1.0:
        resized = image.resize((new_w, new_h), Image.LANCZOS)
    else:
        resized = image  # taille d'origine conservée, pas d'étirement

    offset = ((page_w - new_w) // 2, (page_h - new_h) // 2)
    canvas.paste(resized, offset)
    return canvas


def enhance_scan(image: Image.Image) -> Image.Image:
    """Effet 'scanner' simple : niveaux de gris + contraste automatique
    (façon CamScanner), sans dépendance externe."""
    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray, cutoff=1)
    return gray.convert("RGB")


def images_to_pdf(
    images: List[bytes],
    page_size: str = "Taille d'origine",
    scan_effect: bool = False,
) -> bytes:
    """Convertit une liste d'images (bytes) en un PDF multi-pages."""
    pil_images = []
    for raw in images:
        im = Image.open(io.BytesIO(raw))
        im = ImageOps.exif_transpose(im)
        if im.mode != "RGB":
            im = im.convert("RGB")
        if scan_effect:
            im = enhance_scan(im)
        if page_size != "Taille d'origine":
            im = _fit_to_page(im, PAGE_SIZES_MM[page_size])
        pil_images.append(im)

    out = io.BytesIO()
    pil_images[0].save(
        out, format="PDF", save_all=True, append_images=pil_images[1:], quality=92
    )
    return out.getvalue()

# --------------------------------------------------------------------------- #
# 4) Diviser un PDF (une page par fichier, dans un zip)
# --------------------------------------------------------------------------- #

def split_pdf_to_zip(pdf_bytes: bytes, base_name: str = "page") -> bytes:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, page in enumerate(reader.pages, start=1):
            writer = PdfWriter()
            writer.add_page(page)
            page_buf = io.BytesIO()
            writer.write(page_buf)
            zf.writestr(f"{base_name}_{i:03d}.pdf", page_buf.getvalue())
    return zip_buf.getvalue()


# --------------------------------------------------------------------------- #
# 5) Extraire / réorganiser des pages
# --------------------------------------------------------------------------- #

def extract_pages(pdf_bytes: bytes, page_numbers: List[int]) -> bytes:
    """page_numbers : liste 1-indexée, dans l'ordre souhaité."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    for n in page_numbers:
        writer.add_page(reader.pages[n - 1])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# --------------------------------------------------------------------------- #
# 6) Pivoter des pages
# --------------------------------------------------------------------------- #

def rotate_pdf(pdf_bytes: bytes, angle: int, page_numbers: List[int] = None) -> bytes:
    """angle : 90 / 180 / 270. page_numbers=None -> toutes les pages (1-indexé sinon)."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    target = set(page_numbers) if page_numbers else None
    for i, page in enumerate(reader.pages, start=1):
        if target is None or i in target:
            page.rotate(angle)
        writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
