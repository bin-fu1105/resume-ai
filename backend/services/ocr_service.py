"""Automatic resume text extraction with optional PaddleOCR fallback."""

from __future__ import annotations

import logging
import os
import tempfile
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from contextlib import suppress
from pathlib import Path

import fitz

from services.resume_parser import (
    ResumeParseError,
    extract_docx_text,
    extract_pdf_text,
)

logger = logging.getLogger(__name__)

SELECTABLE_TEXT_THRESHOLD = 50
OCR_TIMEOUT_SECONDS = 15
OCR_FAIL_MESSAGE = "Unable to recognize text from the uploaded document."
OCR_SUCCESS_MESSAGE = "Scanned resume detected. OCR completed successfully."
OCR_TIMEOUT_MESSAGE = (
    "This scanned document is too large.\nPlease upload a text-based PDF."
)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
PDF_EXTENSION = ".pdf"
DOCX_EXTENSION = ".docx"

_ocr_engine = None


class OcrTimeoutError(ResumeParseError):
    """Raised when OCR exceeds the allowed wall-clock budget."""


def _format_exception(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"


def _traceback_text(exc: BaseException | None = None) -> str:
    if exc is None:
        return traceback.format_exc()
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def _raise_ocr_error(prefix: str, exc: BaseException | None = None) -> None:
    """Raise ResumeParseError with the complete traceback (never empty-text fallback)."""
    if exc is None:
        tb = traceback.format_exc()
        message = prefix
    else:
        tb = _traceback_text(exc)
        message = f"{prefix}: {_format_exception(exc)}"
    logger.error("%s\n%s", message, tb)
    raise ResumeParseError(f"{message}\n\n{tb}") from exc


def probe_ocr_runtime() -> dict:
    """Report whether OCR imports/initializes in this runtime (for deploy proof)."""
    status = {
        "ocr_service_imported": True,
        "paddleocr_installed": False,
        "paddleocr_import_error": None,
        "paddleocr_initialized": False,
        "paddleocr_init_error": None,
        "engine_ready": _ocr_engine is not None,
    }
    try:
        import paddleocr  # noqa: F401
        from paddleocr import PaddleOCR  # noqa: F401

        status["paddleocr_installed"] = True
        status["paddleocr_version"] = getattr(
            __import__("paddleocr"), "__version__", "unknown"
        )
    except Exception as exc:
        status["paddleocr_import_error"] = _format_exception(exc)
        status["paddleocr_import_traceback"] = _traceback_text(exc)
        return status

    try:
        _get_ocr_engine()
        status["paddleocr_initialized"] = True
        status["engine_ready"] = True
    except Exception as exc:
        status["paddleocr_init_error"] = str(exc)
    return status


def _get_ocr_engine():
    """Lazy-load PaddleOCR (Chinese + English). Heavy import deferred until needed."""
    global _ocr_engine
    if _ocr_engine is not None:
        logger.info("PaddleOCR engine reuse (already initialized)")
        return _ocr_engine

    logger.info("PaddleOCR import starting")
    try:
        from paddleocr import PaddleOCR
    except Exception as exc:
        logger.exception("PaddleOCR import failed")
        _raise_ocr_error("OCR unavailable (import failed)", exc)

    # Prefer PaddleOCR 3.x ONNX runtime (portable). Fall back to classic 2.x init.
    init_attempts = (
        {
            "lang": "ch",
            "engine": "onnxruntime",
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
        },
        {
            "lang": "ch",
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
        },
        {
            "use_angle_cls": True,
            "lang": "ch",
            "use_gpu": False,
            "show_log": False,
        },
        {
            "use_angle_cls": True,
            "lang": "ch",
            "use_gpu": False,
        },
        {
            "lang": "ch",
        },
        {},
    )

    errors: list[str] = []
    for kwargs in init_attempts:
        try:
            logger.info("PaddleOCR init attempt with keys=%s", sorted(kwargs))
            engine = PaddleOCR(**kwargs)
            _ocr_engine = engine
            logger.info(
                "PaddleOCR initialized successfully with keys=%s",
                sorted(kwargs),
            )
            return _ocr_engine
        except Exception as exc:
            message = _format_exception(exc)
            errors.append(f"{sorted(kwargs) or ['<defaults>']}: {message}")
            logger.exception("PaddleOCR init attempt failed for keys=%s", sorted(kwargs))

    detail = " | ".join(errors) if errors else "unknown initialization error"
    logger.error("PaddleOCR init failed after all attempts: %s", detail)
    raise ResumeParseError(
        "OCR unavailable (init failed): "
        f"{detail}\n\n"
        "Complete init attempt errors are listed above."
    )


def _lines_from_ocr_result(result) -> list[str]:
    """Normalize PaddleOCR 2.x / 3.x output into plain text lines."""
    lines: list[str] = []
    if result is None:
        return lines

    # PaddleOCR 3.x: predict() may return a list of result objects/dicts.
    if isinstance(result, list) and result and not isinstance(result[0], (list, tuple)):
        for item in result:
            if item is None:
                continue
            if isinstance(item, dict):
                texts = item.get("rec_texts") or item.get("texts") or []
                for text in texts:
                    cleaned = str(text).strip()
                    if cleaned:
                        lines.append(cleaned)
                continue

            texts = getattr(item, "rec_texts", None) or getattr(item, "texts", None)
            if texts:
                for text in texts:
                    cleaned = str(text).strip()
                    if cleaned:
                        lines.append(cleaned)
                continue

            as_dict = getattr(item, "json", None)
            if callable(as_dict):
                as_dict = None
            if as_dict is None and hasattr(item, "to_dict") and callable(item.to_dict):
                try:
                    as_dict = item.to_dict()
                except Exception as exc:
                    logger.warning(
                        "OCR result to_dict failed: %s", _format_exception(exc)
                    )
                    as_dict = None
            if isinstance(as_dict, dict):
                res_payload = as_dict.get("res") if isinstance(as_dict.get("res"), dict) else as_dict
                texts = (
                    res_payload.get("rec_texts")
                    or res_payload.get("texts")
                    or []
                )
                for text in texts:
                    cleaned = str(text).strip()
                    if cleaned:
                        lines.append(cleaned)

        if lines:
            return lines

    pages = result if isinstance(result, list) else [result]
    for page in pages:
        if not page:
            continue
        if isinstance(page, dict):
            texts = page.get("rec_texts") or page.get("texts") or []
            for text in texts:
                cleaned = str(text).strip()
                if cleaned:
                    lines.append(cleaned)
            continue

        for item in page:
            try:
                # Classic 2.x shape: [box, (text, confidence)]
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    text_info = item[1]
                    if isinstance(text_info, (list, tuple)) and text_info:
                        text = str(text_info[0]).strip()
                    else:
                        text = str(text_info).strip()
                    if text:
                        lines.append(text)
            except (TypeError, ValueError, IndexError) as exc:
                logger.warning("Skipping OCR line parse error: %s", _format_exception(exc))
                continue

    return lines


def _ensure_ocr_budget(deadline: float) -> None:
    if time.monotonic() > deadline:
        raise OcrTimeoutError(OCR_TIMEOUT_MESSAGE)


def _ocr_image(image_path: str, deadline: float | None = None) -> str:
    if deadline is not None:
        _ensure_ocr_budget(deadline)

    engine = _get_ocr_engine()
    errors: list[str] = []
    result = None

    if hasattr(engine, "predict"):
        try:
            logger.info("OCR predict() on %s", image_path)
            result = engine.predict(image_path)
        except Exception as exc:
            message = _format_exception(exc)
            errors.append(f"predict: {message}")
            logger.exception("OCR predict() failed for %s", image_path)
            result = None

    if result is None and hasattr(engine, "ocr"):
        try:
            logger.info("OCR ocr() on %s", image_path)
            try:
                result = engine.ocr(image_path, cls=True)
            except TypeError:
                result = engine.ocr(image_path)
        except Exception as exc:
            message = _format_exception(exc)
            errors.append(f"ocr: {message}")
            logger.exception("OCR ocr() failed for %s", image_path)
            result = None

    if deadline is not None:
        _ensure_ocr_budget(deadline)

    if result is None:
        detail = " | ".join(errors) if errors else "no OCR method succeeded"
        raise ResumeParseError(
            f"OCR runtime failed: {detail}\n\n"
            "OCR was attempted but predict()/ocr() produced no result."
        )

    lines = _lines_from_ocr_result(result)
    text = "\n".join(lines).strip()
    logger.info(
        "OCR image parsed path=%s lines=%s chars=%s result_type=%s",
        image_path,
        len(lines),
        len(text),
        type(result).__name__,
    )
    if not text:
        logger.error(
            "OCR returned empty text for %s; raw result preview=%r",
            image_path,
            repr(result)[:1000],
        )
    return text


def _ocr_pdf(pdf_path: str, deadline: float | None = None) -> str:
    """Rasterize each PDF page to a temp PNG, OCR it, then delete the image."""
    page_texts: list[str] = []

    with fitz.open(pdf_path) as document:
        page_count = document.page_count
        logger.info("OCR PDF page_count=%s path=%s", page_count, pdf_path)
        if page_count == 0:
            raise ResumeParseError("OCR runtime failed: PDF has zero pages")

        for page_index, page in enumerate(document):
            if deadline is not None:
                _ensure_ocr_budget(deadline)

            temp_img_path = None
            try:
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=".png",
                    dir=tempfile.gettempdir(),
                    prefix=f"ocr_page_{page_index}_",
                ) as tmp:
                    temp_img_path = tmp.name
                pixmap.save(temp_img_path)
                logger.info(
                    "OCR PDF rendered page=%s/%s -> %s",
                    page_index + 1,
                    page_count,
                    temp_img_path,
                )
                page_text = _ocr_image(temp_img_path, deadline=deadline)
                if page_text:
                    page_texts.append(page_text)
            finally:
                if temp_img_path:
                    with suppress(OSError):
                        os.unlink(temp_img_path)

    text = "\n\n".join(page_texts).strip()
    if not text:
        raise ResumeParseError(
            "OCR runtime failed: no text recognized on any PDF page"
        )
    return text


