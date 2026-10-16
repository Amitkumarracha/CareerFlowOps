import hashlib
import html
import re
from html.parser import HTMLParser

from ingestion.base import RawJob


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def plain_text(value: str) -> str:
    parser = TextParser()
    parser.feed(html.unescape(value))
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def normalized(value: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", value.casefold()).split())


def fingerprint(job: RawJob) -> str:
    key = "|".join(normalized(value) for value in [job.company, job.title, job.location])
    return hashlib.sha256(key.encode()).hexdigest()


def experience_level(title: str) -> str | None:
    for pattern, level in [
        (r"\bintern\b", "internship"),
        (r"\b(junior|entry|graduate)\b", "entry"),
        (r"\b(senior|staff|principal|lead)\b", "senior"),
    ]:
        if re.search(pattern, title, re.I):
            return level
    return None
