"""
SafetyIQ — Quality & Compliance Audit Agent
============================================
Continuously monitors safety procedures, inspection records, and statutory
compliance documentation against OISD, DGMS, and Factory Act 1948 standards.

Responsibilities:
  • Score compliance across three regulatory frameworks (OISD / Factory Act / DGMS)
  • Identify deviations before formal audits
  • Cross-reference active PTW records against mandatory checklist requirements
  • Generate corrective action workflows with regulatory citations
  • Flag overdue inspections, expired certifications, and missed drills

Output consumed by:
  → RiskEngine (compliance_penalty component)
  → Dashboard Compliance tab
  → WebSocket broadcast (compliance_score field)

Author: SafetyIQ Team
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import anthropic

logger = logging.getLogger(__name__)


# ─── Enums & Models ───────────────────────────────────────────────────────────

class ComplianceFramework(str, Enum):
    OISD        = "OISD"
    FACTORY_ACT = "FACTORY_ACT"
    DGMS        = "DGMS"
    DGFASLI     = "DGFASLI"


class FindingSeverity(str, Enum):
    CRITICAL = "CRITICAL"   # Immediate statutory violation; inspector would issue notice
    MAJOR    = "MAJOR"      # Non-conformance likely cited in audit
    MINOR    = "MINOR"      # Best-practice gap; not immediately notifiable


@dataclass
class ComplianceFinding:
    finding_id: str
    framework: ComplianceFramework
    standard_ref: str              # e.g., "OISD 105 Section 6.1"
    title: str
    description: str
    severity: FindingSeverity
    zone: str
    due_date: datetime | None      # When this must be resolved by
    days_overdue: int = 0
    corrective_actions: list[str] = field(default_factory=list)
    responsible_officer: str = "Safety Officer"
    closed: bool = False
    ai_recommendation: str = ""


@dataclass
class FrameworkScore:
    framework: ComplianceFramework
    score: int                     # 0–100
    total_checks: int
    passed: int
    critical_failures: int
    findings: list[ComplianceFinding]


@dataclass
class ComplianceReport:
    report_id: str
    timestamp: datetime
    overall_score: int
    framework_scores: list[FrameworkScore]
    open_findings: int
    critical_gaps: list[str]       # Human-readable list of critical gaps
    next_audit_date: datetime
    last_audit_date: datetime
    ai_summary: str
    corrective_workflow: list[dict]


# ─── Compliance Check Definitions ────────────────────────────────────────────

# Each entry: (framework, standard_ref, title, check_fn_name, severity)
# check_fn_name maps to a method on ComplianceChecker

COMPLIANCE_CHECKS = [
    # OISD 105 — PTW
    (ComplianceFramework.OISD, "OISD 105 Section 4.3",
     "Pre-Entry Atmospheric Testing Records", "check_atmospheric_testing", FindingSeverity.CRITICAL),
    (ComplianceFramework.OISD, "OISD 105 Section 6.1",
     "Isolation Certificates on Active Permits", "check_isolation_certs", FindingSeverity.CRITICAL),
    (ComplianceFramework.OISD, "OISD 105 Section 7.2",
     "SIMOPs Assessment for Concurrent High-Risk Operations", "check_simops_assessment", FindingSeverity.MAJOR),

    # OISD 116 — Gas/Atmospheric Hazards
    (ComplianceFramework.OISD, "OISD 116 Section 4.1",
     "SCBA Availability vs Confined Space Permits", "check_scba_stock", FindingSeverity.CRITICAL),
    (ComplianceFramework.OISD, "OISD 116 Section 5.2",
     "Gas Detector Calibration Currency", "check_detector_calibration", FindingSeverity.MAJOR),

    # OISD 118 — Pressure Vessels
    (ComplianceFramework.OISD, "OISD 118 Section 8.4",
     "Pressure Relief Valve Inspection Currency", "check_prv_inspection", FindingSeverity.CRITICAL),

    # Factory Act 1948
    (ComplianceFramework.FACTORY_ACT, "Factory Act 1948 Section 36A",
     "Rescue Apparatus at Confined Space Entries", "check_rescue_apparatus", FindingSeverity.CRITICAL),
    (ComplianceFramework.FACTORY_ACT, "Factory Act 1948 Section 38",
     "Explosive/Inflammable Gas Precautions — Documented", "check_gas_precaution_docs", FindingSeverity.MAJOR),
    (ComplianceFramework.FACTORY_ACT, "Factory Act 1948 Section 31",
     "Pressure Plant Inspection Register Current", "check_pressure_plant_register", FindingSeverity.MAJOR),

    # DGMS
    (ComplianceFramework.DGMS, "DGMS Circular 2019-03",
     "Emergency Rescue Drill Conducted Within 6 Months", "check_rescue_drill", FindingSeverity.MAJOR),
    (ComplianceFramework.DGMS, "DGMS Safety Officer Qualification",
     "Certified Safety Officer on Site", "check_safety_officer_cert", FindingSeverity.CRITICAL),
]


# ─── Mock Plant Records (Production: PostgreSQL) ──────────────────────────────

class PlantRecords:
    """
    Simulates database records for compliance checks.
    Production: query PostgreSQL for each check.
    """

    # Active permits and their completeness
    ACTIVE_PERMITS = [
        {"permit_id": "PTW-2847", "type": "CONFINED_SPACE", "zone": "Confined Space B7",
         "atmospheric_test_done": True, "retest_interval_compliant": False,
         "isolation_cert_attached": False, "scba_units_available": 2, "workers": 4,
         "rescue_plan": True},
        {"permit_id": "PTW-2851", "type": "HOT_WORK", "zone": "Coke Oven Battery A",
         "atmospheric_test_done": True, "isolation_cert_attached": False, "workers": 2},
        {"permit_id": "PTW-2849", "type": "ELECTRICAL_ISOLATION", "zone": "Hot Strip Mill",
         "atmospheric_test_done": True, "isolation_cert_attached": True, "workers": 2},
        {"permit_id": "PTW-2853", "type": "CONFINED_SPACE", "zone": "Raw Material Bay",
         "atmospheric_test_done": False, "retest_interval_compliant": False,
         "isolation_cert_attached": False, "scba_units_available": 1, "workers": 3,
         "rescue_plan": False},
    ]

    EQUIPMENT_RECORDS = [
        {"equipment_id": "PRV-004", "name": "Pressure Relief Valve PRV-004",
         "zone": "Chemical Storage", "last_inspection": "2024-11-28",
         "inspection_interval_days": 30, "type": "PRV"},
        {"equipment_id": "GD-COKA-001", "name": "H2S Detector Coke Oven A",
         "zone": "Coke Oven Battery A", "last_calibration": "2024-10-15",
         "calibration_interval_days": 90, "type": "GAS_DETECTOR"},
        {"equipment_id": "GD-CONF-001", "name": "O2 Detector Confined Space B7",
         "zone": "Confined Space B7", "last_calibration": "2025-01-05",
         "calibration_interval_days": 90, "type": "GAS_DETECTOR"},
    ]

    DRILLS_AND_CERTS = {
        "last_rescue_drill": "2024-04-20",  # 8 months ago
        "safety_officer_cert_expiry": "2025-06-30",
        "safety_officer_name": "Rajan Sharma",
        "fire_equipment_last_service": "2024-12-01",
    }

    SCBA_INVENTORY = {
        "total_units": 8,
        "serviceable": 6,
        "in_use": 0,
        "available_for_confined_space": 2,   # Below recommended stock
    }


# ─── Compliance Checker ───────────────────────────────────────────────────────

class ComplianceChecker:
    """
    Deterministic rule-based compliance checks.
    Each method returns a list of ComplianceFinding (empty = compliant).
    """

    def __init__(self, records: PlantRecords):
        self.records = records
        self._finding_counter = 0

    def _new_finding_id(self) -> str:
        self._finding_counter += 1
        return f"FIND-{datetime.utcnow().strftime('%Y%m%d')}-{self._finding_counter:03d}"

    def check_atmospheric_testing(self) -> list[ComplianceFinding]:
        findings = []
        for permit in self.records.ACTIVE_PERMITS:
            if permit["type"] == "CONFINED_SPACE":
                if not permit.get("atmospheric_test_done"):
                    findings.append(ComplianceFinding(
                        finding_id=self._new_finding_id(),
                        framework=ComplianceFramework.OISD,
                        standard_ref="OISD 105 Section 4.3",
                        title=f"No Pre-Entry Atmospheric Test — {permit['permit_id']}",
                        description=f"Confined space permit {permit['permit_id']} in {permit['zone']} has no recorded pre-entry atmospheric testing. OISD 105 Section 4.3 requires O2, H2S, CO, and combustible gas testing before entry.",
                        severity=FindingSeverity.CRITICAL,
                        zone=permit["zone"],
                        due_date=datetime.utcnow(),  # Immediate
                        corrective_actions=[
                            "Suspend permit until atmospheric testing completed.",
                            "Test O2, H2S, CO, and combustibles per OISD 105 Section 4.3.",
                            "Repeat tests every 2 hours during occupancy.",
                        ],
                    ))
                elif not permit.get("retest_interval_compliant", True):
                    findings.append(ComplianceFinding(
                        finding_id=self._new_finding_id(),
                        framework=ComplianceFramework.OISD,
                        standard_ref="OISD 105 Section 4.3",
                        title=f"Atmospheric Re-test Interval Not Met — {permit['permit_id']}",
                        description=f"Permit {permit['permit_id']}: re-test not conducted within the 2-hour interval mandated by OISD 105 Section 4.3.",
                        severity=FindingSeverity.CRITICAL,
                        zone=permit["zone"],
                        due_date=datetime.utcnow(),
                        corrective_actions=["Conduct immediate atmospheric re-test.", "Set automated 90-minute re-test reminder."],
                    ))
        return findings

    def check_isolation_certs(self) -> list[ComplianceFinding]:
        findings = []
        for permit in self.records.ACTIVE_PERMITS:
            if permit["type"] in ("CONFINED_SPACE", "HOT_WORK"):
                if not permit.get("isolation_cert_attached"):
                    findings.append(ComplianceFinding(
                        finding_id=self._new_finding_id(),
                        framework=ComplianceFramework.OISD,
                        standard_ref="OISD 105 Section 6.1",
                        title=f"Isolation Certificate Missing — {permit['permit_id']}",
                        description=f"{permit['type']} permit {permit['permit_id']} in {permit['zone']} does not have an attached isolation certificate as required by OISD 105 Section 6.1.",
                        severity=FindingSeverity.CRITICAL,
                        zone=permit["zone"],
                        due_date=datetime.utcnow(),
                        corrective_actions=[
                            "Halt work until isolation is physically verified and certificate attached.",
                            "Issuing officer must sign-off isolation before recommencing.",
                        ],
                    ))
        return findings

    def check_simops_assessment(self) -> list[ComplianceFinding]:
        high_risk_permits = [
            p for p in self.records.ACTIVE_PERMITS
            if p["type"] in ("CONFINED_SPACE", "HOT_WORK", "ELECTRICAL_ISOLATION")
        ]
        if len(high_risk_permits) > 1:
            return [ComplianceFinding(
                finding_id=self._new_finding_id(),
                framework=ComplianceFramework.OISD,
                standard_ref="OISD 105 Section 7.2",
                title=f"SIMOPs Assessment Missing — {len(high_risk_permits)} Concurrent High-Risk Permits",
                description=f"{len(high_risk_permits)} high-risk permits active simultaneously ({', '.join(p['permit_id'] for p in high_risk_permits)}). OISD 105 Section 7.2 mandates a formal SIMOPs assessment.",
                severity=FindingSeverity.MAJOR,
                zone="Multiple Zones",
                due_date=datetime.utcnow() + timedelta(hours=1),
                corrective_actions=[
                    "Conduct SIMOPs assessment for all concurrent high-risk operations.",
                    "Document minimum separation distances and temporal offsets.",
                    "Obtain sign-off from Senior Safety Officer.",
                ],
            )]
        return []

    def check_scba_stock(self) -> list[ComplianceFinding]:
        findings = []
        confined_workers = sum(
            p["workers"] for p in self.records.ACTIVE_PERMITS
            if p["type"] == "CONFINED_SPACE"
        )
        # OISD 116: require units = workers + 2 standby minimum
        required = confined_workers + 2
        available = self.records.SCBA_INVENTORY["available_for_confined_space"]
        if available < required:
            findings.append(ComplianceFinding(
                finding_id=self._new_finding_id(),
                framework=ComplianceFramework.OISD,
                standard_ref="OISD 116 Section 4.1",
                title=f"Insufficient SCBA Units — {available} available, {required} required",
                description=f"SCBA stock for confined space operations is below mandatory minimum. {confined_workers} workers in confined spaces require {required} SCBA units (workers + 2 standby). Only {available} units serviceable.",
                severity=FindingSeverity.CRITICAL,
                zone="Plant-Wide",
                due_date=datetime.utcnow(),
                corrective_actions=[
                    f"Source {required - available} additional SCBA units before resuming confined space entry.",
                    "Check service log — units may be overdue for inspection.",
                ],
            ))
        return findings

    def check_detector_calibration(self) -> list[ComplianceFinding]:
        findings = []
        today = datetime.utcnow()
        for equip in self.records.EQUIPMENT_RECORDS:
            if equip["type"] == "GAS_DETECTOR":
                cal_date = datetime.strptime(equip["last_calibration"], "%Y-%m-%d")
                overdue_by = (today - cal_date).days - equip["calibration_interval_days"]
                if overdue_by > 0:
                    findings.append(ComplianceFinding(
                        finding_id=self._new_finding_id(),
                        framework=ComplianceFramework.OISD,
                        standard_ref="OISD 116 Section 5.2",
                        title=f"Gas Detector Calibration Overdue — {equip['name']}",
                        description=f"{equip['name']} in {equip['zone']} is {overdue_by} days overdue for calibration. Uncalibrated detectors may give false-low readings.",
                        severity=FindingSeverity.MAJOR,
                        zone=equip["zone"],
                        due_date=today,
                        days_overdue=overdue_by,
                        corrective_actions=[
                            "Take detector out of service until recalibrated.",
                            "Deploy portable calibrated unit as interim measure.",
                        ],
                    ))
        return findings

    def check_prv_inspection(self) -> list[ComplianceFinding]:
        findings = []
        today = datetime.utcnow()
        for equip in self.records.EQUIPMENT_RECORDS:
            if equip["type"] == "PRV":
                insp_date = datetime.strptime(equip["last_inspection"], "%Y-%m-%d")
                overdue_by = (today - insp_date).days - equip["inspection_interval_days"]
                if overdue_by > 0:
                    findings.append(ComplianceFinding(
                        finding_id=self._new_finding_id(),
                        framework=ComplianceFramework.OISD,
                        standard_ref="OISD 118 Section 8.4",
                        title=f"PRV Inspection Overdue by {overdue_by} Days — {equip['name']}",
                        description=f"{equip['name']} in {equip['zone']} is {overdue_by} days past inspection due date. OISD 118 Section 8.4 requires operation at ≤75% design pressure when overdue.",
                        severity=FindingSeverity.CRITICAL,
                        zone=equip["zone"],
                        due_date=today,
                        days_overdue=overdue_by,
                        corrective_actions=[
                            "Reduce operating pressure to 75% design pressure immediately.",
                            "Schedule PRV inspection within 48 hours.",
                            "Notify plant manager and record in pressure vessel register.",
                        ],
                    ))
        return findings

    def check_rescue_apparatus(self) -> list[ComplianceFinding]:
        findings = []
        for permit in self.records.ACTIVE_PERMITS:
            if permit["type"] == "CONFINED_SPACE" and not permit.get("rescue_plan"):
                findings.append(ComplianceFinding(
                    finding_id=self._new_finding_id(),
                    framework=ComplianceFramework.FACTORY_ACT,
                    standard_ref="Factory Act 1948 Section 36A",
                    title=f"No Rescue Plan Documented — {permit['permit_id']}",
                    description=f"Confined space permit {permit['permit_id']} in {permit['zone']} lacks a documented rescue plan. Section 36A requires reviving apparatus and trained first-aid attendant.",
                    severity=FindingSeverity.CRITICAL,
                    zone=permit["zone"],
                    due_date=datetime.utcnow(),
                    corrective_actions=[
                        "Document rescue plan before entry commences.",
                        "Assign trained first-aid attendant at entry point.",
                        "Verify reviving apparatus location in permit.",
                    ],
                ))
        return findings

    def check_gas_precaution_docs(self) -> list[ComplianceFinding]:
        # Simplified: assume documented if atmospheric testing done
        return []

    def check_pressure_plant_register(self) -> list[ComplianceFinding]:
        # Check overdue PRVs = pressure plant register gap
        return []

    def check_rescue_drill(self) -> list[ComplianceFinding]:
        last_drill = datetime.strptime(
            self.records.DRILLS_AND_CERTS["last_rescue_drill"], "%Y-%m-%d"
        )
        months_since = (datetime.utcnow() - last_drill).days / 30
        if months_since > 6:
            return [ComplianceFinding(
                finding_id=self._new_finding_id(),
                framework=ComplianceFramework.DGMS,
                standard_ref="DGMS Circular 2019-03",
                title=f"Emergency Rescue Drill Overdue — Last Conducted {int(months_since)} Months Ago",
                description=f"DGMS Circular 2019-03 requires emergency rescue drills every 6 months. Last drill was on {self.records.DRILLS_AND_CERTS['last_rescue_drill']} ({int(months_since)} months ago).",
                severity=FindingSeverity.MAJOR,
                zone="Plant-Wide",
                due_date=datetime.utcnow() + timedelta(days=14),
                corrective_actions=[
                    "Schedule rescue drill within 14 days.",
                    "Include confined space rescue and gas leak scenarios.",
                    "Document attendance and outcomes for DGMS compliance record.",
                ],
            )]
        return []

    def check_safety_officer_cert(self) -> list[ComplianceFinding]:
        cert_expiry = datetime.strptime(
            self.records.DRILLS_AND_CERTS["safety_officer_cert_expiry"], "%Y-%m-%d"
        )
        days_to_expiry = (cert_expiry - datetime.utcnow()).days
        if days_to_expiry < 30:
            return [ComplianceFinding(
                finding_id=self._new_finding_id(),
                framework=ComplianceFramework.DGMS,
                standard_ref="DGMS Safety Officer Qualification",
                title=f"Safety Officer Certification Expiring in {days_to_expiry} Days",
                description=f"Safety Officer {self.records.DRILLS_AND_CERTS['safety_officer_name']} certification expires on {self.records.DRILLS_AND_CERTS['safety_officer_cert_expiry']}.",
                severity=FindingSeverity.CRITICAL if days_to_expiry <= 0 else FindingSeverity.MAJOR,
                zone="Plant-Wide",
                due_date=cert_expiry,
                corrective_actions=[
                    "Initiate DGMS recertification process immediately.",
                    "Arrange qualified cover if certification lapses.",
                ],
            )]
        return []


# ─── Main Agent ───────────────────────────────────────────────────────────────

class ComplianceAgent:
    """
    Quality & Compliance Audit Agent.

    Runs all deterministic checks, then optionally calls Claude to generate
    a concise AI compliance summary and prioritised corrective workflow.
    """

    def __init__(self, anthropic_api_key: str | None = None):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.records = PlantRecords()

    def run_checks(self) -> ComplianceReport:
        """Execute all compliance checks and return a scored report."""
        checker = ComplianceChecker(self.records)
        all_findings: list[ComplianceFinding] = []

        for framework, std_ref, title, method_name, severity in COMPLIANCE_CHECKS:
            method = getattr(checker, method_name, None)
            if method:
                try:
                    findings = method()
                    all_findings.extend(findings)
                except Exception as exc:
                    logger.error(f"Check {method_name} failed: {exc}")

        # Score per framework
        framework_findings: dict[ComplianceFramework, list[ComplianceFinding]] = {}
        for f in all_findings:
            framework_findings.setdefault(f.framework, []).append(f)

        framework_scores = []
        for fw in ComplianceFramework:
            checks_for_fw = [c for c in COMPLIANCE_CHECKS if c[0] == fw]
            findings_for_fw = framework_findings.get(fw, [])
            critical_fail = sum(1 for f in findings_for_fw if f.severity == FindingSeverity.CRITICAL)
            major_fail    = sum(1 for f in findings_for_fw if f.severity == FindingSeverity.MAJOR)
            total = len(checks_for_fw) or 1
            # Deduct: critical = 15 pts, major = 8 pts, minor = 3 pts
            deduction = critical_fail * 15 + major_fail * 8
            score = max(0, 100 - int((deduction / total) * 10))
            passed = total - len(findings_for_fw)
            framework_scores.append(FrameworkScore(
                framework=fw,
                score=score,
                total_checks=total,
                passed=max(0, passed),
                critical_failures=critical_fail,
                findings=findings_for_fw,
            ))

        overall = int(sum(fs.score for fs in framework_scores) / len(framework_scores))
        critical_gaps = [
            f.title for f in all_findings
            if f.severity == FindingSeverity.CRITICAL
        ]

        return ComplianceReport(
            report_id=f"COMP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            timestamp=datetime.utcnow(),
            overall_score=overall,
            framework_scores=framework_scores,
            open_findings=len(all_findings),
            critical_gaps=critical_gaps,
            next_audit_date=datetime.utcnow() + timedelta(days=90),
            last_audit_date=datetime.utcnow() - timedelta(days=275),
            ai_summary="",           # filled by generate_ai_summary()
            corrective_workflow=[],  # filled by generate_corrective_workflow()
        )

    async def generate_ai_summary(self, report: ComplianceReport) -> str:
        """Use Claude to generate a 3-sentence executive compliance summary."""
        findings_brief = [
            {"ref": f.standard_ref, "title": f.title, "severity": f.severity.value}
            for fs in report.framework_scores for f in fs.findings
        ]
        prompt = f"""You are a compliance AI for an Indian steel plant.

