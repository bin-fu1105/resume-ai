"""Automatic resume text extraction with OCR fallback.

Production (Vercel): RapidOCR — fits the 500MB serverless bundle limit.
Local/heavy hosts: PaddleOCR when installed (preferred for EN/ZH quality).
"""

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
_ocr_backend: str | None = None


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
    print(f"OCR ERROR: {message}\n{tb}", flush=True)
    raise ResumeParseError(f"{message}\n\n{tb}") from exc


def probe_ocr_runtime() -> dict:
    """Report whether OCR imports/initializes in this runtime (for deploy proof)."""
    status: dict = {
        "ocr_service_imported": True,
        "active_backend": _ocr_backend,
        "engine_ready": _ocr_engine is not None,
        "paddleocr_installed": False,
        "rapidocr_installed": False,
        "claude_vision_available": bool(os.getenv("ANTHROPIC_API_KEY")),
        "paddleocr_import_error": None,
        "rapidocr_import_error": None,
        "init_error": None,
    }

    try:
        import paddleocr  # noqa: F401

        status["paddleocr_installed"] = True
        status["paddleocr_version"] = getattr(paddleocr, "__version__", "unknown")
    except Exception as exc:
        status["paddleocr_import_error"] = _format_exception(exc)

    try:
        import rapidocr_onnxruntime  # noqa: F401

        status["rapidocr_installed"] = True
    except Exception as exc:
        status["rapidocr_import_error"] = _format_exception(exc)

    try:
        _get_ocr_engine()
        status["active_backend"] = _ocr_backend
        status["engine_ready"] = _ocr_engine is not None
        status["initialized"] = True
    except Exception as exc:
        status["initialized"] = False
        status["init_error"] = str(exc)

    return status


def _init_paddleocr():
    from paddleocr import PaddleOCR

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
        {"use_angle_cls": True, "lang": "ch", "use_gpu": False, "show_log": False},
        {"use_angle_cls": True, "lang": "ch", "use_gpu": False},
        {"lang": "ch"},
        {},
    )
    errors: list[str] = []
    for kwargs in init_attempts:
        try:
            engine = PaddleOCR(**kwargs)
            logger.info("PaddleOCR initialized with keys=%s", sorted(kwargs))
            print(f"PaddleOCR initialized successfully keys={sorted(kwargs)}", flush=True)
            return engine
        except Exception as exc:
            errors.append(f"{sorted(kwargs) or ['<defaults>']}: {_format_exception(exc)}")
            logger.exception("PaddleOCR init attempt failed")
    raise RuntimeError(" | ".join(errors))


def _init_rapidocr():
    # Prefer headless OpenCV on serverless (no libxcb).
    os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "0")
    from rapidocr_onnxruntime import RapidOCR

    engine = RapidOCR()
    logger.info("RapidOCR initialized successfully")
    print("RapidOCR initialized successfully", flush=True)
    return engine


class _ClaudeVisionOcr:
    """Vercel-safe OCR fallback using Anthropic vision (no native GUI libs)."""

    def __call__(self, image_path: str):
        import base64
        import mimetypes

        import anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured for Claude OCR.")

        mime, _ = mimetypes.guess_type(image_path)
        if mime not in {"image/png", "image/jpeg", "image/webp", "image/gif"}:
            mime = "image/png"

        with open(image_path, "rb") as handle:
            encoded = base64.standard_b64encode(handle.read()).decode("utf-8")

        client = anthropic.Anthropic(api_key=api_key)
        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        message = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime,
                                "data": encoded,
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Extract all readable text from this resume image. "
                                "Return plain text only, preserving reading order. "
                                "Do not add commentary."
                            ),
                        },
                    ],
                }
            ],
        )
        chunks: list[str] = []
        for block in message.content:
            text = getattr(block, "text", None)
            if text:
                chunks.append(text)
        text = "\n".join(chunks).strip()
        if not text:
            return [], 0.0
        # Match RapidOCR shape: list of [box, text, score]
        return [[[0, 0], text, 1.0]], 0.0


def _init_claude_ocr():
    engine = _ClaudeVisionOcr()
    logger.info("Claude vision OCR initialized successfully")
    print("Claude vision OCR initialized successfully", flush=True)
    return engine


