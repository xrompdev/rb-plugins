#!/usr/bin/env python3
"""Patrol prep: steps 1-4 of /patrol as code, plus a Jev pre-pass per PR.

Run from the repo root. Prints one JSON document to stdout: which PRs to review and why the
rest were skipped, and for each PR to review, the checks Jev judged relevant, its coverage
verdicts on the linked issue's requirements and on earlier review comments, and the facts code
can decide (services, environment.ts, Connect, CONTEXT.md apps). It also fetches each PR head
into refs/patrol/<number>. It never approves, comments, or writes outside refs/patrol/*.

Without TYPESAFE_API_KEY, or if a Jev call fails, a PR's `jev` is null and the reviewer runs
the full checklist.
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ME = "xrompdev"
DEPENDABOT_LOGINS = {"dependabot", "dependabot[bot]", "app/dependabot"}
LESSONS_PATH = Path("/home/xromp/obsidian/responsibid-brain/Retros/LESSONS.md")
LARGE_PR_LINES = 500

# Recall over precision: an extra check costs the reviewer a minute, a missed one ships a bug.
APPLIES = 0.3
COVERED = 0.8
NOT_COVERED = 0.2
# Jev's default limit is 32k tokens per question; past ~90k chars of state use its long-context mode.
LONG_CONTEXT_CHARS = 90_000
MAX_STATE_CHARS = 700_000

SERVICES = {
    "apps/server/": "server-graphql",
    "apps/connect/": "server-connect",
    "apps/shortener/": "server-shortener",
    "apps/queue-dispatcher/": "server-queue-dispatcher",
    "apps/zapier-app/": "server-zapier-app",
    "apps/gateway/": "server-gateway",
    "apps/payment/": "server-payment",
    "apps/orchestrator/": "server-orchestrator",
    "apps/projector/": "server-projector",
    "apps/reactor/": "server-reactor",
    "apps/notification/": "server-notification",
    "apps/pdf-service/": "server-pdf-service",
    "apps/temporal-worker/": "server-temporal-worker",
    "apps/queue/": "server-queue",
}

RISK_LEVELS = [
    "Trivial: docs, comments, config text, renames, or test-only changes",
    "Low: a small, contained logic change that comes with tests",
    "Medium: changes shared logic, data writes, or a public contract",
    "High: touches money, auth, tenant scoping, migrations, or event or workflow history",
]

CONDITIONAL_QUESTIONS = {
    "read_after_write": "Does `pr.diff` add or change a database read that must see current data: a read after a "
    "write in the same flow, or a read that decides whether to write (a validation, duplicate check, status or "
    "auth check before a write)?",
    "money": "Does `pr.diff` compute, round, convert, sum or compare money amounts (prices, totals, deposits, "
    "payments, refunds, tax)?",
    "event_or_workflow": "Does `pr.diff` change event-sourced code (aggregates, events, projections, projectors) "
    "or Temporal workflow code?",
}


def gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def gh_json(*args):
    return json.loads(gh(*args) or "null")


def latest(timestamps):
    present = [t for t in timestamps if t]
    return max(present) if present else None


def triage(pr, view):
    """Steps 2-3. Returns (action, reason): action is review, re-review or skip."""
    my_reviews = [r for r in view["reviews"] if (r.get("author") or {}).get("login") == ME]
    if any(r.get("state") == "APPROVED" for r in my_reviews):
        return "skip", "already approved by me"
    last_comment = latest(
        [c["createdAt"] for c in view["comments"] if (c.get("author") or {}).get("login") == ME]
        + [r.get("submittedAt") for r in my_reviews]
    )
    if last_comment is None:
        return "review", "not reviewed yet"
    last_commit = latest([c.get("committedDate") for c in view["commits"]])
    if last_commit and last_commit > last_comment:
        return "re-review", "new commits since my last comment"
    return "skip", "nothing new since my last comment"


def my_earlier_comments(number, view, repo):
    inline = gh_json("api", "--paginate", "--slurp", f"repos/{repo}/pulls/{number}/comments")
    inline = [c for page in inline for c in page]
    return [
        {"where": f"{c['path']}:{c.get('line') or c.get('original_line')}", "url": c["html_url"], "text": c["body"]}
        for c in inline
        if c["user"]["login"] == ME and not c.get("in_reply_to_id")
    ] + [
        {"where": "conversation", "url": c.get("url", ""), "text": c["body"]}
        for c in view["comments"] + view["reviews"]
        if (c.get("author") or {}).get("login") == ME and c.get("body", "").strip()
    ]


def requirements(issue_body):
    return [m.group(1).strip() for m in re.finditer(r"^\s*[-*] \[[ xX]\] (.+)$", issue_body or "", re.M)]


def load_lessons():
    if not LESSONS_PATH.exists():
        return []
    lessons = []
    for line in LESSONS_PATH.read_text().splitlines():
        # "→ moved to probe-review" lines are pointers, not lessons; patrol applies those probes directly (5c).
        if line.startswith("- ") and not line[2:].lstrip().startswith("→"):
            text = re.sub(r"\s*\(×\d+\)|\s*\[\[[^\]]+\]\]", "", line[2:]).strip()
            lessons.append(text)
    return lessons


THREADS_QUERY = """query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){
pullRequest(number:$number){reviewThreads(first:100){nodes{isResolved comments(first:1){nodes{
author{login} path line body url}}}}}}}"""


def other_reviewers(number, view, repo):
    """What other reviewers have open on the PR: a still-standing CHANGES_REQUESTED, approvals,
    and unresolved review threads (humans and bots like Qodo) that I didn't start."""
    latest_state = {}
    for r in sorted(view["reviews"], key=lambda r: r.get("submittedAt") or ""):
        login = (r.get("author") or {}).get("login")
        if login and login != ME and r.get("state") in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
            latest_state[login] = r["state"]
    owner, name = repo.split("/")
    data = gh_json("api", "graphql", "-f", f"query={THREADS_QUERY}", "-F", f"owner={owner}",
                   "-F", f"name={name}", "-F", f"number={number}")
    threads = data["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    unresolved = []
    for t in threads:
        first = (t["comments"]["nodes"] or [None])[0]
        if t["isResolved"] or not first or (first.get("author") or {}).get("login") == ME:
            continue
        unresolved.append({"author": (first.get("author") or {}).get("login"),
                           "where": f"{first['path']}:{first.get('line')}", "url": first["url"],
                           "text": first["body"][:500]})
    return {
        "changes_requested_by": sorted(k for k, v in latest_state.items() if v == "CHANGES_REQUESTED"),
        "approved_by": sorted(k for k, v in latest_state.items() if v == "APPROVED"),
        "unresolved_threads": unresolved,
    }


def my_last_reviewed_commit(view):
    mine = [r for r in view["reviews"] if (r.get("author") or {}).get("login") == ME and (r.get("commit") or {}).get("oid")]
    return max(mine, key=lambda r: r.get("submittedAt") or "")["commit"]["oid"] if mine else None


def load_adrs():
    adrs = []
    for path in sorted(Path("docs/adr").glob("*.md")):
        first = path.read_text().splitlines()[:1]
        title = first[0].lstrip("# ").strip() if first else path.stem
        adrs.append({"file": str(path), "title": title})
    return adrs


def code_facts(files):
    apps_with_context = sorted(
        {p.split("/")[1] for p in files if p.startswith("apps/") and Path("apps", p.split("/")[1], "CONTEXT.md").exists()}
    )
    return {
        "services": sorted({svc for p in files for prefix, svc in SERVICES.items() if p.startswith(prefix)}),
        "environment_ts_changed": any(p.endswith("environment.ts") for p in files),
        "touches_connect": any(p.startswith("apps/connect/") for p in files),
        "touches_db_schema": any(p.startswith("prisma/") or "/migrations/" in p for p in files),
        "context_md": [f"apps/{app}/CONTEXT.md" for app in apps_with_context],
    }


def call_jev(state, questions, long_context):
    headers = {"Authorization": f"Bearer {os.environ['TYPESAFE_API_KEY']}", "Content-Type": "application/json"}
    if long_context:
        headers["TypeSafe-Danger-Zone-Long-Context"] = "true"
    request = urllib.request.Request(
        "https://api.typesafe.ai/v1/systemone",
        data=json.dumps({"model": "jev-latest", "state": state, "questions": questions}).encode(),
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["answers"]


def noul(instructions):
    return {"type": "noul", "instructions": instructions}


def verdict(p):
    if p >= COVERED:
        return "covered"
    if p <= NOT_COVERED:
        return "not covered"
    return "verify"


def jev_prepass(pr, diff, files, reqs, earlier, lessons, adrs):
    state = {"pr": {"title": pr["title"], "body": (pr.get("body") or "")[:4000], "files": files, "diff": diff}}
    truncated = len(diff) > MAX_STATE_CHARS
    if truncated:
        state["pr"]["diff"] = diff[:MAX_STATE_CHARS]
    questions = {
        "risk": {"type": "score", "instructions": "How risky is merging the change in `pr.diff`?", "criteria": RISK_LEVELS},
        **{k: noul(v) for k, v in CONDITIONAL_QUESTIONS.items()},
        **{
            f"lesson_{i}": noul(f"Does the change in `pr.diff` match this review lesson's trigger, so a reviewer "
                                f"should apply it? Lesson: {text}")
            for i, text in enumerate(lessons)
        },
        **{
            f"adr_{i}": noul(f"Does the change in `pr.diff` touch the area governed by this architecture decision "
                             f"record: \"{adr['title']}\"?")
            for i, adr in enumerate(adrs)
        },
        **{
            f"req_{i}": noul(f"Does the change in `pr.diff` implement this requirement from the linked issue: {text}")
            for i, text in enumerate(reqs)
        },
        **{
            f"prev_{i}": noul(f"Does the change in `pr.diff` address this earlier review comment on {c['where']}: "
                              f"{c['text'][:1500]}")
            for i, c in enumerate(earlier)
        },
    }
    answers = call_jev(state, questions, long_context=len(json.dumps(state)) > LONG_CONTEXT_CHARS)

    def p(key):
        value = (answers.get(key) or {}).get("noul")
        return round(value, 2) if isinstance(value, (int, float)) else None

    risk = answers.get("risk") or {}
    risk_score = risk.get("score") if isinstance(risk.get("score"), (int, float)) else None
    return {
        "diff_truncated_for_jev": truncated,
        "risk": None if risk_score is None else {
            "score": round(risk_score, 2), "level": RISK_LEVELS[min(round(risk_score), len(RISK_LEVELS) - 1)],
        },
        "conditional": {k: p(k) for k in CONDITIONAL_QUESTIONS},
        "lessons_to_apply": [
            {"lesson": text, "p": p(f"lesson_{i}")} for i, text in enumerate(lessons) if (p(f"lesson_{i}") or 0) >= APPLIES
        ],
        "adrs_to_open": [
            {**adr, "p": p(f"adr_{i}")} for i, adr in enumerate(adrs) if (p(f"adr_{i}") or 0) >= APPLIES
        ],
        "requirements": [
            {"text": text, "p": p(f"req_{i}"), "verdict": verdict(p(f"req_{i}") or 0)} for i, text in enumerate(reqs)
        ],
        "earlier_comments": [
            {"where": c["where"], "url": c["url"], "p_addressed": p(f"prev_{i}"), "verdict": verdict(p(f"prev_{i}") or 0)}
            for i, c in enumerate(earlier)
        ],
    }


def prepare(pr, repo, lessons, adrs):
    number = pr["number"]
    view = gh_json("pr", "view", str(number), "--json", "reviews,comments,commits,body,closingIssuesReferences")
    action, reason = triage(pr, view)
    entry = {"number": number, "title": pr["title"], "url": pr["url"], "author": pr["author"]["login"],
             "action": action, "reason": reason}
    if action == "skip":
        return entry

    # `gh pr view --json files` stops at 100 files; the diff name list is complete.
    files = gh("pr", "diff", str(number), "--name-only").split()
    issues = [
        {"number": i["number"], **gh_json("issue", "view", str(i["number"]), "--json", "title,body")}
        for i in view["closingIssuesReferences"]
    ]
    reqs = [r for issue in issues for r in requirements(issue["body"])]
    earlier = my_earlier_comments(number, view, repo) if action == "re-review" else []
    changed_lines = pr["additions"] + pr["deletions"]
    entry.update({
        "size": {"additions": pr["additions"], "deletions": pr["deletions"], "files": len(files)},
        "large": changed_lines > LARGE_PR_LINES,
        "linked_issues": [{"number": i["number"], "title": i["title"]} for i in issues],
        "head_ref": f"refs/patrol/{number}",
        "last_reviewed_commit": my_last_reviewed_commit(view) if action == "re-review" else None,
        "other_reviewers": other_reviewers(number, view, repo),
        **code_facts(files),
        "jev": None,
    })
    if os.environ.get("TYPESAFE_API_KEY"):
        try:
            diff = gh("pr", "diff", str(number))
            pr_with_body = {**pr, "body": view.get("body")}
            entry["jev"] = jev_prepass(pr_with_body, diff, files, reqs, earlier, lessons, adrs)
        except Exception as error:  # a failed pre-pass means a full review, never a skipped one
            entry["jev_error"] = type(error).__name__
    return entry


def main():
    started = time.monotonic()
    repo = gh_json("repo", "view", "--json", "nameWithOwner")["nameWithOwner"]
    prs = gh_json("pr", "list", "--state", "open", "--limit", "1000",
                  "--json", "number,title,author,url,isDraft,additions,deletions")
    filtered, candidates = [], []
    for pr in prs:
        login = pr["author"]["login"]
        if pr["isDraft"]:
            filtered.append({"number": pr["number"], "title": pr["title"], "reason": "draft"})
        elif login in DEPENDABOT_LOGINS:
            filtered.append({"number": pr["number"], "title": pr["title"], "reason": "dependabot"})
        elif login == ME:
            filtered.append({"number": pr["number"], "title": pr["title"], "reason": "my own PR"})
        else:
            candidates.append(pr)

    lessons, adrs = load_lessons(), load_adrs()
    with ThreadPoolExecutor(max_workers=8) as pool:
        entries = list(pool.map(lambda pr: prepare(pr, repo, lessons, adrs), candidates))

    to_review = [e for e in entries if e["action"] != "skip"]
    if to_review:
        refspecs = [f"pull/{e['number']}/head:{e['head_ref']}" for e in to_review]
        subprocess.run(["git", "fetch", "--quiet", "--force", "origin", *refspecs], check=True)

    print(json.dumps({
        "repo": repo,
        "open_prs": len(prs),
        "filtered": filtered,
        "skipped": [{k: e[k] for k in ("number", "title", "reason")} for e in entries if e["action"] == "skip"],
        "to_review": to_review,
        "lessons_checked": len(lessons),
        "adrs_checked": len(adrs),
        "seconds": round(time.monotonic() - started, 1),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
