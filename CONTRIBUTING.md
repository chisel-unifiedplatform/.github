# Contributing to Orphix

Thanks for taking the time to contribute! These guidelines apply to every repository in
the [Orphix organization](https://github.com/chisel-unifiedplatform) unless a repo
overrides them with its own `CONTRIBUTING.md`.

## Before you start

- **Internal contributors:** check the relevant project board / tracker before starting
  substantial work so we don't duplicate effort.
- **External contributors:** for anything larger than a small fix, please open an issue
  first to discuss the change so it isn't a surprise at review time.

## Development workflow

1. **Branch** off the default branch. Use a descriptive name:
   `feat/<short-desc>`, `fix/<short-desc>`, or `chore/<short-desc>`.
2. **Make focused commits.** Keep each PR scoped to one logical change.
3. **Follow the code style** of the repo you're working in (linters/formatters are
   configured per-repo — run them before pushing).
4. **Add or update tests** for behavior you change.
5. **Update docs** when you change public behavior or configuration.

## Commit messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(voice): add barge-in support to the call server
fix(mcp): handle empty tool responses
docs(readme): clarify tenant setup
```

Common types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `ci`.

## Opening a pull request

- Fill out the pull request template.
- Link the issue it closes (`Closes #123`).
- Make sure CI is green and there are no lint/type errors.
- Keep the PR small enough to review in one sitting where possible.

A maintainer will review, request changes if needed, and merge once it's approved and
green.

## Reporting bugs & requesting features

Use the issue templates (Bug report / Feature request). For **security issues**, do
**not** open a public issue — follow the [Security Policy](SECURITY.md).

## Code of conduct

By participating you agree to uphold our [Code of Conduct](CODE_OF_CONDUCT.md).
