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

Add it as the **first step of the first job** in a deploy workflow:

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: read
      checks: read
      statuses: read
    steps:
      - uses: chisel-unifiedplatform/.github/actions/deploy-guard@v1
        with:
          target: prod                 # or dev
          require-approval: "true"     # optional
          notify-webhook: ${{ secrets.DEPLOY_ALERTS_WEBHOOK }}   # optional
      - uses: actions/checkout@v4
      # ...the rest of the job as before
```

If the job already sets `permissions:`, add the four read permissions above to it.
Needs `python3` on the runner (present on GitHub-hosted Ubuntu runners).

## Try it locally

```bash
GH_TOKEN=$(gh auth token) REPO=chisel-unifiedplatform/micro-services \
SHA=$(git rev-parse origin/main) REF=refs/heads/main EVENT=push TARGET=prod \
python3 actions/deploy-guard/guard.py
```

## Releasing a new version of the guard

Callers pin `@v1`, so a change here reaches prod deploys only when the tag moves:

```bash
git tag -f v1 && git push -f origin v1
```

## Pre-push hook

`hooks/pre-push` stops `git push` to `main`, `dev`, `prod` and `master` on a
developer's machine, before the guard has to. Install it for every repo in a folder:

```bash
curl -fsSL https://raw.githubusercontent.com/chisel-unifiedplatform/.github/main/hooks/install.sh | sh -s -- ~/code
```

Bypass once with `ALLOW_PUSH=1 git push …`.
