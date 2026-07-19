import { lazy, Suspense, useEffect, useRef, useState } from "react";
import Navbar from "./components/Navbar";
import UploadCard from "./components/UploadCard";
import JobDescriptionCard from "./components/JobDescriptionCard";
import AnalyzeButton from "./components/AnalyzeButton";
import RewriteButton from "./components/RewriteButton";
import AnalysisProgress, { STAGES } from "./components/AnalysisProgress";
import CareerCoachPanel from "./components/CareerCoachPanel";
import CompareView from "./components/CompareView";
import HeatmapView from "./components/HeatmapView";
import InterviewView from "./components/InterviewView";
import JobCompareView from "./components/JobCompareView";
import ToastContainer from "./components/Toast";
import ErrorState from "./components/ui/ErrorState";
import Skeleton from "./components/ui/Skeleton";
import { useToast } from "./hooks/useToast";
import {
  toFriendlyAnalyzeError,
  toFriendlyRewriteError,
  toFriendlyUploadError,
} from "./utils/friendlyError";
import {
  API_BASE,
  uploadResumeFile,
  validateResumeFile,
} from "./utils/uploadFile";

const ResultsSection = lazy(() => import("./components/ResultsSection"));
const SECTION_KEYS = [
  "summary",
  "experience",
  "projects",
  "skills",
  "education",
];

function ResultsFallback() {
  return (
    <section className="mt-10" aria-label="Loading results">
      <div className="mb-5 space-y-2">
        <div className="skeleton-block h-3 w-20 rounded" />
        <div className="skeleton-block h-7 w-48 rounded" />
        <div className="skeleton-block h-4 w-72 max-w-full rounded" />
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        <div className="panel-card">
          <Skeleton variant="score" />
        </div>
        <div className="panel-card">
          <Skeleton variant="bars" />
        </div>
        <div className="panel-card">
          <Skeleton variant="chips" />
        </div>
        <div className="panel-card md:col-span-2 xl:col-span-3">
          <Skeleton variant="list" />
        </div>
      </div>
    </section>
  );
}

