import re
from .models import ChangeSummary

CATEGORY_RULES = {
    "terraform": (r"\.tf$", r"\.tfvars$"),
    "kubernetes": (r"(^|/)k8s/", r"deployment\.ya?ml$", r"service\.ya?ml$", r"helm"),
    "ci": (r"\.github/workflows/", r"Jenkinsfile", r"\.gitlab-ci\.yml$"),
    "docker": (r"Dockerfile", r"docker-compose"),
    "config": (r"\.env", r"config.*\.(ya?ml|json|toml)$"),
    "database": (r"migrations?/", r"\.sql$"),
}

def parse_diff(diff: str) -> ChangeSummary:
    files = re.findall(r"^diff --git a/(\S+) b/", diff, flags=re.M)
    added = sum(1 for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff.splitlines() if l.startswith("-") and not l.startswith("---"))
    cats = set()
    for f in files:
        matched = False
        for cat, patterns in CATEGORY_RULES.items():
            if any(re.search(p, f) for p in patterns):
                cats.add(cat)
                matched = True
        if not matched:
            cats.add("app")
    return ChangeSummary(files=files, added=added, removed=removed, categories=sorted(cats))
