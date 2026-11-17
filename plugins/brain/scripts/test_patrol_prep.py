"""Self-check for patrol_prep: python3 -I test_patrol_prep.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import subprocess  # noqa: E402

import patrol_prep  # noqa: E402
from patrol_prep import check_status, final_risk, prepare_or_fail, risk_index, thread_outcome, triage  # noqa: E402


def run(name, status, conclusion, started, workflow="CI"):
    return {"__typename": "CheckRun", "name": name, "status": status, "conclusion": conclusion,
            "startedAt": started, "workflowName": workflow}


rollup = [
    run("build", "COMPLETED", "SUCCESS", "T1"),
    run("lint", "COMPLETED", "FAILURE", "T1"),
    run("gate", "COMPLETED", "SUCCESS", "T2"),  # re-run green after a failure, listed first: newest run wins, not
    run("gate", "COMPLETED", "FAILURE", "T1"),  # the last one in the list
    run("skip", "COMPLETED", "SKIPPED", "T1"),
    run("e2e", "COMPLETED", "SUCCESS", "T1"),  # old green run plus a queued re-run (zero start time): pending
    run("e2e", "QUEUED", None, "0001-01-01T00:00:00Z"),
    run("test", "COMPLETED", "FAILURE", "T1", workflow="A"),  # same name in another workflow does not hide it
    run("test", "COMPLETED", "SUCCESS", "T2", workflow="B"),
    run("review-gate", "QUEUED", None, "T1"),  # waits for a review: never holds approval
    {"__typename": "StatusContext", "context": "qodo", "state": "PENDING", "createdAt": "T1"},
    {"__typename": "StatusContext", "context": "ci/legacy", "state": "ERROR", "createdAt": "T1"},
]
assert check_status(rollup) == {"failing": ["ci/legacy", "lint", "test"], "pending": ["e2e", "qodo"]}, check_status(rollup)
assert check_status(None) == {"failing": [], "pending": []}

FACTS = {"touches_connect": False, "touches_db_schema": False, "environment_ts_changed": False}


def entry(score=None, facts=None, **conditional):
    # Shaped like jev_prepass's output: the index comes from the raw score, the stored score is rounded.
    risk = None if score is None else {"score": round(score, 2), "index": risk_index(score)}
    return {**FACTS, **(facts or {}), "jev": None if score is None else {"risk": risk, "conditional": conditional}}


# Jev alone: its level stands, nothing raised it.
assert final_risk(entry(1.2)) == {"level": "Low", "jev_level": "Low", "raised_by": [], "floor_rules": []}
# Re-rounding the 2-decimal score would give 2.50 -> 2 (Medium); the raw 2.503 is High.
assert final_risk(entry(2.503))["level"] == "High"
# A confident Jev answer on money lifts Low to High; a lower path rule matches but does not raise.
r = final_risk(entry(1.0, {"touches_connect": True}, money=0.9))
assert (r["level"], r["raised_by"]) == ("High", ["money"]), r
assert [m["rule"] for m in r["floor_rules"]] == ["money", "Connect API"], r
# A floor never pulls the level down.
assert final_risk(entry(3.0, {"touches_db_schema": True}))["level"] == "High"
# FLOOR_P is inclusive at 0.8; below it a Jev rule stays a lead, not a minimum.
assert final_risk(entry(0.0, money=0.8))["level"] == "High"
assert final_risk(entry(0.0, money=0.79))["level"] == "Trivial"
# Any migration file is at least Medium; only a destructive one is High.
assert final_risk(entry(0.0, {"touches_db_schema": True}))["level"] == "Medium"
assert final_risk(entry(0.0, {"touches_db_schema": True}, destructive_migration=0.95))["level"] == "High"
# Out-of-range scores clamp: -0.6 rounds to -1, which must be Trivial, not High.
assert final_risk(entry(-0.6))["level"] == "Trivial"
assert final_risk(entry(7))["level"] == "High"
# Without Jev: a path rule gives a minimum only and names it; no rule gives unknown.
r = final_risk(entry(None, {"environment_ts_changed": True}))
assert (r["level"], r["raised_by"]) == ("at least Medium", ["environment.ts"]), r
assert final_risk(entry(None))["level"] == "unknown"
# Jev present but its risk missing: same as without Jev.
assert final_risk({**FACTS, "jev": {"risk": None, "conditional": {}}})["level"] == "unknown"

ME_REVIEW = {"author": {"login": "xrompdev"}, "state": "COMMENTED", "submittedAt": "2026-11-18T10:05:00Z",
             "commit": {"oid": "a" * 40}}
view = {"reviews": [ME_REVIEW], "comments": [], "commits": [{"committedDate": "2026-11-18T10:00:00Z"}]}
# Head unchanged since my review: nothing new.
assert triage({}, {**view, "headRefOid": "a" * 40})[0] == "skip"
# A commit made before my review but pushed after it: the time check misses it, the commit check catches it.
assert triage({}, {**view, "headRefOid": "b" * 40}) == ("re-review", "head moved past the commit I last reviewed")

PR = {"number": 2931, "title": "big", "url": "u", "author": {"login": "dev"}}


def gh_fails(*_):
    raise subprocess.CalledProcessError(
        1, ["gh", "api", "--paginate", "repos/o/r/pulls/2931/files", "--jq", ".[].filename"], stderr="HTTP 404\n")


def odd_response(*_):
    raise KeyError("reviews")


# Any failure in one PR's prep marks only that PR failed, naming the gh call (flags dropped) or the error type.
patrol_prep.prepare = gh_fails
assert prepare_or_fail(PR, "o/r", [], [])["reason"] == "prep failed: gh api repos/o/r/pulls/2931/files: HTTP 404"
patrol_prep.prepare = odd_response
assert prepare_or_fail(PR, "o/r", [], [])["reason"] == "prep failed: KeyError: 'reviews'"

# One bad refspec fails a batched fetch: fall back to one PR at a time and mark only the PR that still fails.
calls = []


def fake_run(cmd, **_):
    refs = [a for a in cmd if a.startswith("pull/")]
    calls.append(refs)
    if any("pull/2/" in r for r in refs):
        raise subprocess.CalledProcessError(128, cmd, stderr="fatal: couldn't find remote ref pull/2/head\n")


patrol_prep.subprocess.run = fake_run
entries = [{"number": n, "head_ref": f"refs/patrol/{n}", "action": "review"} for n in (1, 2, 3)]
patrol_prep.fetch_heads(entries)
assert [e["action"] for e in entries] == ["review", "failed", "review"], entries
assert entries[1]["reason"] == "prep failed: git fetch: fatal: couldn't find remote ref pull/2/head", entries[1]
calls.clear()
patrol_prep.fetch_heads([])
assert calls == [], "no refspec must not run a plain git fetch"


def thread(outdated=False, resolved_by=None, replies=(), total=None):
    who = [("xrompdev", "first"), *replies]
    nodes = [{"author": None if w is None else {"login": w}, "body": b} for w, b in who]
    return {"isOutdated": outdated, "isResolved": resolved_by is not None,
            "resolvedBy": None if resolved_by is None else {"login": resolved_by},
            "comments": {"totalCount": total or len(nodes), "nodes": nodes}}


def outcome(t, author="dev", state="OPEN"):
    return thread_outcome(t, author, state)["outcome"]


# The line changed under the comment: acted on, even if the author also replied.
assert outcome(thread(outdated=True, replies=[("dev", "intended")])) == "fixed"
# Author replied, line unchanged: only the text tells "intended" from "done elsewhere", so it is handed over.
r = thread_outcome(thread(replies=[("dev", "intended"), ("xrompdev", "reword body?"), ("dev", "Reworded it")]), "dev", "MERGED")
assert r == {"outcome": "replied", "author_last_reply": "Reworded it"}, r
# A reply from someone else is not the author's; a deleted author (null) never matches a deleted replier.
assert outcome(thread(replies=[("qodo", "+1")])) == "open"
assert outcome(thread(replies=[(None, "ghost")]), author=None) == "open"
# Resolved: by me means I let it go, by anyone else means accepted.
assert outcome(thread(resolved_by="xrompdev")) == "dropped"
assert outcome(thread(resolved_by="dev")) == "fixed"
# Nothing at all: open while the PR is, unaddressed once it merged or closed.
assert outcome(thread()) == "open"
assert outcome(thread(), state="CLOSED") == "unaddressed"
# More replies than fetched: not judged on part of the thread.
assert outcome(thread(replies=[("dev", "x")], total=150)) == "open"
print("ok")
