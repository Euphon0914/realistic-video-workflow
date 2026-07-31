# Security and privacy

## Supported version

Security fixes are applied to the latest tagged release and the `main` branch.

## Report a vulnerability

Use GitHub's private vulnerability reporting feature when it is available. Do not include real user materials, credentials, portraits, private task identifiers, or confidential project details in a public issue.

## Data-handling rules

- Never commit real intake materials, generated media, post-production files, workflow state, API keys, session cookies, service tokens, private URLs, or `.env` files.
- Treat faces, voices, interviews, locations, products, scripts, and brand materials as potentially sensitive.
- Review the complete Git history before making the repository public; deleting a secret only from the latest commit is insufficient.
- Keep optional service credentials outside the repository and pass them through the service's supported authentication mechanism.
- The intake tool redacts absolute source paths by default, but generated project directories must still remain outside this repository.

Public GitHub repositories receive secret scanning. Enable push protection in repository security settings before accepting contributions.
