#!/usr/bin/env python3
"""Patrol prep: steps 1-4 of /patrol as code, plus a Jev pre-pass per PR.

Run from the repo root. Prints one JSON document to stdout: which PRs to review and why the
rest were skipped, and for each PR to review, the checks Jev judged relevant, its coverage
verdicts on the linked issue's requirements and on earlier review comments, and the facts code
can decide (services, environment.ts, Connect, CONTEXT.md apps, head CI checks). It also fetches
each PR head into refs/patrol/<number>. It never approves, comments, or writes outside refs/patrol/*.

`--gate <number> <reviewed-sha>` prints whether the PR may be approved now (open, head unchanged,
no failing or running checks); step 6e runs it before every approval.

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
    "tenant_or_auth": "Does `pr.diff` add or change a query, mutation, resolver or endpoint whose company scoping, "
    "guard, role or scope check decides who can read or write the data?",
    "public_contract": "Does `pr.diff` change a shape other code or customers depend on: a GraphQL schema type or "
    "field, a Connect response, param or status code, a webhook or domain event payload?",
    "destructive_migration": "Does `pr.diff` add or change a database migration that drops or renames a table or "
    "column, changes a column type, adds a NOT NULL column without a default, or edits or deletes an existing "
    "migration? An additive change (a new table, a nullable column, an index) is not destructive.",
}

# Rule-based minimums under Jev's risk score: the final level is the highest of Jev's level and every rule that
# matched, and a lower match never pulls it down. Each rule is (name, minimum RISK_LEVELS index, key), where key is
# a code fact on the entry (decided by paths, so certain) or a Jev conditional (counts only when Jev is confident).
# Path facts stay at Medium: `touches_db_schema` matches every migration, additive ones too, so only the
# destructive_migration question may raise a migration to High.
RISK_FLOORS = [
    ("money", 3, "money"),
    ("tenant scoping or auth", 3, "tenant_or_auth"),
    ("destructive migration", 3, "destructive_migration"),
    ("event or workflow history", 3, "event_or_workflow"),
    ("public contract", 2, "public_contract"),
    ("Connect API", 2, "touches_connect"),
    ("schema or migration file", 2, "touches_db_schema"),
    ("environment.ts", 2, "environment_ts_changed"),
]
# A floor is a hard minimum, so it takes a confident yes, not the recall threshold (APPLIES) the 5d checks use.
FLOOR_P = COVERED

# A check that ended in one of these fails the head; anything not yet completed is pending.
FAILED_CONCLUSIONS = {"FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE"}
FAILED_STATES = {"FAILURE", "ERROR"}
# Checks that wait for a review (responsibid-server's review-gate reruns on pull_request_review), so
# holding approval until they pass would deadlock. ponytail: name list, add a repo's gate here when it gets one.
REVIEW_DEPENDENT_CHECKS = {"review-gate"}


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
    # committedDate is when a commit was made, not pushed: a push during the wizard can predate the review
    # 6e posts at Submit. My review's commit, not its time, says whether I saw the head.
    reviewed = my_last_reviewed_commit(view)
    if reviewed and view.get("headRefOid") and reviewed != view["headRefOid"]:
        return "re-review", "head moved past the commit I last reviewed"
    return "skip", "nothing new since my last comment"


def check_status(rollup):
    """Head commit's CI from `statusCheckRollup`: names of failing and still-running checks.
    The rollup keeps every run of a re-run check. A check (workflow + name, so two workflows' `test` jobs stay
    apart) is pending while any run of it has not completed: a queued re-run reports a zero start time, so it
    would lose a latest-by-time pick to the old run. Otherwise its latest completed run decides."""
    runs = {}
    for c in rollup or []:
        status_context = c.get("__typename") == "StatusContext"
        name = c.get("context") if status_context else c.get("name")
        if name in REVIEW_DEPENDENT_CHECKS:
            continue
        runs.setdefault((None if status_context else c.get("workflowName"), name), []).append(c)
    failing, pending = [], []
    for (_, name), checks in runs.items():
        if any(c.get("__typename") != "StatusContext" and c.get("status") != "COMPLETED" for c in checks):
            pending.append(name)
            continue
        c = max(checks, key=lambda c: c.get("startedAt") or c.get("createdAt") or "")
        if c.get("__typename") == "StatusContext":
            state = c.get("state")
            if state in FAILED_STATES:
                failing.append(name)
            elif state != "SUCCESS":
                pending.append(name)
        elif c.get("conclusion") in FAILED_CONCLUSIONS:
            failing.append(name)
    return {"failing": sorted(set(failing)), "pending": sorted(set(pending))}


def gate(number, reviewed_sha):
    """Submit-time gate (6e): may I approve this PR now? Reads the PR fresh, not the prep snapshot."""
    try:
        view = gh_json("pr", "view", str(number), "--json", "state,headRefOid,statusCheckRollup")
    except (subprocess.CalledProcessError, json.JSONDecodeError) as error:
        # Unknown state: 6e posts nothing and approves nothing for this PR.
        detail = (getattr(error, "stderr", "") or str(error)).strip().splitlines()[-1:] or [type(error).__name__]
        return {"number": number, "state": "UNKNOWN", "approve": False, "hold": [f"gate failed: {detail[0]}"]}
    hold = []
    if view["state"] != "OPEN":
        hold.append(f"PR is {view['state'].lower()}")
    if view["headRefOid"] != reviewed_sha:
        hold.append(f"head moved to {view['headRefOid'][:8]} since the reviewed {reviewed_sha[:8]}")
    checks = check_status(view["statusCheckRollup"])
    if checks["failing"]:
        hold.append("failing checks: " + ", ".join(checks["failing"]))
    if checks["pending"]:
        hold.append("checks still running: " + ", ".join(checks["pending"]))
    return {"number": number, "state": view["state"], "approve": not hold, "hold": hold}


OUTCOMES_QUERY = """query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){
pullRequest(number:$number){state author{login} reviewThreads(first:100){totalCount nodes{isResolved isOutdated
resolvedBy{login} comments(first:100){totalCount nodes{author{login} url body}}}}}}}"""


def thread_outcome(thread, pr_author, pr_state):
    """What became of one of my inline comments, from GitHub's thread state.
    - outdated: the line changed under it, so it was acted on (`fixed`; a rebase that rewrites the hunk reads the
      same, a known false positive);
    - the author replied and the line did not change: `replied`, with the author's last words, because only the
      text tells "intended" from "done elsewhere" (7f reads it and writes `fixed` or `disputed`);
    - resolved: by me means I let it go (`dropped`), by anyone else means accepted (`fixed`);
    - nothing: `open` while the PR is, `unaddressed` once it merged or closed.
    A thread with more replies than fetched stays `open` rather than be judged on part of it."""
    comments = thread["comments"]
    if comments["totalCount"] > len(comments["nodes"]):
        return {"outcome": "open"}
    if thread["isOutdated"]:
        return {"outcome": "fixed"}
    replies = [c for c in comments["nodes"][1:] if pr_author and (c.get("author") or {}).get("login") == pr_author]
    if replies:
        return {"outcome": "replied", "author_last_reply": (replies[-1].get("body") or "")[:600]}
    if thread["isResolved"]:
        return {"outcome": "dropped" if (thread.get("resolvedBy") or {}).get("login") == ME else "fixed"}
    return {"outcome": "unaddressed" if pr_state in ("MERGED", "CLOSED") else "open"}


def outcomes(repo, number):
    """`--outcomes` (7f): each of my inline review comments on the PR, by URL, with its outcome. Never raises: a gh
    failure or a missing PR returns `error`, and 7f leaves that PR's concerns as they are."""
    owner, name = repo.split("/")
    try:
        pr = gh_json("api", "graphql", "-f", f"query={OUTCOMES_QUERY}", "-F", f"owner={owner}", "-F", f"name={name}",
                     "-F", f"number={number}")["data"]["repository"]["pullRequest"]
        if pr is None:
            raise LookupError(f"no PR #{number} in {repo}")
    except (subprocess.CalledProcessError, json.JSONDecodeError, LookupError, KeyError, TypeError) as error:
        return {"number": number, "error": failure_reason(error).replace("prep failed: ", ""), "comments": []}
    threads = pr["reviewThreads"]
    author, state = (pr.get("author") or {}).get("login"), pr["state"]
    mine = [t for t in threads["nodes"]
            if t["comments"]["nodes"] and (t["comments"]["nodes"][0].get("author") or {}).get("login") == ME]
    return {
        "number": number, "state": state,
        # Past 100 threads the list is cut: say so rather than report the rest as missing.
        "threads_truncated": threads["totalCount"] > len(threads["nodes"]),
        "comments": [{"url": t["comments"]["nodes"][0]["url"], **thread_outcome(t, author, state)} for t in mine],
    }


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


