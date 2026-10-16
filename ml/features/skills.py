import re

SKILLS: dict[str, tuple[str, ...]] = {
    "python": ("python",),
    "sql": ("sql", "postgresql", "postgres", "mysql"),
    "javascript": ("javascript", "js"),
    "typescript": ("typescript",),
    "react": ("react", "react.js", "reactjs"),
    "java": ("java",),
    "go": ("golang",),
    "c++": ("c++",),
    "c#": ("c#",),
    "docker": ("docker",),
    "aws": ("aws", "amazon web services"),
    "kubernetes": ("kubernetes", "k8s"),
    "git": ("git",),
    "linux": ("linux",),
    "machine learning": ("machine learning",),
    "scikit-learn": ("scikit-learn", "sklearn"),
    "pytorch": ("pytorch",),
    "tensorflow": ("tensorflow",),
    "pandas": ("pandas",),
    "numpy": ("numpy",),
    "fastapi": ("fastapi",),
    "django": ("django",),
    "node.js": ("node.js", "nodejs"),
    "html": ("html",),
    "css": ("css",),
    "spark": ("apache spark", "pyspark"),
    "airflow": ("airflow",),
    "mlflow": ("mlflow",),
    "dvc": ("dvc",),
    "terraform": ("terraform",),
    "excel": ("excel",),
    "tableau": ("tableau",),
    "figma": ("figma",),
    "rust": ("rust",),
}


def extract_skills(text: str) -> list[str]:
    return sorted(
        skill
        for skill, aliases in SKILLS.items()
        if any(
            re.search(r"(?<![\w])" + re.escape(alias) + r"(?![\w])", text, re.I)
            for alias in aliases
        )
    )


def normalize_skills(skills: list[str]) -> list[str]:
    aliases = {alias: skill for skill, variants in SKILLS.items() for alias in variants}
    return sorted(
        {
            aliases.get(skill.strip().casefold(), skill.strip().casefold())
            for skill in skills
            if skill.strip()
        }
    )
