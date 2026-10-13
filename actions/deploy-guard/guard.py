#!/usr/bin/env python3
"""Deploy guard: refuse to deploy a commit that didn't arrive the agreed way.

Branch protection needs a paid GitHub plan for private repos, so these rules
are checked at deploy time instead. A push deploys only if its commit is the
result of a merged pull request into the branch that was pushed. For prod,
the PR must also not come from an environment branch (no `dev -> main`
merges), can be required to have an approval, and its checks must not have
failed. A tag push deploys only if the tagged commit is already on the prod
branch. Manual runs (workflow_dispatch) are allowed, optionally only for a
list of people.

Configuration comes from environment variables (the composite action maps its
inputs onto these). Exit code 1 blocks the deploy when MODE=enforce; with
MODE=warn problems are reported but the deploy continues.

Run it locally to see what it would decide:
    GH_TOKEN=$(gh auth token) REPO=org/repo SHA=<commit> REF=refs/heads/main \\
    EVENT=push TARGET=prod python3 guard.py
"""
import fnmatch
import json
import os
import sys
import urllib.error
import urllib.request

API = os.environ.get("GITHUB_API_URL", "https://api.github.com")


def env(name, default=""):
    # The composite action passes every input, so an unset input arrives as "" and must fall back too.
    return os.environ.get(name, "").strip() or default


def flag(name, default):
    return env(name, default).lower() in ("1", "true", "yes", "on")


def listing(name, default=""):
    return [x.strip() for x in env(name, default).split(",") if x.strip()]


