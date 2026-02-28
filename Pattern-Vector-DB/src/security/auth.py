"""
Authentication & Security for Pattern Vector Verdict Engine
JWT 토큰 기반 인증, Rate Limiting
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
import hashlib
import secrets
from fastapi import HTTPException, status
from pydantic import BaseModel


# ============================================================================
# JWT Configuration
# ============================================================================

class JWTConfig:
    """JWT 설정"""
    def __init__(
        self,
        secret_key: str = "your-secret-key-change-in-production",
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days


# ============================================================================
# Token Models
# ============================================================================

class TokenPayload(BaseModel):
    """토큰 페이로드"""
    sub: str  # subject (user_id)
    exp: datetime
    iat: datetime
    scopes: list = []
    api_key: Optional[str] = None


class AccessToken(BaseModel):
    """액세스 토큰"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class APIKey(BaseModel):
    """API 키"""
    key: str
    name: str
    created_at: datetime
    last_used: Optional[datetime] = None
    is_active: bool = True


# ============================================================================
# JWT Manager
# ============================================================================

class JWTManager:
    """JWT 관리"""

    def __init__(self, config: Optional[JWTConfig] = None):
        """초기화"""
        self.config = config or JWTConfig()

    def create_access_token(self, user_id: str, scopes: list = []) -> str:
        """액세스 토큰 생성"""
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.config.access_token_expire_minutes)

        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": now,
            "scopes": scopes,
        }

        token = jwt.encode(
            payload,
            self.config.secret_key,
            algorithm=self.config.algorithm,
        )

        return token

    def create_refresh_token(self, user_id: str) -> str:
        """리프레시 토큰 생성"""
        now = datetime.utcnow()
        expire = now + timedelta(days=self.config.refresh_token_expire_days)

        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": now,
            "type": "refresh",
        }

        token = jwt.encode(
            payload,
            self.config.secret_key,
            algorithm=self.config.algorithm,
        )

        return token

    def create_tokens(self, user_id: str, scopes: list = []) -> AccessToken:
        """액세스 및 리프레시 토큰 생성"""
        access_token = self.create_access_token(user_id, scopes)
        refresh_token = self.create_refresh_token(user_id)

        return AccessToken(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.config.access_token_expire_minutes * 60,
        )

    def verify_token(self, token: str) -> TokenPayload:
        """토큰 검증"""
        try:
            payload = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm],
            )

            return TokenPayload(
                sub=payload.get("sub"),
                exp=datetime.fromtimestamp(payload.get("exp")),
                iat=datetime.fromtimestamp(payload.get("iat")),
                scopes=payload.get("scopes", []),
            )

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

    def refresh_access_token(self, refresh_token: str) -> str:
        """액세스 토큰 갱신"""
        try:
            payload = jwt.decode(
                refresh_token,
                self.config.secret_key,
                algorithms=[self.config.algorithm],
            )

            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not a refresh token",
                )

            user_id = payload.get("sub")
            return self.create_access_token(user_id)

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired",
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )


# ============================================================================
# API Key Manager
# ============================================================================

class APIKeyManager:
    """API 키 관리"""

    def __init__(self):
        """초기화"""
        self.keys: Dict[str, APIKey] = {}

    def generate_key(self, name: str) -> str:
        """API 키 생성"""
        key = secrets.token_urlsafe(32)

        api_key = APIKey(
            key=key,
            name=name,
            created_at=datetime.utcnow(),
        )

        self.keys[key] = api_key
        return key

    def verify_key(self, key: str) -> APIKey:
        """API 키 검증"""
        if key not in self.keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )

        api_key = self.keys[key]

        if not api_key.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key is inactive",
            )

        # 마지막 사용 시간 업데이트
        api_key.last_used = datetime.utcnow()

        return api_key

    def revoke_key(self, key: str):
        """API 키 폐지"""
        if key in self.keys:
            self.keys[key].is_active = False

    def get_keys(self, user_id: str = None) -> list:
        """사용자의 API 키 목록"""
        return list(self.keys.values())


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """Rate Limiting (고정 윈도우)"""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """초기화"""
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}

    def is_allowed(self, identifier: str) -> bool:
        """요청 허용 여부"""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)

        if identifier not in self.requests:
            self.requests[identifier] = []

        # 윈도우 밖의 요청 제거
        self.requests[identifier] = [
            req_time
            for req_time in self.requests[identifier]
            if req_time > window_start
        ]

        # 요청 개수 확인
        if len(self.requests[identifier]) < self.max_requests:
            self.requests[identifier].append(now)
            return True

        return False

    def get_remaining(self, identifier: str) -> int:
        """남은 요청 개수"""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)

        if identifier not in self.requests:
            return self.max_requests

        recent_requests = [
            req_time
            for req_time in self.requests[identifier]
            if req_time > window_start
        ]

        return max(0, self.max_requests - len(recent_requests))

    def get_reset_time(self, identifier: str) -> Optional[datetime]:
        """초기화 시간"""
        if identifier not in self.requests or not self.requests[identifier]:
            return None

        oldest_request = min(self.requests[identifier])
        return oldest_request + timedelta(seconds=self.window_seconds)


# ============================================================================
# Global Instances
# ============================================================================

jwt_manager = JWTManager()
api_key_manager = APIKeyManager()
rate_limiter = RateLimiter(max_requests=1000, window_seconds=60)  # 분당 1000개 요청


# ============================================================================
# Helper Functions
# ============================================================================

def hash_password(password: str) -> str:
    """비밀번호 해싱"""
    salt = secrets.token_hex(32)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000,
    )
    return f"{salt}${pwd_hash.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """비밀번호 검증"""
    try:
        salt, pwd_hash = hashed.split("$")
        pwd_hash_check = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000,
        )
        return pwd_hash_check.hex() == pwd_hash
    except ValueError:
        return False