def _run_ocr_job(file_path: str, extension: str, deadline: float) -> str:
    logger.info("OCR STARTED path=%s extension=%s", file_path, extension)
    started = time.monotonic()
    try:
        if extension == PDF_EXTENSION:
            text = _ocr_pdf(file_path, deadline=deadline)
        elif extension in IMAGE_EXTENSIONS:
            text = _ocr_image(file_path, deadline=deadline)
        else:
            raise ResumeParseError(
                f"OCR runtime failed: unsupported extension for OCR ({extension})"
            )

        if not text or not text.strip():
            raise ResumeParseError(OCR_FAIL_MESSAGE)

        elapsed = time.monotonic() - started
        logger.info(
            "OCR FINISHED path=%s chars=%s elapsed=%.2fs",
            file_path,
            len(text.strip()),
            elapsed,
        )
        return text.strip()
    except Exception:
        elapsed = time.monotonic() - started
        logger.error(
            "OCR FAILED path=%s elapsed=%.2fs\n%s",
            file_path,
            elapsed,
            traceback.format_exc(),
        )
        raise


def _run_ocr(file_path: str, extension: str) -> str:
    deadline = time.monotonic() + OCR_TIMEOUT_SECONDS

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_ocr_job, file_path, extension, deadline)
            return future.result(timeout=OCR_TIMEOUT_SECONDS)
    except OcrTimeoutError:
        raise
    except FuturesTimeoutError as exc:
        logger.error(
            "OCR timed out after %ss for %s", OCR_TIMEOUT_SECONDS, file_path
        )
        raise OcrTimeoutError(OCR_TIMEOUT_MESSAGE) from exc
    except ResumeParseError:
        raise
    except Exception as exc:
        _raise_ocr_error("OCR runtime failed", exc)


