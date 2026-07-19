// Production: same-origin relative paths (Vercel rewrites /upload etc. to backend).
// Local dev: talk to FastAPI on :8000 unless VITE_API_URL overrides.
const API_BASE =
  import.meta.env.VITE_API_URL ??
  (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");
const ALLOWED_EXTENSIONS = [".pdf", ".docx"];
const MAX_FILE_SIZE = 10 * 1024 * 1024;

export function validateResumeFile(file) {
  if (!file) {
    return "Please select a resume file.";
  }

  const name = file.name.toLowerCase();
  const isAllowed = ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext));

  if (!isAllowed) {
    return "Unsupported file type. Only PDF and DOCX are allowed.";
  }

  if (file.size > MAX_FILE_SIZE) {
    return "File exceeds maximum size of 10 MB.";
  }

  if (file.size === 0) {
    return "File is empty.";
  }

  return null;
}

export function uploadResumeFile(file, { onProgress } = {}) {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/upload`);

    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable || typeof onProgress !== "function") {
        return;
      }

      const percent = Math.round((event.loaded / event.total) * 100);
      onProgress(percent);
    };

    xhr.onload = () => {
      let data = null;

      try {
        data = JSON.parse(xhr.responseText || "{}");
      } catch {
        reject(new Error("Invalid response from server."));
        return;
      }

      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(data);
        return;
      }

      const message =
        typeof data.detail === "string"
          ? data.detail
          : data.error || "Upload failed.";
      reject(new Error(message));
    };

    xhr.onerror = () => {
      reject(new Error("Network error while uploading."));
    };

    xhr.send(formData);
  });
}

export { API_BASE };
