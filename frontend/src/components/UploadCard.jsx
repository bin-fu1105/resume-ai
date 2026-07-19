import { useRef, useState } from "react";
import { formatFileSize } from "../utils/formatFileSize";
import Spinner from "./ui/Spinner";

function UploadIcon({ active }) {
  return (
    <div
      className={[
        "mb-3 flex h-14 w-14 items-center justify-center rounded-2xl transition",
        active
          ? "bg-accent text-white shadow-md shadow-accent/25"
          : "bg-accent-soft text-accent",
      ].join(" ")}
      aria-hidden="true"
    >
      <svg
        className="h-7 w-7"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M12 16V4" />
        <path d="M7 9l5-5 5 5" />
        <path d="M20 16.5V18a2 2 0 01-2 2H6a2 2 0 01-2-2v-1.5" />
      </svg>
    </div>
  );
}

function UploadCard({
  file,
  uploadStatus,
  uploadProgress,
  uploadError,
  uploadResult,
  onFileSelect,
}) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const dragDepthRef = useRef(0);

  const handleFiles = (files) => {
    const nextFile = files?.[0];
    if (nextFile) {
      onFileSelect(nextFile);
    }
  };

  const dropZoneClass = [
    "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-10 text-center transition-all duration-200 sm:py-12",
    isDragging
      ? "scale-[1.01] border-accent bg-accent-soft shadow-inner ring-4 ring-accent/15"
      : "border-line bg-canvas/70 hover:border-accent hover:bg-accent-soft/40",
    uploadStatus === "uploading" ? "pointer-events-none opacity-80" : "",
  ].join(" ");

  return (
    <section className="panel-card min-w-0" aria-labelledby="resume-upload-heading">
      <div className="mb-4">
        <h2
          id="resume-upload-heading"
          className="font-display text-base font-semibold tracking-tight text-ink"
        >
          Resume Upload
        </h2>
        <p className="mt-1 text-sm text-muted">
          Drag & drop or click to upload a PDF or DOCX resume (max 10 MB).
        </p>
      </div>

      <div
        className={dropZoneClass}
        onClick={() => inputRef.current?.click()}
        onDragEnter={(e) => {
          e.preventDefault();
          e.stopPropagation();
          dragDepthRef.current += 1;
          setIsDragging(true);
        }}
        onDragOver={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setIsDragging(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          e.stopPropagation();
          dragDepthRef.current -= 1;
          if (dragDepthRef.current <= 0) {
            dragDepthRef.current = 0;
            setIsDragging(false);
          }
        }}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          dragDepthRef.current = 0;
          setIsDragging(false);
          handleFiles(e.dataTransfer.files);
        }}
        role="button"
        tabIndex={0}
        aria-label="Upload resume. Drag and drop or press Enter to browse files."
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
      >
        {uploadStatus === "uploading" ? (
          <>
            <Spinner label="Uploading resume" />
            <span className="mt-3 font-display text-sm font-semibold text-ink">
              Uploading...
            </span>
            <span className="mt-1 text-xs text-muted">
              {uploadProgress}% complete
            </span>
          </>
        ) : (
          <>
            <UploadIcon active={isDragging} />
            <span className="font-display text-sm font-semibold text-ink">
              {isDragging
                ? "Drop your resume to upload"
                : "Drop resume here or click to browse"}
            </span>
            <span className="mt-1 text-xs text-muted">
              Supports .pdf and .docx
            </span>
          </>
        )}

        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="sr-only"
          aria-hidden="true"
          tabIndex={-1}
          onChange={(e) => {
            handleFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {file && (
        <div className="mt-4 rounded-xl bg-canvas px-4 py-3 text-sm">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate font-medium text-ink">{file.name}</p>
              <p className="mt-1 text-muted">{formatFileSize(file.size)}</p>
            </div>
            {uploadStatus === "uploading" && (
              <Spinner label="Upload in progress" />
            )}
          </div>

          {(uploadStatus === "uploading" || uploadStatus === "success") && (
            <div className="mt-3">
              <div className="h-2 overflow-hidden rounded-full bg-line">
                <div
                  className={`h-full rounded-full transition-all ${
                    uploadStatus === "success" ? "bg-accent" : "bg-accent/80"
                  }`}
                  style={{
                    width: `${uploadStatus === "success" ? 100 : uploadProgress}%`,
                  }}
                  role="progressbar"
                  aria-valuenow={
                    uploadStatus === "success" ? 100 : uploadProgress
                  }
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label="Upload progress"
                />
              </div>
            </div>
          )}
        </div>
      )}

      {uploadStatus === "success" && uploadResult && (
        <div
          className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800"
          role="status"
        >
          Upload successful — {uploadResult.original_filename || file?.name} (
          {formatFileSize(uploadResult.size ?? file?.size)})
        </div>
      )}

      {uploadStatus === "error" && uploadError && (
        <div
          className="mt-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          role="alert"
        >
          {uploadError}
        </div>
      )}

      {!file && uploadStatus === "idle" && (
        <p className="mt-3 text-sm text-muted">No file selected</p>
      )}
    </section>
  );
}

export default UploadCard;