function App() {
  const [file, setFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState("idle");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState("");
  const [uploadResult, setUploadResult] = useState(null);

  const [jobDescription, setJobDescription] = useState("");
  const [jobDescriptionError, setJobDescriptionError] = useState("");
  const [loading, setLoading] = useState(false);
  const [rewriting, setRewriting] = useState(false);
  const [analysisStage, setAnalysisStage] = useState(0);
  const [showResults, setShowResults] = useState(false);

  const [score, setScore] = useState(null);
  const [atsExplanation, setAtsExplanation] = useState("");
  const [dimensions, setDimensions] = useState({});
  const [strengths, setStrengths] = useState([]);
  const [missingSkills, setMissingSkills] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [optimizedSummary, setOptimizedSummary] = useState("");
  const [analysisPayload, setAnalysisPayload] = useState(null);
  const [rewrittenResume, setRewrittenResume] = useState(null);
  const [sectionInsights, setSectionInsights] = useState([]);
  const [rewriteError, setRewriteError] = useState("");
  const [rewriteSection, setRewriteSection] = useState(null);
  const [rewriteApplied, setRewriteApplied] = useState(false);
  const [applyingRewrite, setApplyingRewrite] = useState(false);
  const [analyzingAgain, setAnalyzingAgain] = useState(false);
  const [baselineAtsScore, setBaselineAtsScore] = useState(null);
  const [afterAtsScore, setAfterAtsScore] = useState(null);
  const [activeTab, setActiveTab] = useState("dashboard");

  const [error, setError] = useState("");
  const stageTimersRef = useRef([]);
  const resultsRef = useRef(null);
  const { toasts, showToast, dismissToast } = useToast();

  useEffect(() => {
    return () => {
      stageTimersRef.current.forEach(clearTimeout);
    };
  }, []);

  const clearStageTimers = () => {
    stageTimersRef.current.forEach(clearTimeout);
    stageTimersRef.current = [];
  };

  const startStageProgress = () => {
    clearStageTimers();
    setAnalysisStage(0);

    STAGES.slice(1).forEach((_, index) => {
      const timer = setTimeout(() => {
        setAnalysisStage(index + 1);
      }, (index + 1) * 900);
      stageTimersRef.current.push(timer);
    });
  };

  const resetAnalysisState = ({ keepOptimization = false } = {}) => {
    setScore(null);
    setAtsExplanation("");
    setDimensions({});
    setStrengths([]);
    setMissingSkills([]);
    setSuggestions([]);
    setOptimizedSummary("");
    setAnalysisPayload(null);
    setShowResults(false);
    setAfterAtsScore(null);

    if (!keepOptimization) {
      setRewrittenResume(null);
      setSectionInsights([]);
      setRewriteError("");
      setRewriteSection(null);
      setRewriteApplied(false);
      setBaselineAtsScore(null);
    }
  };

  const handleJobDescriptionChange = (e) => {
    setJobDescription(e.target.value);
    if (jobDescriptionError) {
      setJobDescriptionError("");
    }
  };

  const handleFileSelect = async (selectedFile) => {
    setFile(selectedFile);
    setUploadResult(null);
    setUploadError("");
    setUploadProgress(0);
    setError("");
    resetAnalysisState();

    const validationError = validateResumeFile(selectedFile);
    if (validationError) {
      setUploadStatus("error");
      setUploadError(validationError);
      showToast(validationError, "error");
      return;
    }

    setUploadStatus("uploading");

    try {
      const result = await uploadResumeFile(selectedFile, {
        onProgress: setUploadProgress,
      });

      setUploadProgress(100);
      setUploadResult(result);
      setUploadStatus("success");
      showToast("Resume uploaded successfully.", "success");
    } catch (err) {
      const message = toFriendlyUploadError(err);
      setUploadStatus("error");
      setUploadError(message);
      setUploadResult(null);
      showToast(message, "error");
    }
  };

  const handleAnalyze = async () => {
    if (uploadStatus !== "success" || !uploadResult?.filename) {
      showToast("Please upload a resume successfully before analyzing.", "error");
      return;
    }

    if (!jobDescription.trim()) {
      setJobDescriptionError("Please enter a job description.");
      showToast("Please enter a job description.", "error");
      return;
    }

    setJobDescriptionError("");
    setLoading(true);
    setError("");
    resetAnalysisState();
    startStageProgress();

    try {
      const response = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          filename: uploadResult.filename,
          job_description: jobDescription,
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        clearStageTimers();
        const message = toFriendlyAnalyzeError(data.detail || data.error || data);
        setError(message);
        showToast(message, "error");
        setLoading(false);
        return;
      }

      if (data.error) {
        clearStageTimers();
        const message = toFriendlyAnalyzeError(data.error);
        setError(message);
        showToast(message, "error");
        setLoading(false);
        return;
      }

      const analysis = data.analysis || {};

      clearStageTimers();
      setAnalysisStage(STAGES.length - 1);

      setScore(analysis.ats_score ?? null);
      setAtsExplanation(analysis.ats_explanation || "");
      setDimensions(analysis.resume_match || {});
      setStrengths(analysis.strengths || []);
      setMissingSkills(analysis.missing_skills || []);
      setSuggestions(analysis.suggestions || []);
      setOptimizedSummary(analysis.optimized_summary || "");
      setAnalysisPayload(analysis);
      setBaselineAtsScore(analysis.ats_score ?? null);
      setAfterAtsScore(null);
      setRewriteApplied(false);

      setTimeout(() => {
        setLoading(false);
        setShowResults(true);
        setActiveTab("heatmap");
        showToast("Analysis complete. Optimize to improve each section.", "success");
        requestAnimationFrame(() => {
          resultsRef.current?.scrollIntoView({
            behavior: "smooth",
            block: "start",
          });
        });
      }, 450);
    } catch (err) {
      clearStageTimers();
      const message = toFriendlyAnalyzeError(err);
      setError(message);
      showToast(message, "error");
      setLoading(false);
    }
  };

  const handleAnalyzeAgain = async () => {
    if (!uploadResult?.filename || !rewriteApplied) {
      showToast("Apply a rewrite before analyzing again.", "error");
      return;
    }
    if (!jobDescription.trim()) {
      showToast("Please enter a job description.", "error");
      return;
    }

    setAnalyzingAgain(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: uploadResult.filename,
          job_description: jobDescription,
          use_applied: true,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || data.error || "Analyze again failed.");
      }

      const analysis = data.analysis || {};
      setAfterAtsScore(analysis.ats_score ?? null);
      setScore(analysis.ats_score ?? null);
      setAtsExplanation(analysis.ats_explanation || "");
      setDimensions(analysis.resume_match || {});
      setStrengths(analysis.strengths || []);
      setMissingSkills(analysis.missing_skills || []);
      setSuggestions(analysis.suggestions || []);
      setOptimizedSummary(analysis.optimized_summary || "");
      setAnalysisPayload(analysis);
      setShowResults(true);
      showToast("Optimized resume analyzed. Compare Before vs After ATS.", "success");
    } catch (err) {
      const message = toFriendlyAnalyzeError(err);
      setError(message);
      showToast(message, "error");
    } finally {
      setAnalyzingAgain(false);
    }
  };

  const handleApplyRewrite = async () => {
    if (!uploadResult?.filename || !rewrittenResume) {
      showToast("Generate an optimized rewrite first.", "error");
      return;
    }

    setApplyingRewrite(true);
    try {
      const response = await fetch(`${API_BASE}/apply-rewrite`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: uploadResult.filename,
          rewrite: rewrittenResume,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || data.error || "Apply rewrite failed.");
      }

      setRewriteApplied(true);
      setAfterAtsScore(null);
      showToast("Rewrite applied to your working resume.", "success");
    } catch (err) {
      showToast(toFriendlyRewriteError(err), "error");
    } finally {
      setApplyingRewrite(false);
    }
  };

  const mergeSectionRewrite = (incoming, focusSection) => {
    if (!focusSection || !SECTION_KEYS.includes(focusSection)) {
      return incoming;
    }

    if (!rewrittenResume) {
      return incoming;
    }

    return {
      ...rewrittenResume,
      [focusSection]: incoming[focusSection],
    };
  };

  const handleRewrite = async (section = null) => {
    if (uploadStatus !== "success" || !uploadResult?.filename) {
      showToast("Please upload a resume successfully before rewriting.", "error");
      return;
    }

    if (!jobDescription.trim()) {
      setJobDescriptionError("Please enter a job description.");
      showToast("Please enter a job description.", "error");
      return;
    }

    if (!analysisPayload) {
      showToast("Analyze your resume first.", "error");
      return;
    }

    const focusSection =
      typeof section === "string" && SECTION_KEYS.includes(section)
        ? section
        : null;

    setRewriting(true);
    setRewriteSection(focusSection);
    setRewriteError("");
    setError("");

    try {
      const body = {
        filename: uploadResult.filename,
        job_description: jobDescription,
      };
      if (focusSection) {
        body.section = focusSection;
      }

      const response = await fetch(`${API_BASE}/rewrite`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const message = toFriendlyRewriteError(data.detail || data.error || data);
        setRewriteError(message);
        showToast(message, "error");
        setRewriting(false);
        setRewriteSection(null);
        return;
      }

      const rewritePayload = data.rewrite
        ? data.rewrite
        : {
            summary: data.summary || "",
            experience: data.experience || [],
            projects: data.projects || [],
            skills: data.skills || [],
            education: data.education || [],
          };

      const nextRewrite = mergeSectionRewrite(rewritePayload, focusSection);
      setRewrittenResume(nextRewrite);
      setSectionInsights(data.section_insights || []);
      setRewriteApplied(false);
      setAfterAtsScore(null);
      setShowResults(true);

      if (focusSection) {
        showToast(
          `${focusSection.charAt(0).toUpperCase()}${focusSection.slice(1)} section optimized.`,
          "success",
        );
      } else {
        setActiveTab("optimize");
        showToast("Resume optimized. Review Original vs Optimized.", "success");
      }
    } catch (err) {
      const message = toFriendlyRewriteError(err);
      setRewriteError(message);
      showToast(message, "error");
    }

    setRewriting(false);
    setRewriteSection(null);
  };

  const canAnalyze = uploadStatus === "success" && Boolean(uploadResult?.filename);
  const canRewrite = canAnalyze && Boolean(analysisPayload) && !loading;
  const hasResults =
    showResults &&
    (score !== null ||
      Object.keys(dimensions).length > 0 ||
      missingSkills.length > 0 ||
      suggestions.length > 0 ||
      Boolean(optimizedSummary) ||
      Boolean(rewrittenResume));

  const statusMessage = loading
    ? "AI analysis in progress..."
    : rewriting
      ? "Optimizing resume sections with Claude..."
      : canRewrite
        ? "Analysis ready. Optimize each section, then apply the rewrite."
        : canAnalyze
          ? "Resume uploaded. Add a job description, then analyze."
          : "Upload a resume successfully to enable analysis.";

  return (
    <div className="min-h-screen">
      <a
        href="#workspace"
        className="absolute left-4 top-4 z-50 -translate-y-20 rounded-lg bg-white px-3 py-2 text-sm font-semibold text-ink opacity-0 shadow-md transition focus:translate-y-0 focus:opacity-100 focus:outline-2 focus:outline-offset-2 focus:outline-accent"
      >
        Skip to workspace
      </a>

      <Navbar activeTab={activeTab} onTabChange={setActiveTab} />
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-10">
        <section id="workspace" className="mb-6 scroll-mt-24 sm:mb-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-accent">
                Workspace
              </p>
              <h1 className="font-display text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
                Resume Optimization
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted sm:text-base">
                Upload, analyze, optimize each section, apply the rewrite, then
                compare Before vs After ATS.
              </p>
            </div>

            <div
              className="inline-flex rounded-xl border border-line bg-white p-1 shadow-sm"
              role="tablist"
              aria-label="Workspace views"
            >
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === "dashboard"}
                onClick={() => setActiveTab("dashboard")}
                className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
                  activeTab === "dashboard"
                    ? "bg-accent text-white"
                    : "text-muted hover:text-ink"
                }`}
              >
                Dashboard
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === "heatmap"}
                onClick={() => setActiveTab("heatmap")}
                className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
                  activeTab === "heatmap"
                    ? "bg-accent text-white"
                    : "text-muted hover:text-ink"
                }`}
              >
                Heatmap
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === "optimize"}
                onClick={() => setActiveTab("optimize")}
                className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
                  activeTab === "optimize"
                    ? "bg-accent text-white"
                    : "text-muted hover:text-ink"
                }`}
              >
                Optimize
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === "interview"}
                onClick={() => setActiveTab("interview")}
                className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
                  activeTab === "interview"
                    ? "bg-accent text-white"
                    : "text-muted hover:text-ink"
                }`}
              >
                Interview
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === "jobs"}
                onClick={() => setActiveTab("jobs")}
                className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
                  activeTab === "jobs"
                    ? "bg-accent text-white"
                    : "text-muted hover:text-ink"
                }`}
              >
                Jobs
              </button>
            </div>
          </div>
        </section>

        {activeTab === "optimize" ? (
          <CompareView
            filename={uploadResult?.filename || ""}
            rewrite={rewrittenResume}
            sectionInsights={sectionInsights}
            enabled={Boolean(uploadResult?.filename && rewrittenResume)}
            canOptimize={canRewrite}
            optimizing={rewriting && !rewriteSection}
            baselineAtsScore={baselineAtsScore}
            afterAtsScore={afterAtsScore}
            rewriteApplied={rewriteApplied}
            applying={applyingRewrite}
            analyzingAgain={analyzingAgain}
            onOptimize={() => handleRewrite()}
            onApplyRewrite={handleApplyRewrite}
            onAnalyzeAgain={handleAnalyzeAgain}
          />
        ) : activeTab === "heatmap" ? (
          <HeatmapView
            enabled={Boolean(analysisPayload)}
            overallScore={score}
            atsExplanation={atsExplanation}
            sections={analysisPayload?.sections}
            onRewriteSection={handleRewrite}
            rewriting={rewriting}
            rewriteSection={rewriteSection}
          />
        ) : activeTab === "interview" ? (
          <InterviewView
            filename={uploadResult?.filename || ""}
            jobDescription={jobDescription}
            enabled={canAnalyze}
          />
        ) : activeTab === "jobs" ? (
          <JobCompareView
            filename={uploadResult?.filename || ""}
            enabled={canAnalyze}
          />
        ) : (
          <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.9fr)]">
            <div className="min-w-0 space-y-5" aria-label="Resume Dashboard">
              <section
                className="grid grid-cols-1 gap-4 sm:gap-5 lg:grid-cols-2"
                aria-label="Resume inputs"
              >
                <UploadCard
                  file={file}
                  uploadStatus={uploadStatus}
                  uploadProgress={uploadProgress}
                  uploadError={uploadError}
                  uploadResult={uploadResult}
                  onFileSelect={handleFileSelect}
                />
                <JobDescriptionCard
                  value={jobDescription}
                  onChange={handleJobDescriptionChange}
                  error={jobDescriptionError}
                />
              </section>

              <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
                <div
                  className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row"
                  role="group"
                  aria-label="Primary actions"
                >
                  <AnalyzeButton
                    loading={loading}
                    disabled={!canAnalyze || rewriting}
                    onClick={handleAnalyze}
                  />
                  <RewriteButton
                    loading={rewriting && !rewriteSection}
                    disabled={!canRewrite}
                    disabledReason={
                      !canRewrite && !rewriting
                        ? "Analyze your resume first."
                        : undefined
                    }
                    onClick={() => handleRewrite()}
                  />
                </div>
                <p
                  className="text-xs leading-relaxed text-muted sm:text-sm"
                  aria-live="polite"
                >
                  {statusMessage}
                </p>
              </div>

              {loading && <AnalysisProgress stageIndex={analysisStage} />}

              {error && (
                <ErrorState
                  title="Analysis failed"
                  message={error}
                  onRetry={handleAnalyze}
                  retryLabel="Retry analysis"
                />
              )}

              <Suspense fallback={<ResultsFallback />}>
                <ResultsSection
                  loading={loading}
                  rewriting={rewriting && !rewriteSection}
                  hasResults={hasResults}
                  score={score}
                  atsExplanation={atsExplanation}
                  dimensions={dimensions}
                  strengths={strengths}
                  missingSkills={missingSkills}
                  suggestions={suggestions}
                  optimizedSummary={optimizedSummary}
                  rewrittenResume={rewrittenResume}
                  rewriteError={rewriteError}
                  onRetryRewrite={() => handleRewrite()}
                  resultsRef={resultsRef}
                />
              </Suspense>
            </div>

            <CareerCoachPanel
              filename={uploadResult?.filename || ""}
              jobDescription={jobDescription}
              analysis={analysisPayload}
              rewrite={rewrittenResume}
              enabled={canAnalyze}
            />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