def _get_ocr_engine():
    """Lazy-load OCR: PaddleOCR -> RapidOCR -> Claude vision."""
    global _ocr_engine, _ocr_backend
    if _ocr_engine is not None and _ocr_backend is not None:
        logger.info("OCR engine reuse backend=%s", _ocr_backend)
        return _ocr_engine, _ocr_backend

    errors: list[str] = []

    try:
        print("OCR ENGINE INIT: trying PaddleOCR", flush=True)
        _ocr_engine = _init_paddleocr()
        _ocr_backend = "paddleocr"
        return _ocr_engine, _ocr_backend
    except Exception as exc:
        errors.append(f"PaddleOCR: {_format_exception(exc)}")
        logger.warning("PaddleOCR unavailable: %s", _format_exception(exc))
        print(
            f"OCR ENGINE INIT: PaddleOCR unavailable: {_format_exception(exc)}",
            flush=True,
        )

    try:
        print("OCR ENGINE INIT: trying RapidOCR", flush=True)
        _ocr_engine = _init_rapidocr()
        _ocr_backend = "rapidocr"
        return _ocr_engine, _ocr_backend
    except Exception as exc:
        errors.append(f"RapidOCR: {_format_exception(exc)}")
        logger.warning("RapidOCR unavailable: %s", _format_exception(exc))
        print(
            f"OCR ENGINE INIT: RapidOCR unavailable: {_format_exception(exc)}",
            flush=True,
        )

    try:
        print("OCR ENGINE INIT: trying Claude vision OCR", flush=True)
        _ocr_engine = _init_claude_ocr()
        _ocr_backend = "claude_vision"
        return _ocr_engine, _ocr_backend
    except Exception as exc:
        errors.append(f"ClaudeVision: {_format_exception(exc)}")
        _raise_ocr_error(
            "OCR unavailable (all engines failed). " + " | ".join(errors),
            exc,
        )
        raise  # pragma: no cover


def _lines_from_paddle_result(result) -> list[str]:
    lines: list[str] = []
    if result is None:
        return lines

    if isinstance(result, list) and result and not isinstance(result[0], (list, tuple)):
        for item in result:
            if item is None:
                continue
            if isinstance(item, dict):
                texts = item.get("rec_texts") or item.get("texts") or []
                lines.extend(str(t).strip() for t in texts if str(t).strip())
                continue
            texts = getattr(item, "rec_texts", None) or getattr(item, "texts", None)
            if texts:
                lines.extend(str(t).strip() for t in texts if str(t).strip())
                continue
            as_dict = getattr(item, "json", None)
            if callable(as_dict):
                as_dict = None
            if as_dict is None and hasattr(item, "to_dict") and callable(item.to_dict):
                try:
                    as_dict = item.to_dict()
                except Exception:
                    as_dict = None
            if isinstance(as_dict, dict):
                payload = as_dict.get("res") if isinstance(as_dict.get("res"), dict) else as_dict
                texts = payload.get("rec_texts") or payload.get("texts") or []
                lines.extend(str(t).strip() for t in texts if str(t).strip())
        if lines:
            return lines

    pages = result if isinstance(result, list) else [result]
    for page in pages:
        if not page:
            continue
        if isinstance(page, dict):
            texts = page.get("rec_texts") or page.get("texts") or []
            lines.extend(str(t).strip() for t in texts if str(t).strip())
            continue
        for item in page:
            try:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    text_info = item[1]
                    if isinstance(text_info, (list, tuple)) and text_info:
                        text = str(text_info[0]).strip()
                    else:
                        text = str(text_info).strip()
                    if text:
                        lines.append(text)
            except (TypeError, ValueError, IndexError):
                continue
    return lines


def _lines_from_rapid_result(result) -> list[str]:
    lines: list[str] = []
    if not result:
        return lines
    for item in result:
        try:
            # RapidOCR: [box, text, confidence]
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                text = str(item[1]).strip()
                if text:
                    lines.append(text)
        except (TypeError, ValueError, IndexError):
            continue
    return lines


def _ensure_ocr_budget(deadline: float) -> None:
    if time.monotonic() > deadline:
        raise OcrTimeoutError(OCR_TIMEOUT_MESSAGE)


