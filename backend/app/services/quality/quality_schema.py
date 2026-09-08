from typing import Any, Dict, List

# Required sections in the final merged summary.
REQUIRED_SECTIONS = [
    "metadata",
    "main_topic",
    "problem_statement",
    "objectives",
    "methodology",
    "main_results",
    "scientific_contributions",
    "limitations",
    "future_work",
    "keywords",
    "executive_summary",
    "key_takeaways",
]

# Valid final decisions.
VALID_DECISIONS = {"PASS", "REVIEW", "FAIL"}
VALID_SOURCE_AVAILABILITY = {
    "AVAILABLE",
    "PARTIAL",
    "NOT_AVAILABLE",
}


def build_empty_quality_report() -> Dict[str, Any]:
    """Return the expected structure for a quality assessment report."""

    section_template = {
        "source_availability": "NOT_AVAILABLE",
        "score": 0,
        "content_coverage": 0,
        "fidelity": 0,
        "readability": 0,
        "noise": 0,
        "issues": [],
    }

    return {
        "overall_score": 0,
        "decision": "FAIL",
        "sections": {
            section: section_template.copy()
            for section in REQUIRED_SECTIONS
        },
        "global_checks": {
            "metadata_accuracy": 0,
            "keyword_quality": 0,
            "numerical_accuracy": 0,
            "factual_accuracy": 0,
            "missing_information_handling": 0,
        },
        "critical_errors": [],
        "recommendations": [],
    }


def _validate_score(value: Any, field_name: str) -> int:
    """Validate a score that must be between 0 and 10."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a number between 0 and 10.")

    if not 0 <= value <= 10:
        raise ValueError(f"{field_name} must be between 0 and 10.")

    return int(round(value))

def calculate_overall_score(report: Dict[str, Any]) -> int:
    """Calculate the overall summary quality score deterministically."""

    sections = report["sections"]

    applicable_scores = []

    for section in sections.values():
        source_availability = section["source_availability"]

        if source_availability in {"AVAILABLE", "PARTIAL"}:
            applicable_scores.append(section["score"])

    section_quality = (
        sum(applicable_scores) / len(applicable_scores)
        if applicable_scores
        else 0
    )

    global_checks = report["global_checks"]

    global_scores = [
        global_checks["metadata_accuracy"],
        global_checks["keyword_quality"],
        global_checks["numerical_accuracy"],
        global_checks["factual_accuracy"],
        global_checks["missing_information_handling"],
    ]

    global_quality = sum(global_scores) / len(global_scores)

    base_score = (
        section_quality * 0.60
        + global_quality * 0.40
    )

    critical_errors = report["critical_errors"]

    critical_error_count = len(critical_errors)

    if critical_error_count == 1:
        base_score -= 1

    elif critical_error_count >= 2:
        base_score -= 2

    return max(0, min(10, int(round(base_score))))

def calculate_decision(report: Dict[str, Any]) -> str:
    """Calculate the final quality decision deterministically."""

    overall_score = report["overall_score"]
    critical_errors = report["critical_errors"]

    if critical_errors and overall_score < 8:
        return "FAIL"

    if overall_score >= 8:
        return "PASS"

    if overall_score >= 6:
        return "REVIEW"

    return "FAIL"

def validate_quality_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize a Judge LLM quality report.

    Raises:
        ValueError: if the report does not respect the expected structure.
    """

    if not isinstance(report, dict):
        raise ValueError("Quality report must be a JSON object.")

    if "sections" not in report:
        raise ValueError("Missing 'sections'.")

    if "global_checks" not in report:
        raise ValueError("Missing 'global_checks'.")

    if "critical_errors" not in report:
        raise ValueError("Missing 'critical_errors'.")

    if "recommendations" not in report:
        raise ValueError("Missing 'recommendations'.")

    report["overall_score"] = calculate_overall_score(report)
    report["decision"] = calculate_decision(report)


    if report["decision"] not in VALID_DECISIONS:
        raise ValueError(
            f"decision must be one of: {', '.join(sorted(VALID_DECISIONS))}."
        )

    sections = report["sections"]

    if not isinstance(sections, dict):
        raise ValueError("'sections' must be an object.")

    for section_name in REQUIRED_SECTIONS:
        if section_name not in sections:
            raise ValueError(
                f"Missing required section assessment: '{section_name}'."
            )

        section = sections[section_name]

        if not isinstance(section, dict):
            raise ValueError(
                f"Section '{section_name}' must be an object."
            )
        if "source_availability" not in section:
            raise ValueError(
                f"Missing 'source_availability' in section '{section_name}'."
            )

        if section["source_availability"] not in VALID_SOURCE_AVAILABILITY:
            raise ValueError(
                f"Invalid source_availability in section '{section_name}'. "
                f"Expected one of: {', '.join(sorted(VALID_SOURCE_AVAILABILITY))}."
    )

        for field in (
            "score",
            "content_coverage",
            "fidelity",
            "readability",
            "noise",
        ):
            if field not in section:
                raise ValueError(
                    f"Missing '{field}' in section '{section_name}'."
                )

            section[field] = _validate_score(
                section[field],
                f"{section_name}.{field}",
            )

        if "issues" not in section:
            section["issues"] = []

        if not isinstance(section["issues"], list):
            raise ValueError(
                f"'{section_name}.issues' must be a list."
            )

    global_checks = report["global_checks"]

    if not isinstance(global_checks, dict):
        raise ValueError("'global_checks' must be an object.")

    for field in (
        "metadata_accuracy",
        "keyword_quality",
        "numerical_accuracy",
        "factual_accuracy",
        "missing_information_handling",
    ):
        if field not in global_checks:
            raise ValueError(
                f"Missing global check: '{field}'."
            )

        global_checks[field] = _validate_score(
            global_checks[field],
            f"global_checks.{field}",
        )

    if not isinstance(report["critical_errors"], list):
        raise ValueError("'critical_errors' must be a list.")

    if not isinstance(report["recommendations"], list):
        raise ValueError("'recommendations' must be a list.")

    return report