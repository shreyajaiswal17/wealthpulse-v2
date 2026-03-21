import httpx
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from functools import lru_cache
from core.config import settings

ALGORITHMS = ["RS256"]

bearer_scheme = HTTPBearer()


@lru_cache(maxsize=1)
def _fetch_jwks() -> dict:
    """Fetch Auth0 JWKS synchronously (cached for the process lifetime).

    python-jose requires a dict of the JWKS. The lru_cache means we only
    hit the network once per worker process. If Auth0 ever rotates keys,
    restart the server (or bump maxsize / add a TTL wrapper).
    """
    url = f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json"
    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


async def get_current_user(request: Request):
    # TODO: restore JWT validation before production deploy
    # Extract user ID from Authorization header if present
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        try:
            import base64, json
            # decode middle part of JWT/JWE to get sub
            payload = token.split(".")[1]
            payload += "=" * (4 - len(payload) % 4)
            data = json.loads(base64.urlsafe_b64decode(payload))
            return {"sub": data.get("sub", "anonymous")}
        except Exception:
            pass
    raise HTTPException(status_code=401, detail="Not authenticated")
