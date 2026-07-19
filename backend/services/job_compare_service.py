"""Compare one resume against multiple job descriptions via the ATS engine."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from services.claude_service import ClaudeService, ClaudeServiceError


def _average_match(resume_match: dict[str, Any] | None) -> int:
    if not isinstance(resume_match, dict) or not resume_match:
        return 0

    values: list[int] = []
    for value in resume_match.values():
        try:
            values.append(max(0, min(100, int(value))))
        except (TypeError, ValueError):
            continue

    if not values:
        return 0
    return round(sum(values) / len(values))


def _as_strength_labels(items: list[Any]) -> list[str]:
    labels: list[str] = []
    for item in items or []:
        if isinstance(item, dict):
            text = str(item.get("title") or item.get("reason") or "").strip()
        else:
            text = str(item).strip()
        if text:
            labels.append(text)
        if len(labels) >= 5:
            break
    return labels


def _as_skill_labels(items: list[Any]) -> list[str]:
    labels: list[str] = []
    for item in items or []:
        if isinstance(item, dict):
            text = str(item.get("skill") or item.get("title") or "").strip()
        else:
            text = str(item).strip()
        if text:
            labels.append(text)
        if len(labels) >= 5:
            break
    return labels


def _recommendation(score: int, is_best: bool) -> str:
    if is_best:
        return "Best overall fit — prioritize this application."
    if score >= 80:
        return "Strong fit. Tailor keywords slightly, then apply."
    if score >= 65:
        return "Promising fit. Close skill gaps before applying."
    if score >= 50:
        return "Partial fit. Rewrite toward this JD before applying."
    return "Weak fit. Consider other roles or a major rewrite."


class JobCompareService:
    """Runs independent ATS analyses and ranks companies by score."""

    MAX_JOBS = 5

    def __init__(self, claude_service: ClaudeService | None = None):
        self.claude_service = claude_service or ClaudeService()

    def _analyze_one(
        self, company: str, job_description: str, resume_text: str
    ) -> dict[str, Any]:
        analysis = self.claude_service.analyze_resume(
            resume_text=resume_text,
            job_description=job_description,
        )

        score = int(analysis.get("ats_score") or 0)
        strengths = _as_strength_labels(analysis.get("strengths") or [])
        missing = _as_skill_labels(analysis.get("missing_skills") or [])
        summary = str(
            analysis.get("ats_explanation")
            or analysis.get("optimized_summary")
            or ""
        ).strip()

        return {
            "company": company,
            "score": max(0, min(100, score)),
            "resume_match": _average_match(analysis.get("resume_match")),
            "strengths": strengths,
            "missing_skills": missing,
            "summary": summary,
        }

    def compare_jobs(
        self,
        resume_text: str,
        jobs: list[dict[str, str]],
    ) -> dict[str, Any]:
        if not resume_text.strip():
            raise ClaudeServiceError("Resume text is empty.")

        if not jobs:
            raise ClaudeServiceError("At least one job is required.")

        if len(jobs) > self.MAX_JOBS:
            raise ClaudeServiceError(
                f"Compare up to {self.MAX_JOBS} job descriptions at a time."
            )

        prepared: list[tuple[str, str]] = []
        seen_companies: set[str] = set()

        for index, job in enumerate(jobs, start=1):
            company = str(job.get("company") or "").strip() or f"Job {index}"
            # Keep company labels unique for best_match clarity.
            base = company
            suffix = 2
            while company.lower() in seen_companies:
                company = f"{base} ({suffix})"
                suffix += 1
            seen_companies.add(company.lower())

            jd = str(job.get("job_description") or "").strip()
            if not jd:
                raise ClaudeServiceError(
                    f"Job description is required for {company}."
                )
            prepared.append((company, jd))

        results_by_company: dict[str, dict[str, Any]] = {}
        errors: list[str] = []

        # Parallelize a bit, but keep concurrency modest for API stability.
        workers = min(3, len(prepared))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(self._analyze_one, company, jd, resume_text): company
                for company, jd in prepared
            }
            for future in as_completed(futures):
                company = futures[future]
                try:
                    results_by_company[company] = future.result()
                except ClaudeServiceError as exc:
                    errors.append(f"{company}: {exc}")
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{company}: {exc}")

        if not results_by_company:
            detail = "; ".join(errors) if errors else "No analyses completed."
            raise ClaudeServiceError(detail)

        # Preserve input order, then attach recommendations after best known.
        ordered = [
            results_by_company[company]
            for company, _ in prepared
            if company in results_by_company
        ]

        best = max(ordered, key=lambda item: item["score"])
        best_company = best["company"]

        for item in ordered:
            item["recommendation"] = _recommendation(
                item["score"], item["company"] == best_company
            )

        reason = (
            f"Highest ATS score ({best['score']}) with the strongest keyword "
            "and competency alignment for this resume."
        )
        if best.get("summary"):
            # Keep reason short for the recommendation panel.
            first = best["summary"].split(".")[0].strip()
            if first and len(first) < 160:
                reason = f"{first}."

        payload: dict[str, Any] = {
            "results": ordered,
            "best_match": best_company,
            "reason": reason,
        }
        if errors:
            payload["partial_errors"] = errors
        return payload
