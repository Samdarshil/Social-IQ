"""Instagram, X and LinkedIn adapters.

API reality (stated plainly, not hidden):
  * Instagram: needs a Business/Creator account and Meta app review for insights.
  * X: reading your own post metrics needs a paid X API tier.
  * LinkedIn: member post analytics require LinkedIn partner approval. Without it this adapter
    refuses to fabricate anything and reports the limitation.
Each adapter works only when real credentials are supplied; otherwise the UI shows "Not configured".
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

from app.config import get_settings
from app.integrations.base import ProviderAdapter, ProviderUnavailable, TokenSet
from app.schemas.content import AccountSnapshot, Content
from app.utils.categorize import infer_category


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00").replace("+0000", "+00:00"))


class InstagramAdapter(ProviderAdapter):
    platform = "instagram"
    label = "Instagram"
    read_only_scopes = ["instagram_business_basic", "instagram_business_manage_insights"]
    api_notes = ("Requires an Instagram Business or Creator account. Reads media and insight counts only; "
                 "never posts, comments or messages.")

    def is_configured(self) -> bool:
        s = get_settings()
        return bool(s.instagram_client_id and s.instagram_client_secret)

    def authorization_url(self, state, redirect_uri, code_challenge=None) -> str:
        if not self.is_configured():
            raise ProviderUnavailable("Instagram OAuth credentials are not configured on this server.")
        q = dict(client_id=get_settings().instagram_client_id, redirect_uri=redirect_uri, response_type="code",
                 scope=",".join(self.read_only_scopes), state=state)
        return f"https://www.instagram.com/oauth/authorize?{urlencode(q)}"

    def exchange_code(self, code, redirect_uri, code_verifier=None) -> TokenSet:
        s = get_settings()
        r = httpx.post("https://api.instagram.com/oauth/access_token", data=dict(
            client_id=s.instagram_client_id, client_secret=s.instagram_client_secret, grant_type="authorization_code",
            redirect_uri=redirect_uri, code=code), timeout=20)
        if r.status_code != 200:
            raise ProviderUnavailable(f"Instagram rejected the token request ({r.status_code}).")
        short = r.json()["access_token"]
        r2 = httpx.get("https://graph.instagram.com/access_token", params=dict(
            grant_type="ig_exchange_token", client_secret=s.instagram_client_secret, access_token=short), timeout=20)
        if r2.status_code == 200:
            j = r2.json()
            return TokenSet(j["access_token"], None, datetime.now(timezone.utc) + timedelta(seconds=int(j.get("expires_in", 5184000))),
                            self.read_only_scopes)
        return TokenSet(short, None, None, self.read_only_scopes)

    def _get(self, path: str, tokens: TokenSet, **params) -> dict:
        r = httpx.get(f"https://graph.instagram.com/{path}", params={**params, "access_token": tokens.access_token}, timeout=20)
        if r.status_code != 200:
            raise ProviderUnavailable(f"Instagram API error {r.status_code}.")
        return r.json()

    def fetch_account(self, tokens) -> AccountSnapshot:
        j = self._get("me", tokens, fields="username,followers_count")
        return AccountSnapshot(platform="instagram", account_label="@" + j.get("username", "instagram"),
                               followers=int(j.get("followers_count", 0)), scopes=self.read_only_scopes)

    def fetch_content(self, tokens, limit: int = 100) -> list[Content]:
        j = self._get("me/media", tokens, limit=min(limit, 50),
                      fields="id,caption,media_type,media_product_type,timestamp,like_count,comments_count")
        out = []
        for m in j.get("data", []):
            try:
                ins = self._get(f"{m['id']}/insights", tokens, metric="views,shares")
                vals = {d["name"]: d["values"][0]["value"] for d in ins.get("data", [])}
            except ProviderUnavailable:
                continue  # insights unavailable for this media: skip rather than invent numbers
            if "views" not in vals:
                continue
            ctype = "reel" if m.get("media_product_type") == "REELS" else \
                "carousel" if m.get("media_type") == "CAROUSEL_ALBUM" else "image"
            cap = m.get("caption") or ""
            out.append(Content(platform="instagram", content_id=m["id"], content_type=ctype, title=cap[:200],
                               published_at=_ts(m["timestamp"]), views=int(vals["views"]), likes=int(m.get("like_count", 0)),
                               comments=int(m.get("comments_count", 0)), shares=int(vals.get("shares", 0)),
                               category=infer_category(cap), metadata={"category_source": "heuristic"}))
        return out


class XAdapter(ProviderAdapter):
    platform = "x"
    label = "X"
    read_only_scopes = ["tweet.read", "users.read", "offline.access"]
    api_notes = "Read-only. Reading your own post metrics requires an X API plan that includes it. Never posts or deletes."
    uses_pkce = True

    def is_configured(self) -> bool:
        s = get_settings()
        return bool(s.x_client_id and s.x_client_secret)

    def authorization_url(self, state, redirect_uri, code_challenge=None) -> str:
        if not self.is_configured():
            raise ProviderUnavailable("X OAuth credentials are not configured on this server.")
        q = dict(response_type="code", client_id=get_settings().x_client_id, redirect_uri=redirect_uri,
                 scope=" ".join(self.read_only_scopes), state=state, code_challenge=code_challenge,
                 code_challenge_method="S256")
        return f"https://twitter.com/i/oauth2/authorize?{urlencode(q)}"

    def _basic(self) -> dict:
        s = get_settings()
        return {"Authorization": "Basic " + base64.b64encode(f"{s.x_client_id}:{s.x_client_secret}".encode()).decode()}

    def exchange_code(self, code, redirect_uri, code_verifier=None) -> TokenSet:
        r = httpx.post("https://api.twitter.com/2/oauth2/token", headers=self._basic(), data=dict(
            code=code, grant_type="authorization_code", redirect_uri=redirect_uri, code_verifier=code_verifier or ""), timeout=20)
        if r.status_code != 200:
            raise ProviderUnavailable(f"X rejected the token request ({r.status_code}).")
        j = r.json()
        return TokenSet(j["access_token"], j.get("refresh_token"),
                        datetime.now(timezone.utc) + timedelta(seconds=int(j.get("expires_in", 7200))), self.read_only_scopes)

    def _get(self, path: str, tokens: TokenSet, **params) -> dict:
        r = httpx.get(f"https://api.twitter.com/2/{path}", params=params, headers={"Authorization": f"Bearer {tokens.access_token}"}, timeout=20)
        if r.status_code in (401, 403):
            raise ProviderUnavailable("X denied access (expired token or your API plan does not include this data).")
        if r.status_code != 200:
            raise ProviderUnavailable(f"X API error {r.status_code}.")
        return r.json()

    def fetch_account(self, tokens) -> AccountSnapshot:
        d = self._get("users/me", tokens, **{"user.fields": "public_metrics,username"})["data"]
        return AccountSnapshot(platform="x", account_label="@" + d["username"],
                               followers=int(d["public_metrics"]["followers_count"]), scopes=self.read_only_scopes)

    def fetch_content(self, tokens, limit: int = 100) -> list[Content]:
        uid = self._get("users/me", tokens)["data"]["id"]
        j = self._get(f"users/{uid}/tweets", tokens, max_results=min(max(limit, 5), 100),
                      **{"tweet.fields": "created_at,public_metrics,referenced_tweets", "exclude": "retweets,replies"})
        out = []
        for t in j.get("data", []):
            pm = t["public_metrics"]
            if "impression_count" not in pm:
                continue
            out.append(Content(platform="x", content_id=t["id"], content_type="post", title=t["text"][:200],
                               published_at=_ts(t["created_at"]), views=int(pm["impression_count"]), likes=int(pm["like_count"]),
                               comments=int(pm["reply_count"]), shares=int(pm["retweet_count"]) + int(pm.get("quote_count", 0)),
                               category=infer_category(t["text"]), metadata={"category_source": "heuristic"}))
        return out


class LinkedInAdapter(ProviderAdapter):
    platform = "linkedin"
    label = "LinkedIn"
    read_only_scopes = ["openid", "profile"]
    api_notes = ("LinkedIn only shares member post analytics with approved partners. Without that approval SocialIQ "
                 "cannot read your LinkedIn performance, and will say so instead of guessing.")

    def is_configured(self) -> bool:
        s = get_settings()
        return bool(s.linkedin_client_id and s.linkedin_client_secret)

    def authorization_url(self, state, redirect_uri, code_challenge=None) -> str:
        if not self.is_configured():
            raise ProviderUnavailable("LinkedIn OAuth credentials are not configured on this server.")
        q = dict(response_type="code", client_id=get_settings().linkedin_client_id, redirect_uri=redirect_uri,
                 state=state, scope=" ".join(self.read_only_scopes))
        return f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(q)}"

    def exchange_code(self, code, redirect_uri, code_verifier=None) -> TokenSet:
        s = get_settings()
        r = httpx.post("https://www.linkedin.com/oauth/v2/accessToken", data=dict(
            grant_type="authorization_code", code=code, redirect_uri=redirect_uri,
            client_id=s.linkedin_client_id, client_secret=s.linkedin_client_secret), timeout=20)
        if r.status_code != 200:
            raise ProviderUnavailable(f"LinkedIn rejected the token request ({r.status_code}).")
        j = r.json()
        return TokenSet(j["access_token"], None, datetime.now(timezone.utc) + timedelta(seconds=int(j.get("expires_in", 5184000))),
                        self.read_only_scopes)

    def fetch_account(self, tokens) -> AccountSnapshot:
        r = httpx.get("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {tokens.access_token}"}, timeout=20)
        name = r.json().get("name", "LinkedIn member") if r.status_code == 200 else "LinkedIn member"
        return AccountSnapshot(platform="linkedin", account_label=name, followers=0, scopes=self.read_only_scopes)

    def fetch_content(self, tokens, limit: int = 100) -> list[Content]:
        raise ProviderUnavailable(
            "LinkedIn does not provide post analytics to apps without partner approval, so no LinkedIn data can be "
            "synced. Demo mode shows how LinkedIn would appear.")
