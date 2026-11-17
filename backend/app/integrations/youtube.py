"""YouTube adapter: Google OAuth 2.0 + YouTube Data API v3, read-only scope."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

from app.config import get_settings
from app.integrations.base import ProviderAdapter, ProviderUnavailable, TokenSet
from app.schemas.content import AccountSnapshot, Content
from app.utils.categorize import infer_category

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/youtube/v3"
SCOPE = "https://www.googleapis.com/auth/youtube.readonly"


def _iso_duration(s: str) -> int:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    if not m:
        return 0
    d, h, mi, se = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + se


class YouTubeAdapter(ProviderAdapter):
    platform = "youtube"
    label = "YouTube"
    read_only_scopes = [SCOPE]
    api_notes = ("Reads your channel's public statistics and your videos' view/like/comment counts. "
                 "Watch-time and retention need the separate YouTube Analytics scope, which SocialIQ does not request.")

    def is_configured(self) -> bool:
        s = get_settings()
        return bool(s.google_client_id and s.google_client_secret)

    def authorization_url(self, state, redirect_uri, code_challenge=None) -> str:
        if not self.is_configured():
            raise ProviderUnavailable("YouTube OAuth credentials are not configured on this server.")
        q = dict(client_id=get_settings().google_client_id, redirect_uri=redirect_uri, response_type="code",
                 scope=SCOPE, access_type="offline", prompt="consent", state=state, include_granted_scopes="false")
        return f"{AUTH_URL}?{urlencode(q)}"

    def _token_request(self, data: dict) -> TokenSet:
        s = get_settings()
        r = httpx.post(TOKEN_URL, data={**data, "client_id": s.google_client_id,
                                        "client_secret": s.google_client_secret}, timeout=20)
        if r.status_code != 200:
            raise ProviderUnavailable(f"Google rejected the token request ({r.status_code}).")
        j = r.json()
        return TokenSet(j["access_token"], j.get("refresh_token"),
                        datetime.now(timezone.utc) + timedelta(seconds=int(j.get("expires_in", 3600))),
                        (j.get("scope") or SCOPE).split())

    def exchange_code(self, code, redirect_uri, code_verifier=None) -> TokenSet:
        return self._token_request({"code": code, "redirect_uri": redirect_uri, "grant_type": "authorization_code"})

    def refresh(self, tokens: TokenSet) -> TokenSet:
        if not tokens.refresh_token:
            raise ProviderUnavailable("No refresh token stored; please reconnect YouTube.")
        t = self._token_request({"refresh_token": tokens.refresh_token, "grant_type": "refresh_token"})
        t.refresh_token = tokens.refresh_token
        return t

    def _get(self, path: str, tokens: TokenSet, **params) -> dict:
        r = httpx.get(f"{API}/{path}", params=params, headers={"Authorization": f"Bearer {tokens.access_token}"}, timeout=20)
        if r.status_code == 401:
            raise ProviderUnavailable("YouTube access expired; please reconnect.")
        if r.status_code != 200:
            raise ProviderUnavailable(f"YouTube API error {r.status_code}.")
        return r.json()

    def fetch_account(self, tokens) -> AccountSnapshot:
        j = self._get("channels", tokens, part="snippet,statistics", mine="true")
        items = j.get("items") or []
        if not items:
            raise ProviderUnavailable("No YouTube channel found for this Google account.")
        ch = items[0]
        return AccountSnapshot(platform="youtube", account_label=ch["snippet"]["title"],
                               followers=int(ch["statistics"].get("subscriberCount", 0)), scopes=[SCOPE])

    def fetch_content(self, tokens, limit: int = 100) -> list[Content]:
        ch = self._get("channels", tokens, part="contentDetails", mine="true")["items"][0]
        uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
        ids: list[str] = []
        page = None
        while len(ids) < limit:
            j = self._get("playlistItems", tokens, part="contentDetails", playlistId=uploads,
                          maxResults=50, **({"pageToken": page} if page else {}))
            ids += [i["contentDetails"]["videoId"] for i in j.get("items", [])]
            page = j.get("nextPageToken")
            if not page:
                break
        out: list[Content] = []
        for i in range(0, len(ids[:limit]), 50):
            j = self._get("videos", tokens, part="snippet,statistics,contentDetails", id=",".join(ids[i:i + 50]))
            for v in j.get("items", []):
                st, sn = v.get("statistics", {}), v["snippet"]
                dur = _iso_duration(v["contentDetails"].get("duration", ""))
                out.append(Content(
                    platform="youtube", content_id=v["id"], content_type="short" if 0 < dur <= 60 else "video",
                    title=sn["title"], published_at=datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00")),
                    views=int(st.get("viewCount", 0)), likes=int(st.get("likeCount", 0)),
                    comments=int(st.get("commentCount", 0)), shares=0, duration_sec=dur or None,
                    category=infer_category(sn["title"] + " " + sn.get("description", "")[:200]),
                    metadata={"category_source": "heuristic", "shares_available": False}))
        return out
