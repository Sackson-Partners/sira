# Branch Protection Settings — SIRA Platform

Apply these settings in GitHub → Settings → Branches → Add branch protection rule.

## Rule: `main`

| Setting | Value |
|---|---|
| Branch name pattern | `main` |
| Require a pull request before merging | ✅ Enabled |
| — Required approvals | 1 |
| — Dismiss stale reviews on new commits | ✅ Enabled |
| Require status checks to pass before merging | ✅ Enabled |
| — Required checks | `Backend Tests`, `Frontend Tests`, `Security Scan` |
| Require branches to be up to date | ✅ Enabled |
| Require conversation resolution before merging | ✅ Enabled |
| Include administrators | ✅ Enabled |
| Allow force pushes | ❌ Disabled |
| Allow deletions | ❌ Disabled |

## Required Secrets (Settings → Secrets and variables → Actions)

| Secret Name | Description | How to Generate |
|---|---|---|
| `SECRET_KEY` | JWT signing key (production) | `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `CI_SECRET_KEY` | JWT signing key (CI tests only) | Same as above — use a different value |
| `DB_ADMIN_PASSWORD` | PostgreSQL admin password | Strong random password (min 16 chars, mixed) |
| `CI_DB_PASSWORD` | PostgreSQL password for CI test DB | Any value — ephemeral GHA service |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | `https://sira.vercel.app,https://sira.yourdomain.com` |
| `AZURE_CREDENTIALS` | Azure service principal JSON | See scripts/setup-azure-sp.sh |
| `DOCKERHUB_USERNAME` | Docker Hub username | `sacksons` |
| `DOCKERHUB_TOKEN` | Docker Hub access token | Docker Hub → Account Settings → Security → New Token |

## Environments (Settings → Environments)

Create two environments: `staging` and `prod`.

**prod environment** — add protection rules:
- Required reviewers: 1 (yourself or a team member)
- Deployment branches: selected branches only → `main`, tag patterns `v*.*.*`

## Notes

- The `test` job in `azure-deploy.yml` is a hard gate: Docker images only build if all tests pass.
- The `security-scan` job in `ci.yml` runs Bandit + Safety on every push.
- PRs to `main` require all CI checks to pass before the merge button is active.