def _ocr_image(image_path: str, deadline: float | None = None) -> str:
    if deadline is not None:
        _ensure_ocr_budget(deadline)

    engine, backend = _get_ocr_engine()
    print(f"OCR RUN backend={backend} image={image_path}", flush=True)

    if backend == "paddleocr":
        result = None
        errors: list[str] = []
        if hasattr(engine, "predict"):
            try:
                result = engine.predict(image_path)
            except Exception as exc:
                errors.append(f"predict: {_format_exception(exc)}")
                logger.exception("OCR predict() failed")
        if result is None and hasattr(engine, "ocr"):
            try:
                try:
                    result = engine.ocr(image_path, cls=True)
                except TypeError:
                    result = engine.ocr(image_path)
            except Exception as exc:
                errors.append(f"ocr: {_format_exception(exc)}")
                logger.exception("OCR ocr() failed")
        if result is None:
            raise ResumeParseError(
                "OCR runtime failed: "
                + (" | ".join(errors) if errors else "no OCR method succeeded")
            )
        lines = _lines_from_paddle_result(result)
    else:
        # RapidOCR and Claude vision both expose engine(image_path) -> (rows, elapse)
        try:
            rapid_result, _elapse = engine(image_path)
        except Exception as exc:
            _raise_ocr_error(f"OCR runtime failed ({backend})", exc)
            raise  # pragma: no cover
        lines = _lines_from_rapid_result(rapid_result)

    if deadline is not None:
        _ensure_ocr_budget(deadline)

    text = "\n".join(lines).strip()
    logger.info(
        "OCR image parsed backend=%s path=%s lines=%s chars=%s",
        backend,
        image_path,
        len(lines),
        len(text),
    )
    if not text:
        logger.error("OCR returned empty text for %s backend=%s", image_path, backend)
    return text


def _ocr_pdf(pdf_path: str, deadline: float | None = None) -> str:
    page_texts: list[str] = []

    with fitz.open(pdf_path) as document:
        page_count = document.page_count
        logger.info("OCR PDF page_count=%s path=%s", page_count, pdf_path)
        print(f"OCR PDF page_count={page_count} path={pdf_path}", flush=True)
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
    print(f"OCR STARTED path={file_path} extension={extension}", flush=True)
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
        print(
            f"OCR FINISHED path={file_path} chars={len(text.strip())} "
            f"elapsed={elapsed:.2f}s backend={_ocr_backend}",
            flush=True,
        )
        logger.info(
            "OCR FINISHED path=%s chars=%s elapsed=%.2fs backend=%s",
            file_path,
            len(text.strip()),
            elapsed,
            _ocr_backend,
        )
        return text.strip()
    except Exception:
        elapsed = time.monotonic() - started
        print(
            f"OCR FAILED path={file_path} elapsed={elapsed:.2f}s\n{traceback.format_exc()}",
            flush=True,
        )
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
        logger.error("OCR timed out after %ss for %s", OCR_TIMEOUT_SECONDS, file_path)
        print(f"OCR TIMEOUT after {OCR_TIMEOUT_SECONDS}s for {file_path}", flush=True)
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

    Never returns an empty-text fallback before OCR has been attempted for
    PDF/image uploads.
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
            print(
                f"PDF selectable text unavailable: {_format_exception(exc)}",
                flush=True,
            )

        print(
            f"PDF selectable text chars={len(selectable)} threshold={SELECTABLE_TEXT_THRESHOLD}",
            flush=True,
        )
        logger.info(
            "PDF selectable text chars=%s threshold=%s",
            len(selectable),
            SELECTABLE_TEXT_THRESHOLD,
        )

        if len(selectable) > SELECTABLE_TEXT_THRESHOLD:
            logger.info("Using selectable PDF text (OCR not required)")
            return selectable, False

        print("Selectable PDF text insufficient; invoking OCR", flush=True)
        return _run_ocr(str(path), extension), True

    if extension in IMAGE_EXTENSIONS:
        print(f"Image upload detected; invoking OCR for {extension}", flush=True)
        return _run_ocr(str(path), extension), True

    raise ResumeParseError(
        "Unsupported file type. Only PDF, DOCX, PNG, JPG, and JPEG are allowed."
    )
