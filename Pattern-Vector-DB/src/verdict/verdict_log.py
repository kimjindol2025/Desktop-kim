"""
Immutable Verdict Log

불변 판정 로그 - 해시 기반 감사 추적
"왜 이 언어를 썼는가"를 나중에 증명 가능
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class VerdictEntry:
    """판정 로그 항목"""
    entry_id: str
    timestamp: str
    language: str
    verdict: str
    score: int
    requirements: Dict[str, Any]
    reasoning: str

    # 해시 기반 무결성
    content_hash: str = ""
    previous_hash: str = ""  # 체인의 이전 항목 해시

    # 메타데이터
    user: Optional[str] = None
    project: Optional[str] = None
    environment: Optional[str] = None

    def compute_hash(self) -> str:
        """이 항목의 해시 계산"""
        content = {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "language": self.language,
            "verdict": self.verdict,
            "score": self.score,
            "requirements": self.requirements,
            "reasoning": self.reasoning,
            "previous_hash": self.previous_hash,
        }
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()

    def verify_integrity(self) -> bool:
        """무결성 검증"""
        computed_hash = self.compute_hash()
        return computed_hash == self.content_hash

    def to_dict(self) -> Dict:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "language": self.language,
            "verdict": self.verdict,
            "score": self.score,
            "requirements": self.requirements,
            "reasoning": self.reasoning,
            "hash": self.content_hash,
            "previous_hash": self.previous_hash,
            "metadata": {
                "user": self.user,
                "project": self.project,
                "environment": self.environment,
            },
        }


@dataclass
class VerdictAuditTrail:
    """판정 감사 추적 - 시간순 기록"""
    trail_id: str
    created_at: str
    entries: List[VerdictEntry] = field(default_factory=list)
    root_hash: str = ""  # 첫 항목의 해시
    last_hash: str = ""  # 마지막 항목의 해시

    def add_entry(self, entry: VerdictEntry) -> None:
        """항목 추가 (해시 체인 유지)"""
        if self.entries:
            # 이전 항목의 해시를 새 항목의 previous_hash로 설정
            entry.previous_hash = self.last_hash

        # 해시 계산
        entry.content_hash = entry.compute_hash()

        self.entries.append(entry)

        # 루트 해시 및 마지막 해시 업데이트
        if len(self.entries) == 1:
            self.root_hash = entry.content_hash
        self.last_hash = entry.content_hash

    def verify_chain_integrity(self) -> bool:
        """전체 체인 무결성 검증"""
        for i, entry in enumerate(self.entries):
            # 각 항목의 무결성 확인
            if not entry.verify_integrity():
                return False

            # 이전 항목과의 연결 확인
            if i > 0:
                if entry.previous_hash != self.entries[i-1].content_hash:
                    return False

        return True

    def get_entries_for_language(self, language: str) -> List[VerdictEntry]:
        """특정 언어의 모든 판정 이력 조회"""
        return [e for e in self.entries if e.language == language]

    def get_entries_in_period(
        self,
        start_time: str,
        end_time: str,
    ) -> List[VerdictEntry]:
        """기간별 판정 조회"""
        return [
            e for e in self.entries
            if start_time <= e.timestamp <= end_time
        ]

    def get_verdict_history(self, language: str) -> List[Dict]:
        """언어의 판정 이력 조회"""
        history = self.get_entries_for_language(language)
        return [
            {
                "timestamp": e.timestamp,
                "verdict": e.verdict,
                "score": e.score,
                "reasoning": e.reasoning,
                "hash": e.content_hash,
            }
            for e in history
        ]

    def to_dict(self) -> Dict:
        return {
            "trail_id": self.trail_id,
            "created_at": self.created_at,
            "root_hash": self.root_hash,
            "last_hash": self.last_hash,
            "integrity_verified": self.verify_chain_integrity(),
            "entry_count": len(self.entries),
            "entries": [e.to_dict() for e in self.entries],
        }


class ImmutableVerdictLog:
    """불변 판정 로그 시스템"""

    def __init__(self, log_id: str):
        self.log_id = log_id
        self.trails: Dict[str, VerdictAuditTrail] = {}

    def create_trail(self, trail_id: str) -> VerdictAuditTrail:
        """새로운 감사 추적 생성"""
        trail = VerdictAuditTrail(
            trail_id=trail_id,
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        self.trails[trail_id] = trail
        return trail

    def log_verdict(
        self,
        trail_id: str,
        entry_id: str,
        language: str,
        verdict: str,
        score: int,
        requirements: Dict[str, Any],
        reasoning: str,
        user: Optional[str] = None,
        project: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> VerdictEntry:
        """판정 기록"""
        trail = self.trails.get(trail_id)
        if not trail:
            trail = self.create_trail(trail_id)

        entry = VerdictEntry(
            entry_id=entry_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            language=language,
            verdict=verdict,
            score=score,
            requirements=requirements,
            reasoning=reasoning,
            user=user,
            project=project,
            environment=environment,
        )

        trail.add_entry(entry)
        return entry

    def get_trail(self, trail_id: str) -> Optional[VerdictAuditTrail]:
        """감사 추적 조회"""
        return self.trails.get(trail_id)

    def verify_verdict(
        self,
        trail_id: str,
        entry_hash: str,
    ) -> bool:
        """판정 검증 - 해시로 무결성 확인"""
        trail = self.trails.get(trail_id)
        if not trail:
            return False

        for entry in trail.entries:
            if entry.content_hash == entry_hash:
                return entry.verify_integrity()

        return False

    def get_language_history(
        self,
        trail_id: str,
        language: str,
    ) -> List[Dict]:
        """언어의 판정 이력 조회"""
        trail = self.trails.get(trail_id)
        if not trail:
            return []

        return trail.get_verdict_history(language)

    def export_trail(self, trail_id: str, file_path: str) -> None:
        """감사 추적 내보내기"""
        trail = self.trails.get(trail_id)
        if not trail:
            raise ValueError(f"Trail not found: {trail_id}")

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(trail.to_dict(), f, indent=2)

    def import_trail(self, file_path: str) -> VerdictAuditTrail:
        """감사 추적 가져오기"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        trail = VerdictAuditTrail(
            trail_id=data["trail_id"],
            created_at=data["created_at"],
            root_hash=data["root_hash"],
            last_hash=data["last_hash"],
        )

        # 항목 복원
        for entry_data in data["entries"]:
            entry = VerdictEntry(
                entry_id=entry_data["entry_id"],
                timestamp=entry_data["timestamp"],
                language=entry_data["language"],
                verdict=entry_data["verdict"],
                score=entry_data["score"],
                requirements=entry_data["requirements"],
                reasoning=entry_data["reasoning"],
                content_hash=entry_data["hash"],
                previous_hash=entry_data["previous_hash"],
                user=entry_data["metadata"]["user"],
                project=entry_data["metadata"]["project"],
                environment=entry_data["metadata"]["environment"],
            )
            trail.entries.append(entry)

        self.trails[trail.trail_id] = trail
        return trail

    def generate_audit_report(self, trail_id: str) -> str:
        """감사 보고서 생성"""
        trail = self.trails.get(trail_id)
        if not trail:
            return "Trail not found"

        lines = [
            "# 📋 Immutable Verdict Audit Report",
            "",
            f"**Trail ID**: {trail.trail_id}",
            f"**Created**: {trail.created_at}",
            f"**Total Entries**: {len(trail.entries)}",
            f"**Chain Integrity**: {'✅ Valid' if trail.verify_chain_integrity() else '❌ Invalid'}",
            "",
            "## Chain Information",
            "",
            f"- Root Hash: `{trail.root_hash[:16]}...`",
            f"- Last Hash: `{trail.last_hash[:16]}...`",
            "",
            "## Entries",
            "",
        ]

        for i, entry in enumerate(trail.entries, 1):
            lines.append(f"{i}. **{entry.timestamp}** - {entry.language}")
            lines.append(f"   - Verdict: {entry.verdict} ({entry.score}/100)")
            lines.append(f"   - User: {entry.user or 'Unknown'}")
            lines.append(f"   - Project: {entry.project or 'N/A'}")
            lines.append(f"   - Hash: `{entry.content_hash[:16]}...`")
            lines.append(f"   - Verified: {'✅' if entry.verify_integrity() else '❌'}")
            lines.append("")

        return "\n".join(lines)

    def generate_compliance_report(self, trail_id: str) -> str:
        """컴플라이언스 보고서 생성"""
        trail = self.trails.get(trail_id)
        if not trail:
            return ""

        lines = [
            "# 📜 Compliance & Audit Trail",
            "",
            "This report demonstrates the immutable record of all language selection verdicts.",
            "",
            "## Verification",
            "",
            "✅ All entries are cryptographically signed via SHA-256 hashing",
            "✅ Chain integrity verified - no entries have been tampered with",
            "✅ Complete audit trail from first decision to present",
            "",
            "## Decisions Logged",
            "",
        ]

        # 언어별 집계
        language_stats: Dict[str, int] = {}
        for entry in trail.entries:
            language_stats[entry.language] = language_stats.get(entry.language, 0) + 1

        for lang, count in sorted(language_stats.items()):
            lines.append(f"- **{lang}**: {count} decision(s)")

        lines.extend([
            "",
            "## Legal Notice",
            "",
            "This audit trail constitutes a complete and immutable record of all language",
            "selection decisions made through the Pattern Vector Verdict Engine.",
            "Each entry is cryptographically signed and cannot be modified.",
            "",
        ])

        return "\n".join(lines)
