import json
import os
import sys

import httpx

API_BASE = "http://localhost:8000"


def main() -> None:
    with httpx.Client(timeout=10) as client:
        failures = 0

        health = client.get(f"{API_BASE}/health")
        print("health", health.status_code, health.json())
        if health.status_code != 200:
            failures += 1

        match_payload = {
            "candidate": {
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
                "skills": ["python", "fastapi"],
                "experience": [],
            },
            "job": {
                "job_title": "Software Intern",
                "company": "Example",
                "application_url": "https://example.com",
                "source": "test",
            },
        }

        token = os.getenv("SMOKE_BEARER_TOKEN")
        headers = {"Authorization": f"Bearer {token}"} if token else None
        match = client.post(f"{API_BASE}/match", json=match_payload, headers=headers)
        print("match", match.status_code, json.dumps(match.json(), indent=2))

        # /match requires auth; without a token we expect 401 as a valid smoke outcome.
        if token and match.status_code != 200:
            failures += 1
        if not token and match.status_code not in {200, 401}:
            failures += 1

        if failures:
            raise SystemExit(1)

        print("smoke_result ok")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - simple script error reporting
        print(f"smoke_result failed: {exc}", file=sys.stderr)
        raise
