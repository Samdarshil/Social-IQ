# Security and privacy

Implemented and tested:
- OAuth 2.0 authorization-code flow with a signed `state` (CSRF) check; read-only scopes only (YouTube: `youtube.readonly`).
- Platform tokens encrypted at rest with Fernet; never returned by the API or included in exports.
- Passwords hashed with bcrypt; JWT sessions with expiry.
- Disconnect deletes tokens and synced content; export and account deletion endpoints; demo sessions cannot touch real data.
- Security headers, restricted CORS, in-memory rate limiting, generic 500 responses (no stack traces).
- Gemini key is server-side only. Prompts and tool results sent to Gemini contain aggregated metrics and titles, not tokens, emails or identifiers (asserted in tests). The Privacy Center states this.

Not implemented / out of scope: key rotation tooling, distributed rate limiting, audit logging, third-party security review. Set `JWT_SECRET` and `TOKEN_ENCRYPTION_KEY` explicitly in production and serve over HTTPS.
