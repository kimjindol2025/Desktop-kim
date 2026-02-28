"""
Advanced Logging System for Pattern Vector Verdict Engine
프로덕션급 로깅, 모니터링, 알림
"""

import logging
import logging.handlers
import json
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import sys


class JSONFormatter(logging.Formatter):
    """JSON 형식 로그"""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id

        if hasattr(record, "user_id"):
            log_obj["user_id"] = record.user_id

        return json.dumps(log_obj, ensure_ascii=False)


class StructuredLogger:
    """구조화된 로깅"""

    def __init__(self, name: str, log_dir: str = "logs"):
        """초기화"""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # 콘솔 핸들러
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # 파일 핸들러 (일반 로그)
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / f"{name}.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # JSON 로그 핸들러
        json_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / f"{name}_json.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=10,
        )
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(json_handler)

    def log_request(
        self,
        request_id: str,
        method: str,
        endpoint: str,
        status_code: int,
        response_time_ms: float,
        user_id: Optional[str] = None,
    ):
        """요청 로깅"""
        extra = {"request_id": request_id, "user_id": user_id}

        self.logger.info(
            f"HTTP {method} {endpoint} - {status_code} ({response_time_ms:.2f}ms)",
            extra=extra,
        )

    def log_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        request_id: Optional[str] = None,
    ):
        """에러 로깅"""
        extra = {"request_id": request_id}
        self.logger.exception(f"Error in {context}: {str(error)}", extra=extra)

    def log_verdict(
        self,
        request_id: str,
        verdict_id: str,
        language: str,
        verdict: str,
        score: float,
        duration_ms: float,
    ):
        """판정 결과 로깅"""
        extra = {"request_id": request_id}
        self.logger.info(
            f"Verdict: {language} -> {verdict} ({score}/100) [{duration_ms:.2f}ms]",
            extra=extra,
        )

    def log_cache_event(
        self,
        event: str,
        key: str,
        hit: bool = False,
        ttl: Optional[int] = None,
    ):
        """캐시 이벤트 로깅"""
        if hit:
            self.logger.debug(f"Cache HIT: {key}")
        else:
            self.logger.debug(f"Cache {event}: {key}" + (f" (TTL: {ttl}s)" if ttl else ""))

    def log_performance_alert(
        self,
        metric: str,
        value: float,
        threshold: float,
        request_id: Optional[str] = None,
    ):
        """성능 알림 로깅"""
        extra = {"request_id": request_id}
        self.logger.warning(
            f"Performance Alert: {metric}={value:.2f} (threshold: {threshold})",
            extra=extra,
        )

    def log_security_event(
        self,
        event: str,
        user_id: str,
        ip_address: str,
        details: Dict[str, Any],
    ):
        """보안 이벤트 로깅"""
        extra = {"user_id": user_id}
        self.logger.warning(
            f"Security Event: {event} from {ip_address} - {details}",
            extra=extra,
        )


# 글로벌 로거 인스턴스
_logger_instance = None


def get_logger(name: str = "verdict_engine") -> StructuredLogger:
    """로거 인스턴스 반환"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = StructuredLogger(name)
    return _logger_instance


class LoggingMiddleware:
    """로깅 미들웨어 (FastAPI)"""

    def __init__(self, app, logger: Optional[StructuredLogger] = None):
        """초기화"""
        self.app = app
        self.logger = logger or get_logger()

    async def __call__(self, scope, receive, send):
        """ASGI 미들웨어"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = scope.get("headers", {}).get(b"x-request-id", b"unknown").decode()
        method = scope["method"]
        path = scope["path"]
        client = scope.get("client", ("unknown", 0))[0]

        import time
        start_time = time.time()
        status_code = 200

        async def send_with_logging(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_with_logging)
        except Exception as e:
            self.logger.log_error(e, {"path": path, "method": method}, request_id)
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.log_request(
                request_id,
                method,
                path,
                status_code,
                duration_ms,
            )

            # 성능 알림
            if duration_ms > 500:
                self.logger.log_performance_alert(
                    "response_time",
                    duration_ms,
                    500,
                    request_id,
                )
