import httpx

from ingestion.normalize import experience_level, fingerprint
from ingestion.runner import ADAPTERS, sources
from ml.features.skills import extract_skills
from pipelines.common import read, write


def main() -> None:
    raw = read("data/raw/snapshot.json")
    jobs = {}
    with httpx.Client() as client:
        for config in sources():
            adapter = ADAPTERS[config.name](config, client)
            for payload in adapter.records(raw[config.name]):
                item = adapter.parse(payload)
                key = fingerprint(item)
                if key not in jobs:
                    jobs[key] = {
                        "id": key,
                        **item.model_dump(mode="json", exclude={"payload"}),
                        "skills": extract_skills(item.description + " " + item.title),
                        "experience_level": experience_level(item.title),
                        "source_refs": [],
                    }
                jobs[key]["source_refs"].append(f"{item.source_name}:{item.source_job_id}")
    write("data/interim/jobs.json", sorted(jobs.values(), key=lambda job: job["id"]))


if __name__ == "__main__":
    main()
