import math


def ranking_metrics(
    ranked_ids: list[str], relevance: dict[str, int], k: int = 5
) -> dict[str, float]:
    if k <= 0:
        raise ValueError("k must be positive")
    if len(ranked_ids) != len(set(ranked_ids)):
        raise ValueError("Ranked IDs must be unique")
    top = ranked_ids[:k]
    hits = sum(relevance.get(job_id, 0) > 0 for job_id in top)
    positives = sum(value > 0 for value in relevance.values())
    dcg = sum(
        (2 ** relevance.get(job_id, 0) - 1) / math.log2(index + 2)
        for index, job_id in enumerate(top)
    )
    ideal = sum(
        (2**grade - 1) / math.log2(index + 2)
        for index, grade in enumerate(sorted(relevance.values(), reverse=True)[:k])
    )
    reciprocal = next(
        (
            1 / (index + 1)
            for index, job_id in enumerate(ranked_ids)
            if relevance.get(job_id, 0) > 0
        ),
        0.0,
    )
    return {
        "precision_at_5": hits / k,
        "recall_at_5": hits / positives if positives else 0.0,
        "ndcg_at_5": dcg / ideal if ideal else 0.0,
        "mrr": reciprocal,
    }
