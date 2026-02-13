# Security Policy

Axelliant Software Engineering takes security seriously for `ax-agent-core`.

## Supported Versions

| Version | Supported |
| --- | --- |
| 0.1.x | Yes |
| <0.1.0 | No |

## Reporting a Vulnerability

Do not open public issues for security vulnerabilities.

1. Email `security@axelliant.com` with a clear report, impact, and reproduction steps.
2. Include affected versions, environment details, and proof-of-concept payloads if available.
3. If possible, include a patch suggestion or mitigation.

You may also copy `info@axelliant.com` for coordination. We acknowledge within 2 business days and provide a remediation timeline after triage.

## Disclosure Process

1. Triage and reproduce.
2. Assign severity and affected scope.
3. Prepare and validate fix.
4. Coordinate release and disclosure notes.

## Hardening Guidance

- Keep secrets out of source control.
- Prefer least-privilege API keys and scoped credentials.
- Validate all tool input schemas before execution.
- Use provider fallbacks to reduce failure blast radius.