def api(path):
    req = urllib.request.Request(f"{API}{path}", headers={
        "Authorization": f"Bearer {env('GH_TOKEN')}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GitHub API {path} returned {e.code}: {e.read().decode()[:200]}") from None


def notify(text):
    url = env("NOTIFY_WEBHOOK")
    if not url:
        return
    try:  # Slack and Teams incoming webhooks both accept {"text": ...}
        req = urllib.request.Request(url, data=json.dumps({"text": text}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as e:
        print(f"::warning::Couldn't post to the notify webhook: {e}")


def summary(lines):
    path = env("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as f:
            f.write("\n".join(lines) + "\n")


def find_pr(repo, sha, branch):
    """The merged PR whose merge produced `sha` on `branch`, if any."""
    prs = api(f"/repos/{repo}/commits/{sha}/pulls")
    merged = [p for p in prs if p.get("merged_at") and p["base"]["ref"] == branch]
    exact = [p for p in merged if p.get("merge_commit_sha") == sha]
    return (exact or merged or [None])[0]


def approval_problem(repo, pr):
    latest = {}
    for rv in api(f"/repos/{repo}/pulls/{pr['number']}/reviews?per_page=100"):
        if rv["state"] in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
            latest[rv["user"]["login"]] = rv["state"]
    if "CHANGES_REQUESTED" in latest.values():
        return f"PR #{pr['number']} still has changes requested."
    if "APPROVED" not in latest.values():
        return f"PR #{pr['number']} was merged without an approval."
    return None


def checks_problem(repo, pr):
    head = pr["head"]["sha"]
    bad = []
    runs = api(f"/repos/{repo}/commits/{head}/check-runs?per_page=100").get("check_runs", [])
    bad += [c["name"] for c in runs if c.get("conclusion") in ("failure", "timed_out", "cancelled", "action_required")]
    status = api(f"/repos/{repo}/commits/{head}/status")
    bad += [s["context"] for s in status.get("statuses", []) if s["state"] in ("failure", "error")]
    return f"PR #{pr['number']} was merged with failing checks: {', '.join(sorted(set(bad)))}." if bad else None


def main():
    repo, sha, ref, event = env("REPO"), env("SHA"), env("REF"), env("EVENT")
    target = env("TARGET", "prod").lower()
    mode = env("MODE", "enforce" if target == "prod" else "warn").lower()
    prod_branch = env("PROD_BRANCH", "main")
    blocked_heads = listing("BLOCKED_HEAD_BRANCHES", "dev,develop,development,staging")
    allowed_heads = listing("ALLOWED_HEAD_BRANCHES", "*")
    need_approval = flag("REQUIRE_APPROVAL", "false")
    need_checks = flag("REQUIRE_CHECKS", "true")
    dispatchers = listing("DISPATCH_ACTORS")
    mergers = listing("PROD_MERGERS")
    actor = env("ACTOR")

    problems, notes = [], []
    if event == "workflow_dispatch":
        if dispatchers and actor not in dispatchers:
            problems.append(f"{actor} started this deploy by hand, but only {', '.join(dispatchers)} may.")
        else:
            notes.append(f"Manual run by {actor}.")
    elif event == "push" and ref.startswith("refs/tags/"):
        cmp = api(f"/repos/{repo}/compare/{prod_branch}...{sha}")
        if cmp["status"] not in ("identical", "behind"):
            problems.append(f"Tag {ref[10:]} points at {sha[:7]}, which isn't on {prod_branch}.")
        else:
            notes.append(f"Tag {ref[10:]} is on {prod_branch}.")
    elif event == "push" and ref.startswith("refs/heads/"):
        branch = ref[11:]
        pr = find_pr(repo, sha, branch)
        if not pr:
            problems.append(f"{sha[:7]} was pushed straight to {branch} by {actor}, not merged from a pull request.")
        else:
            head = pr["head"]["ref"]
            notes.append(f"Merged from PR #{pr['number']} ({head} → {branch}): {pr['title']}")
            if target == "prod":
                if any(fnmatch.fnmatch(head, p) for p in blocked_heads):
                    problems.append(f"PR #{pr['number']} merges {head} into {branch}. Ship single changes from "
                                    f"release/*, hotfix/* or feature branches instead of the whole of {head}.")
                elif not any(fnmatch.fnmatch(head, p) for p in allowed_heads):
                    problems.append(f"PR #{pr['number']} comes from {head}; prod only accepts {', '.join(allowed_heads)}.")
                if mergers:
                    by = (api(f"/repos/{repo}/pulls/{pr['number']}").get("merged_by") or {}).get("login", "")
                    if by.lower() not in {m.lower() for m in mergers}:
                        problems.append(f"PR #{pr['number']} was merged into {branch} by {by or 'someone unknown'}; "
                                        f"only {', '.join(mergers)} may ship to prod.")
                if pr["head"]["repo"] and pr["head"]["repo"]["full_name"] != repo:
                    problems.append(f"PR #{pr['number']} comes from a fork ({pr['head']['repo']['full_name']}).")
            if need_approval:
                p = approval_problem(repo, pr)
                problems += [p] if p else []
            if need_checks:
                p = checks_problem(repo, pr)
                problems += [p] if p else []
    else:
        notes.append(f"Event '{event}' isn't checked.")

    where = f"{repo}@{sha[:7]} → {target}"
    if problems:
        blocked = mode == "enforce"
        level = "error" if blocked else "warning"
        for p in problems:
            print(f"::{level}::{p}")
        verdict = "Deploy blocked" if blocked else "Deploying anyway (warn mode)"
        summary([f"### 🛑 {verdict}" if blocked else f"### ⚠️ {verdict}", f"`{where}`", "", *[f"- {p}" for p in problems + notes]])
        run_url = f"{env('GITHUB_SERVER_URL', 'https://github.com')}/{repo}/actions/runs/{env('RUN_ID')}" if env("RUN_ID") else ""
        notify(f"{'🛑' if blocked else '⚠️'} {verdict}: {where}\n" + "\n".join(f"• {p}" for p in problems) + (f"\n{run_url}" if run_url else ""))
        print(f"{verdict}: {where}")
        return 1 if blocked else 0
    for n in notes:
        print(n)
    summary(["### ✅ Deploy guard passed", f"`{where}`", "", *[f"- {n}" for n in notes]])
    print(f"Deploy guard passed: {where}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        # A broken guard must not silently let everything through, nor block an urgent fix forever:
        # fail closed for prod, open for dev, and say why.
        fail = env("TARGET", "prod").lower() == "prod" and env("MODE", "enforce").lower() == "enforce"
        print(f"::{'error' if fail else 'warning'}::Deploy guard couldn't run: {e}")
        sys.exit(1 if fail else 0)
