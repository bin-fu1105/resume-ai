"""Resume text extraction: selectable PDF/DOCX text, else Claude Vision."""

from __future__ import annotations

import base64
import logging
import mimetypes
import os
import tempfile
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from contextlib import suppress
from pathlib import Path

import anthropic
import fitz

from services.resume_parser import (
    ResumeParseError,
    extract_docx_text,
    extract_pdf_text,
)

logger = logging.getLogger(__name__)

SELECTABLE_TEXT_THRESHOLD = 50
VISION_TIMEOUT_SECONDS = 90
VISION_MAX_PAGES = 10
# PDF user space is 72 DPI; 180 DPI sits in the requested 150–200 range.
VISION_DPI = 180
VISION_FAIL_MESSAGE = "Unable to read the scanned resume."
VISION_SUCCESS_MESSAGE = "AI Vision extraction completed."
VISION_READING_MESSAGE = (
    "Scanned resume detected.\nReading with AI Vision..."
)

VISION_PROMPT = (
    "You are an OCR engine.\n"
    "\n"
    "Extract every visible word.\n"
    "Preserve formatting where possible.\n"
    "Return plain UTF-8 text only.\n"
    "Do not summarize.\n"
    "Do not explain."
)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
PDF_EXTENSION = ".pdf"
DOCX_EXTENSION = ".docx"

# Kept for upload response compatibility (always Claude Vision when used).
_ocr_backend: str | None = None

# Backward-compatible aliases used by main.py
OCR_SUCCESS_MESSAGE = VISION_SUCCESS_MESSAGE
OCR_FAIL_MESSAGE = VISION_FAIL_MESSAGE


class VisionTimeoutError(ResumeParseError):
    """Raised when Claude Vision exceeds the allowed wall-clock budget."""


def probe_ocr_runtime() -> dict:
    """Deploy proof for the Vision-based extraction path."""
    return {
        "ocr_service_imported": True,
        "extraction_backend": "claude_vision",
        "claude_vision_available": bool(os.getenv("ANTHROPIC_API_KEY")),
        "paddleocr_installed": False,
        "rapidocr_installed": False,
        "vision_max_pages": VISION_MAX_PAGES,
        "vision_dpi": VISION_DPI,
        "note": "Production uses Claude Vision for scanned/image resumes.",
    }


def _mime_for_path(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    if mime in {"image/png", "image/jpeg", "image/webp", "image/gif"}:
        return mime
    return "image/png"


def _image_content_block(image_path: str) -> dict:
    encoded = base64.standard_b64encode(Path(image_path).read_bytes()).decode("utf-8")
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": _mime_for_path(image_path),
            "data": encoded,
        },
    }


def _usage_summary(message) -> str:
    usage = getattr(message, "usage", None)
    if usage is None:
        return "tokens=unavailable"

    input_tokens = getattr(usage, "input_tokens", None)
    output_tokens = getattr(usage, "output_tokens", None)
    cache_read = getattr(usage, "cache_read_input_tokens", None)
    cache_create = getattr(usage, "cache_creation_input_tokens", None)

    parts = [
        f"input_tokens={input_tokens}",
        f"output_tokens={output_tokens}",
    ]
    if cache_read is not None:
        parts.append(f"cache_read_tokens={cache_read}")
    if cache_create is not None:
        parts.append(f"cache_create_tokens={cache_create}")
    return " ".join(parts)


def _log_vision(event: str, **fields) -> None:
    detail = " ".join(f"{key}={value}" for key, value in fields.items())
    line = f"{event} {detail}".strip()
    print(line, flush=True)
    if event == "VISION FAILED":
        logger.error(line)
    else:
        logger.info(line)


def _call_claude_vision(
    image_paths: list[str],
    *,
    filename: str,
    page_count: int,
) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ResumeParseError(VISION_FAIL_MESSAGE)

    if not image_paths:
        raise ResumeParseError(VISION_FAIL_MESSAGE)

    content: list[dict] = [_image_content_block(path) for path in image_paths]
    content.append({"type": "text", "text": VISION_PROMPT})

    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
    client = anthropic.Anthropic(api_key=api_key)
    started = time.monotonic()

    _log_vision(
        "VISION STARTED",
        filename=filename,
        page_count=page_count,
        pages_sent=len(image_paths),
        dpi=VISION_DPI,
        model=model,
    )

    try:
        message = client.messages.create(
            model=model,
            max_tokens=8192,
            messages=[{"role": "user", "content": content}],
        )
    except Exception as exc:
        elapsed = time.monotonic() - started
        _log_vision(
            "VISION FAILED",
            filename=filename,
            page_count=page_count,
            elapsed_s=f"{elapsed:.2f}",
            error=f"{type(exc).__name__}: {exc}",
        )
        print(traceback.format_exc(), flush=True)
        logger.exception("Claude Vision request failed")
        raise ResumeParseError(VISION_FAIL_MESSAGE) from None

    chunks: list[str] = []
    for block in message.content:
        text = getattr(block, "text", None)
        if text:
            chunks.append(text)

    text = "\n".join(chunks).strip()
    elapsed = time.monotonic() - started
    usage = _usage_summary(message)

    if not text:
        _log_vision(
            "VISION FAILED",
            filename=filename,
            page_count=page_count,
            elapsed_s=f"{elapsed:.2f}",
            usage=usage,
            error="empty_text",
        )
        raise ResumeParseError(VISION_FAIL_MESSAGE)

    _log_vision(
        "VISION FINISHED",
        filename=filename,
        page_count=page_count,
        pages_sent=len(image_paths),
        elapsed_s=f"{elapsed:.2f}",
        chars=len(text),
        usage=usage,
    )
    return text