def level_name(index):
    return RISK_LEVELS[index].split(":")[0]


def risk_index(score):
    """Jev's raw score to a RISK_LEVELS index, clamped: round(-0.6) is -1, which would index High."""
    return max(0, min(round(score), len(RISK_LEVELS) - 1))


def final_risk(entry):
    """The entry's risk: the higher of Jev's level and the RISK_FLOORS minimums, with the rules that matched."""
    jev = entry.get("jev") or {}
    conditional = jev.get("conditional") or {}
    matched = [
        {"rule": name, "min": level_name(level), "_level": level}
        for name, level, key in RISK_FLOORS
        if (entry.get(key) is True if key in entry else (conditional.get(key) or 0) >= FLOOR_P)
    ]
    floor = max((m["_level"] for m in matched), default=None)
    # The index jev_prepass took from the raw score; re-rounding the stored 2-decimal score can drop a level.
    index = (jev.get("risk") or {}).get("index")
    jev_level = index if isinstance(index, int) and 0 <= index < len(RISK_LEVELS) else None
    levels = [level for level in (jev_level, floor) if level is not None]
    return {
        # Without Jev, only a floor is known, and it is a minimum: say "at least".
        "level": (level_name(max(levels)) if jev_level is not None else f"at least {level_name(floor)}")
        if levels else "unknown",
        "jev_level": None if jev_level is None else level_name(jev_level),
        # The rules that decided the final level: at the floor, and above Jev's level (or no Jev at all).
        "raised_by": [m["rule"] for m in matched if m["_level"] == floor and (jev_level is None or floor > jev_level)],
        "floor_rules": [{k: v for k, v in m.items() if k != "_level"} for m in matched],
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
            "score": round(risk_score, 2),
            "index": risk_index(risk_score),
            "level": RISK_LEVELS[risk_index(risk_score)],
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
    view = gh_json("pr", "view", str(number), "--json", "reviews,comments,commits,body,closingIssuesReferences,statusCheckRollup,headRefOid")
    action, reason = triage(pr, view)
    entry = {"number": number, "title": pr["title"], "url": pr["url"], "author": pr["author"]["login"],
             "action": action, "reason": reason}
    if action == "skip":
        return entry

    # `gh pr view --json files` stops at 100 files, and `gh pr diff` refuses a diff over 20,000 lines (HTTP 406);
    # the paginated files endpoint has neither limit (it caps at 3,000 files).
    files = gh("api", "--paginate", f"repos/{repo}/pulls/{number}/files", "--jq", ".[].filename").splitlines()
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
        # The files endpoint stops at 3,000; past that, services and code facts miss paths.
        "files_truncated": len(files) < (pr.get("changedFiles") or 0),
        "linked_issues": [{"number": i["number"], "title": i["title"]} for i in issues],
        "head_ref": f"refs/patrol/{number}",
        "last_reviewed_commit": my_last_reviewed_commit(view) if action == "re-review" else None,
        "other_reviewers": other_reviewers(number, view, repo),
        "checks": check_status(view.get("statusCheckRollup")),
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
    entry["risk"] = final_risk(entry)
    return entry


def failure_reason(error):
    """What failed, readable: the gh call without its flags and the last stderr line, or the error type."""
    if isinstance(error, subprocess.CalledProcessError):
        call = " ".join(a for a in error.cmd[:4] if not a.startswith("-"))
        detail = (error.stderr or "").strip().splitlines()[-1:] or [f"exit {error.returncode}"]
        return f"prep failed: {call}: {detail[0]}"
    return f"prep failed: {type(error).__name__}: {error}"


def prepare_or_fail(pr, repo, lessons, adrs):
    """One PR's failure marks that PR failed instead of losing the repo's whole run. Broad on purpose: a gh error,
    an odd gh response (a null field, bad JSON) or a bug here all end the same way, a PR listed as failed with the
    error named, so nothing is skipped silently and a script bug shows up as every PR failing with the same error."""
    try:
        return prepare(pr, repo, lessons, adrs)
    except Exception as error:  # noqa: BLE001 (see docstring)
        return {"number": pr["number"], "title": pr["title"], "url": pr["url"], "author": pr["author"]["login"],
                "action": "failed", "reason": failure_reason(error)}


def fetch_heads(entries):
    """Fetch each PR head into refs/patrol/<number>. One bad refspec (a PR deleted since the list) fails the whole
    fetch, so on failure fetch one by one and mark only the PRs that still fail."""
    def fetch(batch):
        subprocess.run(["git", "fetch", "--quiet", "--force", "origin",
                        *[f"pull/{e['number']}/head:{e['head_ref']}" for e in batch]],
                       capture_output=True, text=True, check=True)
    if not entries:  # no refspec would make it a plain `git fetch origin`
        return
    try:
        fetch(entries)
        return
    except subprocess.CalledProcessError:
        pass
    for e in entries:
        try:
            fetch([e])
        except subprocess.CalledProcessError as error:
            e.update(action="failed", reason=failure_reason(error))


def main():
    if sys.argv[1:2] == ["--gate"]:
        if len(sys.argv) != 4 or not re.fullmatch(r"[0-9]+", sys.argv[2]) or not re.fullmatch(r"[0-9a-f]{40}", sys.argv[3]):
            sys.exit("usage: patrol_prep.py --gate <pr-number> <reviewed-commit-sha>")
        print(json.dumps(gate(int(sys.argv[2]), sys.argv[3])))
        return 0
    if sys.argv[1:2] == ["--outcomes"]:
        if len(sys.argv) != 3 or not re.fullmatch(r"[0-9]+", sys.argv[2]):
            sys.exit("usage: patrol_prep.py --outcomes <pr-number>")
        repo = gh_json("repo", "view", "--json", "nameWithOwner")["nameWithOwner"]
        print(json.dumps(outcomes(repo, int(sys.argv[2]))))
        return 0
    started = time.monotonic()
    repo = gh_json("repo", "view", "--json", "nameWithOwner")["nameWithOwner"]
    prs = gh_json("pr", "list", "--state", "open", "--limit", "1000",
                  "--json", "number,title,author,url,isDraft,additions,deletions,changedFiles")
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
        entries = list(pool.map(lambda pr: prepare_or_fail(pr, repo, lessons, adrs), candidates))

    fetch_heads([e for e in entries if e["action"] in ("review", "re-review")])
    to_review = [e for e in entries if e["action"] in ("review", "re-review")]

    print(json.dumps({
        "repo": repo,
        "open_prs": len(prs),
        "filtered": filtered,
        "skipped": [{k: e[k] for k in ("number", "title", "reason")} for e in entries if e["action"] == "skip"],
        "failed": [{k: e[k] for k in ("number", "title", "url", "reason")} for e in entries if e["action"] == "failed"],
        "to_review": to_review,
        "lessons_checked": len(lessons),
        "adrs_checked": len(adrs),
        "seconds": round(time.monotonic() - started, 1),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
