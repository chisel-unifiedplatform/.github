# Deploy guard

Free replacement for branch protection on private repos (which needs a paid
GitHub plan). Instead of stopping a bad push, it stops the **deploy**: the first
step of every deploy workflow checks how the commit arrived.

| Event | Deploys when |
|---|---|
| Push to `dev` | The commit is a merged PR into `dev`. Default **warn**: reported, still deployed. |
| Push to `main` (prod) | The commit is a merged PR into `main`, the PR does **not** come from `dev` (or another environment branch), and its checks didn't fail. Optionally it needs an approval. Default **enforce**. |
| Tag push (prod) | The tagged commit is already on `main`. |
| Manual run | Always, or only for the logins in `dispatch-actors`. |

A blocked deploy fails the job with a clear message, writes a job summary, and
(if `notify-webhook` is set) posts to Slack or Teams.

## Use it

Run it as its **own job** with a read-only token and no secrets, and make every
other root job wait for it. Pin the action to a full commit SHA, not a tag: a
tag can be moved, a commit can't.

```yaml
jobs:
  guard:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: read
      checks: read
      statuses: read
    steps:
      - name: Deploy guard
        uses: chisel-unifiedplatform/.github/actions/deploy-guard@<full-commit-sha> # v1
        with:
          target: prod                 # or dev
          mode: warn                   # report only; switch to enforce when the team is ready
          require-approval: "false"    # "true" once every PR to main gets a review

  build:                               # every job that had no `needs:` before
    needs: guard
    # ...unchanged
```

Why a separate job: the guard then can't see the deploy job's secrets or its
write token, and can't change files later steps use. The worst a broken or
tampered guard can do is fail.

Needs `python3` on the runner (present on GitHub-hosted Ubuntu runners).

## Try it locally

```bash
GH_TOKEN=$(gh auth token) REPO=chisel-unifiedplatform/micro-services \
SHA=$(git rev-parse origin/main) REF=refs/heads/main EVENT=push TARGET=prod \
python3 actions/deploy-guard/guard.py
```

## Releasing a new version of the guard

Callers pin a commit SHA, so a change here reaches a repo's deploys only when
that repo updates the SHA in a reviewed PR. The `v1` tag marks the current
recommended commit; only org admins can move it.

## Pre-push hook

`hooks/pre-push` stops `git push` to `main`, `dev`, `prod` and `master` on a
developer's machine, before the guard has to. Install it for every repo in a folder:

```bash
curl -fsSL https://raw.githubusercontent.com/chisel-unifiedplatform/.github/main/hooks/install.sh | sh -s -- ~/code
```

Bypass once with `ALLOW_PUSH=1 git push …`.
