const INTERNAL_ERROR_PATTERN =
  /traceback|pydantic|fastapi|starlette|exception|stack|file\s+"|line\s+\d+|at\s+0x|validation error|typeerror|valueerror|keyerror|attributeerror/i;

/**
 * Convert backend/network failures into safe, user-facing copy.
 * Never surface Python/FastAPI internals.
 */
export function toFriendlyError(
  error,
  fallback = "Something went wrong. Please try again."
) {
  let raw = "";

  if (typeof error === "string") {
    raw = error;
  } else if (error && typeof error === "object") {
    if (typeof error.detail === "string") {
      raw = error.detail;
    } else if (typeof error.message === "string") {
      raw = error.message;
    } else if (typeof error.error === "string") {
      raw = error.error;
    }
  }

  raw = raw.trim();
  if (!raw) {
    return fallback;
  }

  if (INTERNAL_ERROR_PATTERN.test(raw) || raw.length > 180) {
    return fallback;
  }

  return raw;
}

export function toFriendlyAnalyzeError(error) {
  return toFriendlyError(
    error,
    "We couldn't analyze your resume. Please try again in a moment."
  );
}

export function toFriendlyRewriteError(error) {
  return toFriendlyError(
    error,
    "We couldn't rewrite your resume. Please try again in a moment."
  );
}

export function toFriendlyUploadError(error) {
  return toFriendlyError(
    error,
    "We couldn't upload your resume. Check the file and try again."
  );
}