def get_resume_text(file_path: str) -> tuple[str, bool]:
    """
    Extract resume text from a local temp file.

    Returns:
        (text, used_ocr)

    Automatically uses selectable PDF/DOCX text when available, otherwise OCR.
    Never returns an empty-text fallback before OCR has been attempted for
    PDF/image uploads.
    """
    path = Path(file_path)
    extension = path.suffix.lower()
    logger.info("get_resume_text start path=%s extension=%s", path, extension)

    if extension == DOCX_EXTENSION:
        try:
            text = extract_docx_text(str(path)).strip()
        except ResumeParseError:
            raise
        except Exception as exc:
            logger.exception("DOCX extraction failed")
            raise ResumeParseError(
                f"Failed to extract DOCX text: {_format_exception(exc)}\n\n"
                f"{_traceback_text(exc)}"
            ) from exc
        if not text:
            raise ResumeParseError(
                "DOCX contained no extractable text. "
                "OCR is not used for DOCX uploads."
            )
        return text, False

    if extension == PDF_EXTENSION:
        try:
            selectable = extract_pdf_text(str(path)).strip()
        except Exception as exc:
            logger.exception("PDF selectable-text extraction failed; will try OCR")
            selectable = ""
            logger.info(
                "PDF selectable text unavailable: %s", _format_exception(exc)
            )

        logger.info(
            "PDF selectable text chars=%s threshold=%s",
            len(selectable),
            SELECTABLE_TEXT_THRESHOLD,
        )

        if len(selectable) > SELECTABLE_TEXT_THRESHOLD:
            logger.info("Using selectable PDF text (OCR not required)")
            return selectable, False

        # Image-only / scanned PDF: always enter OCR. Do not return empty-text.
        logger.info("Selectable PDF text insufficient; invoking OCR")
        return _run_ocr(str(path), extension), True

    if extension in IMAGE_EXTENSIONS:
        logger.info("Image upload detected; invoking OCR for %s", extension)
        return _run_ocr(str(path), extension), True

    raise ResumeParseError(
        "Unsupported file type. Only PDF, DOCX, PNG, JPG, and JPEG are allowed."
    )
