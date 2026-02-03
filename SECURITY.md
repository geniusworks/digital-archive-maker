# Security Policy

## Scope

This project consists of local automation scripts for personal media management. It does not run as a service, handle authentication, or process untrusted input from the network.

## Reporting a Vulnerability

If you discover a security issue:

1. **Do not** open a public GitHub issue
2. **Email** the maintainer directly (see GitHub profile)
3. **Include** a description of the issue and steps to reproduce

You can expect a response within 7 days.

## What Qualifies

- Command injection vulnerabilities in scripts
- Secrets accidentally committed to the repository
- Dependencies with known critical vulnerabilities

## What Doesn't Qualify

- Issues with third-party tools (MakeMKV, HandBrake, etc.)
- API key exposure in user-created `.env` files (that's user responsibility)
