from difflib import SequenceMatcher

from apps.api.app.models.entities import Job
from ingestion.normalize import normalized


def possible_duplicates(jobs: list[Job]) -> list[dict[str, str | float]]:
    """Diagnostic only: similar titles are not evidence of identical requisitions."""
    pairs: list[dict[str, str | float]] = []
    for index, left in enumerate(jobs):
        for right in jobs[index + 1 :]:
            if left.company_id != right.company_id or normalized(left.location) != normalized(
                right.location
            ):
                continue
            similarity = SequenceMatcher(
                None, normalized(left.title), normalized(right.title)
            ).ratio()
            if similarity >= 0.88:
                pairs.append(
                    {"left_id": left.id, "right_id": right.id, "similarity": round(similarity, 4)}
                )
    return pairs
