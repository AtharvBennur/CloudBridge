---
kind: external_dependency
name: Google OAuth
slug: google-oauth
category: external_dependency
category_hints:
    - auth_protocol
scope:
    - '**'
---

### Google OAuth
- **Role in this repo**: Secondary authentication provider alongside email/password login; used for single-sign-on via Google identity tokens.
- **Auth protocol**: Expects a Google-signed `id_token` (JWT) from the client-side Google Sign-In flow; backend does NOT verify the token signature server-side in current implementation — it trusts the id_token contents and extracts email/name fields directly. `GOOGLE_OAUTH_CLIENT_ID` env var is present but not actively used for verification.
- **Durable usage model**: The endpoint treats the Google id_token as opaque and derives user identity from its claims; production hardening should add server-side token verification against Google's JWKS endpoint using `GOOGLE_OAUTH_CLIENT_ID`.