def _pdf_pages_to_temp_images(pdf_path: str) -> tuple[list[str], int]:
    """
    Rasterize PDF pages to temp PNGs at VISION_DPI.

    Returns (image_paths, total_page_count). Only the first VISION_MAX_PAGES
    are rendered. Caller must delete the returned paths.
    """
    image_paths: list[str] = []
    zoom = VISION_DPI / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    with fitz.open(pdf_path) as document:
        total_pages = document.page_count
        if total_pages == 0:
            _log_vision(
                "VISION FAILED",
                filename=Path(pdf_path).name,
                page_count=0,
                elapsed_s=0,
                error="pdf_has_zero_pages",
            )
            raise ResumeParseError(VISION_FAIL_MESSAGE)

        pages_to_render = min(total_pages, VISION_MAX_PAGES)
        if total_pages > VISION_MAX_PAGES:
            logger.warning(
                "Vision page limit applied filename=%s total_pages=%s max=%s",
                Path(pdf_path).name,
                total_pages,
                VISION_MAX_PAGES,
            )

        for page_index in range(pages_to_render):
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".png",
                dir=tempfile.gettempdir(),
                prefix=f"vision_page_{page_index}_",
            ) as tmp:
                image_path = tmp.name
            pixmap.save(image_path)
            image_paths.append(image_path)

    return image_paths, total_pages


def _extract_with_vision(file_path: str, extension: str) -> str:
    global _ocr_backend
    _ocr_backend = "claude_vision"

    filename = Path(file_path).name
    temp_images: list[str] = []
    page_count = 1
    started = time.monotonic()

    try:
        if extension == PDF_EXTENSION:
            temp_images, page_count = _pdf_pages_to_temp_images(file_path)
            image_paths = temp_images
        elif extension in IMAGE_EXTENSIONS:
            image_paths = [file_path]
            page_count = 1
        else:
            raise ResumeParseError(VISION_FAIL_MESSAGE)

        return _call_claude_vision(
            image_paths,
            filename=filename,
            page_count=page_count,
        )
    except ResumeParseError:
        raise
    except Exception as exc:
        elapsed = time.monotonic() - started
        _log_vision(
            "VISION FAILED",
            filename=filename,
            page_count=page_count,
            elapsed_s=f"{elapsed:.2f}",
            error=f"{type(exc).__name__}: {exc}",
        )
        print(traceback.format_exc(), flush=True)
        logger.exception("Vision extraction failed for %s", file_path)
        raise ResumeParseError(VISION_FAIL_MESSAGE) from None
    finally:
        for path in temp_images:
            with suppress(OSError):
                os.unlink(path)


def _run_vision_with_timeout(file_path: str, extension: str) -> str:
    filename = Path(file_path).name
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_extract_with_vision, file_path, extension)
            return future.result(timeout=VISION_TIMEOUT_SECONDS)
    except VisionTimeoutError:
        raise
    except FuturesTimeoutError as exc:
        _log_vision(
            "VISION FAILED",
            filename=filename,
            page_count="unknown",
            elapsed_s=VISION_TIMEOUT_SECONDS,
            error="timeout",
        )
        raise ResumeParseError(VISION_FAIL_MESSAGE) from exc
    except ResumeParseError:
        raise
    except Exception as exc:
        _log_vision(
            "VISION FAILED",
            filename=filename,
            page_count="unknown",
            elapsed_s="unknown",
            error=f"{type(exc).__name__}: {exc}",
        )
        print(traceback.format_exc(), flush=True)
        logger.exception("Vision extraction failed for %s", file_path)
        raise ResumeParseError(VISION_FAIL_MESSAGE) from None


def get_resume_text(file_path: str) -> tuple[str, bool]:
    """
    Extract resume text from a local temp file.

    Returns:
        (text, used_vision)

    Uses selectable PDF/DOCX text when available; otherwise Claude Vision.
    """
    path = Path(file_path)
    extension = path.suffix.lower()
    logger.info("get_resume_text start path=%s extension=%s", path, extension)
    print(f"get_resume_text start path={path} extension={extension}", flush=True)

    if extension == DOCX_EXTENSION:
        try:
            text = extract_docx_text(str(path)).strip()
        except ResumeParseError:
            raise
        except Exception as exc:
            logger.exception("DOCX extraction failed")
            raise ResumeParseError(
                f"Failed to extract DOCX text: {type(exc).__name__}: {exc}"
            ) from exc
        if not text:
            raise ResumeParseError(
                "DOCX contained no extractable text. "
                "Vision is not used for DOCX uploads."
            )
        return text, False

    if extension == PDF_EXTENSION:
        try:
            selectable = extract_pdf_text(str(path)).strip()
        except Exception as exc:
            logger.exception("PDF selectable-text extraction failed; will use Vision")
            selectable = ""
            print(
                f"PDF selectable text unavailable: {type(exc).__name__}: {exc}",
                flush=True,
            )

        print(
            f"PDF selectable text chars={len(selectable)} "
            f"threshold={SELECTABLE_TEXT_THRESHOLD}",
            flush=True,
        )

        if len(selectable) >= SELECTABLE_TEXT_THRESHOLD:
            logger.info("Using selectable PDF text (Vision not required)")
            print("Using selectable PDF text (Vision not required)", flush=True)
            return selectable, False

        print("Selectable PDF text insufficient; invoking Claude Vision", flush=True)
        return _run_vision_with_timeout(str(path), extension), True

    if extension in IMAGE_EXTENSIONS:
        print(
            f"Image upload detected; invoking Claude Vision for {extension}",
            flush=True,
        )
        return _run_vision_with_timeout(str(path), extension), True

    raise ResumeParseError(
        "Unsupported file type. Only PDF, DOCX, PNG, JPG, and JPEG are allowed."
    )
