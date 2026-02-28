"""
Pattern Vector Verdict Engine v2.0

AI-powered language judgment system with advanced features:
- v1: Core verdict engine + search API
- v2: Verdict Trace + Cross-Domain + Contradiction Detection + Immutable Log
"""

# v1 Core
from .verdict_engine import VerdictEngine
from .verdict_types import (
    Verdict, VerdictLevel, Constraint, Capability,
    VerdictDSLRule, FinalVerdict, LanguageVerdict
)

# v2 Advanced Features
from .verdict_trace import VerdictTracer, VerdictTraceChain, TraceStep
from .cross_domain_verdict import (
    CrossDomainVerdictEngine, CrossDomainConfig, CrossDomainVerdictResult
)
from .contradiction_detector import ContradictionDetector, ValidationResult
from .verdict_log import ImmutableVerdictLog, VerdictAuditTrail

__version__ = "2.0.0"
__all__ = [
    # v1
    "VerdictEngine",
    "Verdict",
    "VerdictLevel",
    "Constraint",
    "Capability",
    "VerdictDSLRule",
    "FinalVerdict",
    "LanguageVerdict",
    # v2
    "VerdictTracer",
    "VerdictTraceChain",
    "TraceStep",
    "CrossDomainVerdictEngine",
    "CrossDomainConfig",
    "CrossDomainVerdictResult",
    "ContradictionDetector",
    "ValidationResult",
    "ImmutableVerdictLog",
    "VerdictAuditTrail",
]
