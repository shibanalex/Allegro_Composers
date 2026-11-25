# Security

## Authentication and Sessions

- Passwords hash with salted `scrypt` and verify in constant time.
- Login throttling caps failed attempts (`10` per `15m` per handle + IP) with
  uniform response timing for valid and unknown accounts.
- `SECRET_KEY` must be at least 32 non-default characters at startup.
- Session tokens live exclusively in `HttpOnly`, `SameSite=Lax` cookies
  (`allegro_token`, `Secure` on HTTPS) alongside a non-secret `allegro_session=1`
  presence cookie.
- Password changes and "sign out everywhere" bump `users.session_version`,
  invalidating previously issued tokens.
- State-changing cookie requests validate `Sec-Fetch-Site` (with `Origin`
  comparison against `SITE_URL` / `RENDER_EXTERNAL_URL` for older browsers).
- Optional email addresses are stored encrypted via derived keys; one-time
  password reset tokens are stored only as hashes.

## Uploads and Parsing

- All database access uses parameterized SQLAlchemy ORM queries; authorization is
  checked server-side via `require(Capability)` and object ownership.
- Upload types are verified by extension and magic bytes (`%PDF-`, XML checks,
  image header inspection before decoding). HTML, scripts, and SVG uploads are
  rejected.
- Compressed MusicXML (`.mxl`) enforces a `64 MB` decompression cap against zip
  bombs; XML parsing disables external entities (`expat >= 2.4` mitigates entity
  expansion).
- Images exceeding `30 MB` or `40 MP` are rejected from header dimensions before
  pixel decoding; thumbnail generation runs off the event loop in a worker pool.
- Every upload is tracked in `uploads` against `UPLOAD_DAILY_MB` per member;
  orphan local `/media` serves with `Content-Security-Policy: sandbox`.

## Client and Rate Limits

- Markdown renders without raw HTML and allows only `http(s)`, `mailto`, and
  relative internal paths. JSON-LD embeds escape closing `</script>` tags.
- Security headers set `X-Frame-Options: DENY`, `X-Content-Type-Options:
  nosniff`, `Strict-Transport-Security`, and strict `Permissions-Policy`.
- Write endpoints and search endpoints apply sliding-window rate limits per
  client IP (`CF-Connecting-IP` aware), returning `429` with `Retry-After`.
