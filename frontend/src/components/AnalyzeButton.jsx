import Spinner from "./ui/Spinner";

function AnalyzeButton({ loading, disabled, onClick }) {
  const isDisabled = disabled || loading;

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={isDisabled}
      className="btn-primary"
      aria-busy={loading}
      aria-label={loading ? "Analyzing resume" : "Analyze resume"}
    >
      {loading && <Spinner className="h-4 w-4 text-white" label="Analyzing" />}
      {loading ? "Analyzing..." : "Analyze Resume"}
    </button>
  );
}

export default AnalyzeButton;
