

from typing import Any, Dict, List


def build_quality_report(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    
    if not results:
        return {
            "total_pages": 0,
            "average_score": 0.0,
            "minimum_score": 0,
            "maximum_score": 0,
            "failed_pages": 0,
            "decision": "fallback",
            "pages": [],
        }

    scores = [result.get("quality_score", 0) for result in results]
    average_score = sum(scores) / len(scores)
    failed_pages = len([score for score in scores if score < 75])
    return {
        "total_pages": len(results),
        "average_score": average_score,
        "minimum_score": min(scores),
        "maximum_score": max(scores),
        "failed_pages": failed_pages,
        "decision": "fallback" if failed_pages > 0 else "accept",
        "pages": results,
    }
