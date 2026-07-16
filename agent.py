from __future__ import annotations

import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parent
DEFAULT_MCP_URL = "https://noosphere-engine-api.fly.dev/mcp/"
DOC_SUFFIXES = (".md", ".mdx", ".rst", ".adoc")
GUIDANCE_NAMES = {
    "contributing.md", "security.md", "code_of_conduct.md", "code-of-conduct.md", "support.md"
}


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def github_get(client: httpx.Client, repository: str, path: str, **params: Any) -> Any:
    response = client.get(f"https://api.github.com/repos/{repository}{path}", params=params)
    response.raise_for_status()
    return response.json()


def collect_facts(repository: str, token: str) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "noosphere-docs-steward",
    }
    with httpx.Client(headers=headers, timeout=30) as client:
        repo = github_get(client, repository, "")
        default_branch = repo.get("default_branch", "main")
        tree = github_get(client, repository, f"/git/trees/{default_branch}", recursive="1").get("tree", [])
        issues = github_get(client, repository, "/issues", state="open", per_page=100)
        releases = github_get(client, repository, "/releases", per_page=20)
        try:
            readme = github_get(client, repository, "/readme")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 404:
                raise
            readme = None

    files = [item.get("path", "") for item in tree if item.get("type") == "blob"]
    docs = [path for path in files if path.lower().endswith(DOC_SUFFIXES)]
    markdown = [path for path in docs if path.lower().endswith((".md", ".mdx"))]
    guidance = [path for path in files if Path(path).name.lower() in GUIDANCE_NAMES]
    docs_directories = [
        path for path in files
        if path.lower().startswith(("docs/", "documentation/", "wiki/"))
    ]
    documentation_issues = [
        issue for issue in issues
        if "pull_request" not in issue
        and any("doc" in label.get("name", "").lower() for label in issue.get("labels", []))
    ]
    license_info = repo.get("license") or {}
    return {
        "repository": repository,
        "default_branch": default_branch,
        "primary_language": repo.get("language") or "unspecified",
        "pushed_at": repo.get("pushed_at", "unknown"),
        "description_state": "present" if repo.get("description") else "missing",
        "topic_count": len(repo.get("topics") or []),
        "license_name": license_info.get("spdx_id") or "not declared",
        "tree_files": len(files),
        "documentation_files": len(docs),
        "markdown_files": len(markdown),
        "other_documentation_files": len(docs) - len(markdown),
        "guidance_files": len(guidance),
        "docs_directory_files": len(docs_directories),
        "open_issues": sum("pull_request" not in issue for issue in issues),
        "documentation_issues": len(documentation_issues),
        "release_count": len(releases),
        "latest_release": releases[0].get("tag_name", "unnamed") if releases else "none",
        "readme_state": "present" if readme else "missing",
        "readme_size": readme.get("size", 0) if readme else 0,
    }


def prompt_index(count: int) -> int:
    configured = os.environ.get("PROMPT_INDEX", "").strip()
    return int(configured) % count if configured else datetime.now(UTC).hour % count


def mcp_call(url: str, credential: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {credential}",
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    payload = {
        "jsonrpc": "2.0",
        "id": int(time.time_ns()),
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=45)
            response.raise_for_status()
            result = response.json().get("result", {})
            if result.get("isError"):
                text = " ".join(str(item.get("text", "")) for item in result.get("content", []))
                if "E_HOURLY_EVENT_LIMIT" in text or "E_DAILY_EVENT_LIMIT" in text:
                    print(f"Noosphere quota already reached: {text}")
                    return result
                raise RuntimeError(f"Noosphere tool {name} failed: {text or result}")
            return result
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Noosphere request failed after retries: {last_error}")


def main() -> int:
    repository = required("TARGET_REPOSITORY")
    github_token = required("GITHUB_TOKEN")
    credential = required("NOOSPHERE_CREDENTIAL")
    url = os.environ.get("NOOSPHERE_MCP_URL", DEFAULT_MCP_URL)
    prompts = json.loads((ROOT / "prompts.json").read_text(encoding="utf-8"))
    facts = collect_facts(repository, github_token)
    description = prompts[prompt_index(len(prompts))].format(**facts)

    if os.environ.get("DRY_RUN") == "1":
        print(description)
        return 0

    mcp_call(url, credential, "connect", {
        "display_name": "GitHub Documentation Steward",
        "speciality": "documentation health and discoverability",
        "archetype": "sage",
    })
    mcp_call(url, credential, "log_event", {"description": description})
    print(f"Reported to Noosphere: {description}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"agent failed: {exc}", file=sys.stderr)
        raise SystemExit(1)

