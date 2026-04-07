# Security Hardening Checklist

Generated: 2026-04-07

| ID | Task | Severity | Owner | Target Date | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-001 | Rotate leaked external API keys and purge exposed secrets from git history | Critical | Backend Owner | 2026-04-07 | In Progress |
| SEC-002 | Enforce Clerk JWT audience validation in production | High | Backend Owner | 2026-04-07 | Done |
| SEC-003 | Protect proxy routes with auth and reject missing Bearer tokens | High | Frontend Owner | 2026-04-07 | Done |
| SEC-004 | Sanitize worker error messages returned to API consumers | High | Backend Owner | 2026-04-08 | Done |
| SEC-005 | Restrict automation URLs to approved ATS domains and block private network targets | High | Backend Owner | 2026-04-08 | Done |
| SEC-006 | Add per-user rate limiting for upload, scrape, submit, and run-now endpoints | Medium | Backend Owner | 2026-04-09 | Done |
| SEC-007 | Minimize retained resume PII by disabling raw_text storage by default | Medium | Backend Owner | 2026-04-10 | Done |
| SEC-008 | Encrypt sensitive persisted fields (resume JSON, logs) at rest | Medium | Platform Owner | 2026-04-14 | Planned |
| SEC-009 | Add CI security gates for Bandit, pip-audit, npm audit, and secret scanning | Medium | DevOps Owner | 2026-04-14 | Done |
| SEC-010 | Add pre-commit secret scanner and block accidental secret commits locally | Medium | DevOps Owner | 2026-04-14 | Planned |
| SEC-011 | Define incident-response runbook for key leaks and forced token revocation | Medium | Security Owner | 2026-04-18 | Planned |
| SEC-012 | Run quarterly dependency and auth hardening review | Low | Engineering Manager | 2026-07-01 | Planned |

## Notes

- Local development now supports SQLite plus in-memory Celery defaults, so Docker DB is optional.
- Production should use managed Postgres/Redis, explicit secret management, and `CELERY_TASK_ALWAYS_EAGER=false`.
