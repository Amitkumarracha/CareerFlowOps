from pipelines.common import digest, read, write


def main() -> None:
    jobs = read("data/interim/jobs.json")
    labels = read("data/samples/labels.json")
    lookup = {reference: job["id"] for job in jobs for reference in job["source_refs"]}
    queries = labels["queries"]
    ids = [query["id"] for query in queries]
    if len(ids) != len(set(ids)) or set(query["split"] for query in queries) != {
        "train",
        "validation",
        "test",
    }:
        raise ValueError("Queries must be unique and cover train, validation and test splits")
    for query in queries:
        missing = set(query["relevance"]) - set(lookup)
        if missing:
            raise ValueError(f"Labels reference missing snapshot postings: {missing}")
        relevance = {job["id"]: 0 for job in jobs}
        for reference, grade in query["relevance"].items():
            relevance[lookup[reference]] = max(grade, relevance[lookup[reference]])
        query["relevance"] = relevance
    dataset = {
        "jobs": jobs,
        "queries": queries,
        "labels_description": labels["description"],
        "as_of": labels["as_of"],
    }
    dataset["dataset_version"] = digest(dataset)
    write("data/processed/dataset.json", dataset)


if __name__ == "__main__":
    main()