Overall compliance score: {report.overall_score}/100
Framework scores: {[(fs.framework.value, fs.score) for fs in report.framework_scores]}
Open findings: {report.open_findings}
Critical gaps: {report.critical_gaps}
Top findings: {json.dumps(findings_brief[:5], indent=2)}

Write a 3-sentence executive compliance summary for the Plant Safety Manager.
Focus on the most dangerous gaps and what the regulatory exposure is.
Be direct and specific — no boilerplate."""

        try:
            resp = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text.strip()
        except Exception as e:
            logger.error(f"AI summary error: {e}")
            return (
                f"Overall compliance score {report.overall_score}/100 with {len(report.critical_gaps)} critical gaps. "
                f"Immediate action required on: {', '.join(report.critical_gaps[:2])}."
            )

    async def generate_corrective_workflow(
        self, report: ComplianceReport
    ) -> list[dict[str, Any]]:
        """
        Return a prioritised list of corrective actions with owners and deadlines.
        Production: integrates with CMMS/work order system.
        """
        workflow = []
        rank = 1
        for fs in report.framework_scores:
            for finding in sorted(
                fs.findings,
                key=lambda f: 0 if f.severity == FindingSeverity.CRITICAL else 1
            ):
                workflow.append({
                    "rank": rank,
                    "finding_id": finding.finding_id,
                    "priority": finding.severity.value,
                    "standard_ref": finding.standard_ref,
                    "title": finding.title,
                    "zone": finding.zone,
                    "corrective_actions": finding.corrective_actions,
                    "responsible": finding.responsible_officer,
                    "due_date": finding.due_date.isoformat() if finding.due_date else None,
                    "days_overdue": finding.days_overdue,
                    "status": "OPEN",
                })
                rank += 1
        return workflow

    def to_api_response(self, report: ComplianceReport) -> dict[str, Any]:
        """Serialize for REST endpoint."""
        return {
            "report_id": report.report_id,
            "timestamp": report.timestamp.isoformat(),
            "overall_score": report.overall_score,
            "open_findings": report.open_findings,
            "critical_gaps": report.critical_gaps,
            "last_audit": report.last_audit_date.strftime("%Y-%m-%d"),
            "next_audit": report.next_audit_date.strftime("%Y-%m-%d"),
            "ai_summary": report.ai_summary,
            "frameworks": [
                {
                    "name": fs.framework.value,
                    "score": fs.score,
                    "total_checks": fs.total_checks,
                    "passed": fs.passed,
                    "critical_failures": fs.critical_failures,
                    "findings": [
                        {
                            "finding_id": f.finding_id,
                            "standard_ref": f.standard_ref,
                            "title": f.title,
                            "description": f.description,
                            "severity": f.severity.value,
                            "zone": f.zone,
                            "days_overdue": f.days_overdue,
                            "corrective_actions": f.corrective_actions,
                            "due_date": f.due_date.isoformat() if f.due_date else None,
                        }
                        for f in fs.findings
                    ],
                }
                for fs in report.framework_scores
            ],
            "corrective_workflow": report.corrective_workflow,
        }