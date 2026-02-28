"""
Performance Monitoring for Pattern Vector Verdict Engine
응답시간, 메모리 사용, 캐시 효율성 모니터링
"""

import time
import psutil
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import statistics
import logging

logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """요청 메트릭"""
    request_id: str
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    timestamp: str
    memory_used_mb: float
    cache_hit: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PerformanceMonitor:
    """성능 모니터링 시스템"""

    def __init__(self, max_history: int = 10000):
        """초기화"""
        self.max_history = max_history
        self.request_metrics: List[RequestMetrics] = []
        self.start_time = time.time()
        self.process = psutil.Process(os.getpid())

    def record_request(
        self,
        request_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        cache_hit: bool = False,
    ) -> None:
        """요청 기록"""
        try:
            memory_used = self.process.memory_info().rss / 1024 / 1024  # MB

            metric = RequestMetrics(
                request_id=request_id,
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                response_time_ms=response_time_ms,
                timestamp=datetime.now().isoformat(),
                memory_used_mb=memory_used,
                cache_hit=cache_hit,
            )

            self.request_metrics.append(metric)

            # 히스토리 크기 제한
            if len(self.request_metrics) > self.max_history:
                self.request_metrics.pop(0)

            logger.debug(f"Request recorded: {request_id} ({response_time_ms:.2f}ms)")

        except Exception as e:
            logger.error(f"Error recording metrics: {e}")

    def get_endpoint_stats(self, endpoint: str) -> Dict[str, Any]:
        """엔드포인트별 통계"""
        metrics = [m for m in self.request_metrics if m.endpoint == endpoint]

        if not metrics:
            return {}

        response_times = [m.response_time_ms for m in metrics]
        cache_hits = sum(1 for m in metrics if m.cache_hit)

        return {
            "endpoint": endpoint,
            "total_requests": len(metrics),
            "avg_response_time_ms": statistics.mean(response_times),
            "min_response_time_ms": min(response_times),
            "max_response_time_ms": max(response_times),
            "median_response_time_ms": statistics.median(response_times),
            "stdev_response_time_ms": statistics.stdev(response_times) if len(response_times) > 1 else 0,
            "cache_hit_rate": f"{(cache_hits / len(metrics) * 100):.2f}%",
            "avg_memory_usage_mb": statistics.mean([m.memory_used_mb for m in metrics]),
        }

    def get_overall_stats(self) -> Dict[str, Any]:
        """전체 통계"""
        if not self.request_metrics:
            return {}

        response_times = [m.response_time_ms for m in self.request_metrics]
        success_requests = sum(1 for m in self.request_metrics if 200 <= m.status_code < 300)
        error_requests = sum(1 for m in self.request_metrics if m.status_code >= 400)
        cache_hits = sum(1 for m in self.request_metrics if m.cache_hit)

        uptime_seconds = time.time() - self.start_time

        return {
            "total_requests": len(self.request_metrics),
            "successful_requests": success_requests,
            "error_requests": error_requests,
            "success_rate": f"{(success_requests / len(self.request_metrics) * 100):.2f}%",
            "avg_response_time_ms": statistics.mean(response_times),
            "min_response_time_ms": min(response_times),
            "max_response_time_ms": max(response_times),
            "median_response_time_ms": statistics.median(response_times),
            "p95_response_time_ms": sorted(response_times)[int(len(response_times) * 0.95)] if response_times else 0,
            "p99_response_time_ms": sorted(response_times)[int(len(response_times) * 0.99)] if response_times else 0,
            "cache_hit_rate": f"{(cache_hits / len(self.request_metrics) * 100):.2f}%",
            "avg_memory_usage_mb": statistics.mean([m.memory_used_mb for m in self.request_metrics]),
            "uptime_seconds": int(uptime_seconds),
        }

    def get_method_stats(self) -> Dict[str, Dict[str, Any]]:
        """HTTP 메서드별 통계"""
        methods = set(m.method for m in self.request_metrics)
        stats = {}

        for method in methods:
            method_metrics = [m for m in self.request_metrics if m.method == method]
            response_times = [m.response_time_ms for m in method_metrics]

            stats[method] = {
                "count": len(method_metrics),
                "avg_response_time_ms": statistics.mean(response_times),
                "total_time_ms": sum(response_times),
            }

        return stats

    def get_slowest_requests(self, limit: int = 10) -> List[RequestMetrics]:
        """가장 느린 요청들"""
        sorted_metrics = sorted(
            self.request_metrics,
            key=lambda m: m.response_time_ms,
            reverse=True
        )
        return sorted_metrics[:limit]

    def get_error_summary(self) -> Dict[int, int]:
        """오류 요약"""
        error_codes = {}
        for metric in self.request_metrics:
            if metric.status_code >= 400:
                error_codes[metric.status_code] = error_codes.get(metric.status_code, 0) + 1

        return error_codes

    def export_report(self) -> str:
        """마크다운 리포트 생성"""
        overall = self.get_overall_stats()
        endpoints = {}
        for metric in self.request_metrics:
            if metric.endpoint not in endpoints:
                endpoints[metric.endpoint] = self.get_endpoint_stats(metric.endpoint)

        methods = self.get_method_stats()
        errors = self.get_error_summary()
        slowest = self.get_slowest_requests(10)

        report = f"""
# Performance Report

Generated: {datetime.now().isoformat()}

## Overall Statistics

- **Total Requests**: {overall.get('total_requests', 0)}
- **Success Rate**: {overall.get('success_rate', 'N/A')}
- **Average Response Time**: {overall.get('avg_response_time_ms', 0):.2f}ms
- **Median Response Time**: {overall.get('median_response_time_ms', 0):.2f}ms
- **P95 Response Time**: {overall.get('p95_response_time_ms', 0):.2f}ms
- **P99 Response Time**: {overall.get('p99_response_time_ms', 0):.2f}ms
- **Cache Hit Rate**: {overall.get('cache_hit_rate', 'N/A')}
- **Average Memory Usage**: {overall.get('avg_memory_usage_mb', 0):.2f}MB
- **Uptime**: {overall.get('uptime_seconds', 0)} seconds

## Endpoint Statistics

"""

        for endpoint, stats in endpoints.items():
            report += f"\n### {endpoint}\n\n"
            report += f"- **Total Requests**: {stats.get('total_requests', 0)}\n"
            report += f"- **Avg Response Time**: {stats.get('avg_response_time_ms', 0):.2f}ms\n"
            report += f"- **Min/Max Response Time**: {stats.get('min_response_time_ms', 0):.2f}ms / {stats.get('max_response_time_ms', 0):.2f}ms\n"
            report += f"- **Cache Hit Rate**: {stats.get('cache_hit_rate', 'N/A')}\n"
            report += f"- **Avg Memory Usage**: {stats.get('avg_memory_usage_mb', 0):.2f}MB\n"

        report += f"\n## HTTP Method Statistics\n\n"
        for method, stats in methods.items():
            report += f"- **{method}**: {stats['count']} requests, {stats['avg_response_time_ms']:.2f}ms avg\n"

        if errors:
            report += f"\n## Error Summary\n\n"
            for code, count in errors.items():
                report += f"- **{code}**: {count} errors\n"

        if slowest:
            report += f"\n## Slowest Requests\n\n"
            for i, metric in enumerate(slowest, 1):
                report += f"{i}. {metric.endpoint} ({metric.response_time_ms:.2f}ms) - {metric.timestamp}\n"

        return report

    def clear_history(self):
        """히스토리 초기화"""
        self.request_metrics.clear()
        self.start_time = time.time()


# 글로벌 모니터 인스턴스
_monitor_instance = None


def get_monitor() -> PerformanceMonitor:
    """모니터 인스턴스 반환"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = PerformanceMonitor()
    return _monitor_instance


def timing_middleware(func):
    """응답 시간 측정 데코레이터"""
    import functools
    from uuid import uuid4

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        request_id = str(uuid4())[:8]

        try:
            result = func(*args, **kwargs)
            return result
        finally:
            response_time_ms = (time.time() - start_time) * 1000
            monitor = get_monitor()

            # 간단한 엔드포인트 정보 추출
            endpoint = getattr(func, "__name__", "unknown")
            monitor.record_request(
                request_id=request_id,
                endpoint=endpoint,
                method="function",
                status_code=200,
                response_time_ms=response_time_ms,
            )

    return wrapper
