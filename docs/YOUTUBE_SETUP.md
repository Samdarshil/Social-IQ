# Connecting a real YouTube channel

YouTube is SocialIQ's strongest integration. It uses Google OAuth 2.0 with a single **read-only** scope:
`https://www.googleapis.com/auth/youtube.readonly`. SocialIQ cannot upload, edit, delete or comment.

> **Status of this integration:** the OAuth request construction, state (CSRF) check, token exchange, video
> normalization, encrypted token storage, disconnect and deletion are covered by automated tests against a
> *mocked* Google (`backend/tests/test_integrations.py`). The first run against your real credentials is the
> live verification. Follow the checklist at the bottom.

## 1. Create Google OAuth credentials (about 10 minutes)

1. Open <https://console.cloud.google.com/> and create (or pick) a project.
2. **APIs & Services → Library →** enable **YouTube Data API v3**.
3. **APIs & Services → OAuth consent screen**
   - User type: **External**. App name: `SocialIQ`. Add your email as support and developer contact.
   - **Scopes →** add `.../auth/youtube.readonly` only.
   - **Test users →** add the Google account that owns the channel. While the app is in *Testing*,
     only listed test users can sign in (this is fine for a hackathon; refresh tokens expire after 7 days in this mode).
4. **APIs & Services → Credentials → Create credentials → OAuth client ID**
   - Application type: **Web application**.
   - **Authorized redirect URIs** (exact match, no trailing slash):
     - Local: `http://localhost:8000/api/connect/youtube/callback`
     - Production: `https://YOUR-DOMAIN/api/connect/youtube/callback`
5. Copy the **Client ID** and **Client secret**.

## 2. Configure SocialIQ

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` (this file is git-ignored; never commit it):

```ini
GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxxxxxxx
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173
```

Check it:

```bash
python scripts/doctor.py
```

You should see a green tick next to YouTube and the redirect URI you must have registered.

## 3. Connect

1. Start backend and frontend (see the main README).
2. Choose **Connect my accounts**, create a SocialIQ account (this is *not* your Google password).
3. Privacy Center → YouTube → **Connect** → approve the consent screen.
4. You are redirected back with a count of synced videos. Open Overview: the header badge changes from
   `DEMO DATA` to `LIVE DATA`.

## What YouTube data is and is not available

| Available with `youtube.readonly` | Not available (so SocialIQ does not show it) |
|---|---|
| Subscriber count, video list, views, likes, comment counts, publish time, duration | Watch time, retention, impressions, traffic sources (need the separate YouTube Analytics API and scope) |
| | Per-video shares and subscribers gained |
| | Historical subscriber time series (only today's count is returned) |

Consequences you will see in the UI, by design: follower-growth cards say "history unavailable" for live
accounts, shares are `0`, and the ML model asks for at least **60 posts** before it trains. With fewer, the
simulator reports that plainly instead of producing a number.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `redirect_uri_mismatch` | The URI in Google Console must match `BACKEND_URL + /api/connect/youtube/callback` exactly. |
| `access_denied` / "app not verified" | Add your account under *Test users*, or publish and verify the app. |
| "No YouTube channel found" | The Google account has no channel; sign in with the account that owns one. |
| Redirected with an `error=` message | Shown at the top of the Privacy Center; the failed connection is not kept. |
| Sync works but refresh later fails | Testing-mode refresh tokens last 7 days; click Connect again. |

## Live verification checklist

- [ ] `python scripts/doctor.py` shows YouTube configured
- [ ] Connect succeeds and the badge reads `LIVE DATA`
- [ ] Content page lists your real videos with correct view counts
- [ ] `sqlite3 backend/data/socialiq.db "select access_token_enc from platform_connections"` shows ciphertext (`gAAAA...`), not a token
- [ ] Privacy Center → Disconnect removes the connection and your videos
- [ ] Revoke access at <https://myaccount.google.com/permissions> (disconnecting in SocialIQ deletes our tokens; revoking there ends Google's side)
