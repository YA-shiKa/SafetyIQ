"""
SafetyIQ — Incident Pattern Intelligence Agent (RAG)
=====================================================
RAG-powered agent that cross-references near-miss reports, historical
incident data, and OISD/Factory Act regulatory guidance to identify
recurring patterns that manual investigations miss.
 
Pipeline:
  1. Ingest: Incident reports + regulatory corpus → vector embeddings (ChromaDB)
  2. Retrieve: Semantic search for similar past incidents given current conditions
  3. Analyze: Claude identifies patterns, root causes, and prevention gaps
  4. Prioritize: Score findings by recurrence rate and severity potential
 
Data Sources:
  - Historical incident/near-miss records (internal)
  - OISD Standards 105, 116, 118
  - Factory Act 1948 Sections 7A, 36, 36A, 38, 40
  - DGMS Circulars
  - DGFASLI Form 18 archives
 
Author: SafetyIQ Team
"""
 
from __future__ import annotations
 
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
 
import anthropic
 
logger = logging.getLogger(__name__)
 
 
# ─── Data Models ──────────────────────────────────────────────────────────────
 
@dataclass
class IncidentRecord:
    """Historical incident or near-miss report."""
    incident_id: str
    date: datetime
    plant: str
    zone: str
    incident_type: str               # FATALITY, INJURY, NEAR_MISS, DANGEROUS_OCCURRENCE
    description: str
    root_causes: list[str]
    contributing_factors: list[str]
    regulations_violated: list[str]
    corrective_actions: list[str]
    fatalities: int = 0
    injuries: int = 0
    recurrence_count: int = 0       # How many times this pattern repeated
 
 
@dataclass
class RegulatoryClause:
    """A clause from OISD/Factory Act/DGMS corpus."""
    doc_id: str
    source: str                      # "OISD_105", "FACTORY_ACT_1948", "DGMS", etc.
    section: str
    title: str
    content: str
    applies_to: list[str]            # ["CONFINED_SPACE", "HOT_WORK", etc.]
 
 
@dataclass
class PatternMatch:
    """A recurring incident pattern identified by the RAG agent."""
    pattern_id: str
    pattern_name: str
    description: str
    recurrence_count: int
    severity_potential: str          # FATAL, SERIOUS_INJURY, DANGEROUS_OCCURRENCE
    similar_incidents: list[str]     # incident_ids
    current_condition_match: float   # 0.0 - 1.0 similarity to current plant state
    regulatory_gaps: list[str]
    prevention_priorities: list[str]
    regulatory_refs: list[RegulatoryClause]
    ai_analysis: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
 
 
@dataclass
class CurrentCondition:
    """Snapshot of current plant conditions for pattern matching."""
    zone: str
    active_permit_types: list[str]
    sensor_anomalies: list[dict]     # [{"type": "H2S", "value": 18.4, "trend": "rising"}]
    maintenance_gaps: list[str]
    time_of_day: str                 # "MORNING", "AFTERNOON", "NIGHT", "SHIFT_CHANGE"
    workforce_size: int
    weather: str | None = None
 
 
# ─── Mock Vector Store (Production: ChromaDB / pgvector) ─────────────────────
 
class VectorStore:
    """
    In-memory vector store for demo. Production implementation uses ChromaDB
    with sentence-transformers embeddings or Anthropic's voyage-3 embeddings.
 
    ChromaDB production setup:
        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_or_create_collection("incidents")
    """
 
    def __init__(self):
        self._incidents: list[IncidentRecord] = self._load_seed_incidents()
        self._regulations: list[RegulatoryClause] = self._load_seed_regulations()
 
    def search_incidents(self, query: str, n_results: int = 5) -> list[IncidentRecord]:
        """
        Semantic search over incident corpus.
        Demo: keyword matching. Production: embedding similarity.
        """
        query_lower = query.lower()
        keywords = query_lower.split()
 
        scored = []
        for incident in self._incidents:
            score = sum(
                1 for kw in keywords
                if kw in incident.description.lower()
                or kw in " ".join(incident.root_causes).lower()
                or kw in " ".join(incident.contributing_factors).lower()
            )
            if score > 0:
                scored.append((score, incident))
 
        scored.sort(key=lambda x: x[0], reverse=True)
        return [inc for _, inc in scored[:n_results]]
 
    def search_regulations(self, query: str, n_results: int = 4) -> list[RegulatoryClause]:
        """Semantic search over regulatory corpus."""
        query_lower = query.lower()
        keywords = [kw for kw in query_lower.split() if len(kw) > 3]
 
        scored = []
        for reg in self._regulations:
            score = sum(
                1 for kw in keywords
                if kw in reg.content.lower() or kw in reg.title.lower()
                or any(kw in at.lower() for at in reg.applies_to)
            )
            if score > 0:
                scored.append((score, reg))
 
        scored.sort(key=lambda x: x[0], reverse=True)
        return [reg for _, reg in scored[:n_results]]
 
    def get_incident_by_id(self, incident_id: str) -> IncidentRecord | None:
        return next((i for i in self._incidents if i.incident_id == incident_id), None)
 
    def _load_seed_incidents(self) -> list[IncidentRecord]:
        """Seed data from real Indian steel/refinery incident patterns."""
        return [
            IncidentRecord(
                "INC-2025-001", datetime(2025, 1, 15), "Visakhapatnam Steel Plant", "Coke Oven Battery",
                "FATALITY",
                "Eight workers killed when entrapped gases triggered explosion in coke oven battery. Gas pressure sensor warnings existed but were not acted upon. Workers were conducting routine maintenance during abnormal process conditions.",
                root_causes=["Absence of intelligent alert correlation", "Manual handoff failure during gas pressure warning", "Inadequate pre-entry gas testing protocol"],
                contributing_factors=["Active work permit during abnormal operations", "Shift changeover 15 minutes prior", "Gas detector calibration 45 days overdue", "No confined space rescue plan"],
                regulations_violated=["OISD 105 Section 4.3 (PTW for confined space)", "Factory Act 1948 Section 36A (precautions against dangerous fumes)", "OISD 116 Section 5.2 (gas testing before entry)"],
                corrective_actions=["Automated gas-permit lockout", "Real-time cross-sensor correlation", "Mandatory pre-entry atmospheric testing"],
                fatalities=8, injuries=2, recurrence_count=3,
            ),
            IncidentRecord(
                "INC-2024-047", datetime(2024, 8, 22), "Bhilai Steel Plant", "Blast Furnace Zone",
                "NEAR_MISS",
                "Near-miss: hot work welding commenced 8 meters from area with elevated CO readings (340ppm). Worker noticed sparks near gas measurement point and halted work. Isolation barrier had not been formally confirmed in permit.",
                root_causes=["Permit issued without verifying adjacent zone sensor status", "No automated proximity check between permit zones and live sensor data"],
                contributing_factors=["Incomplete isolation verification", "Supervisor busy with shift handover", "CO sensor alarm set at 400ppm (above OISD recommended 200ppm)"],
                regulations_violated=["OISD 105 Section 6.1 (isolation verification)", "Factory Act 1948 Section 36 (precautions against fire/explosion)"],
                corrective_actions=["Real-time permit-sensor cross-check", "Lower CO alarm thresholds to OISD standard"],
                fatalities=0, injuries=0, recurrence_count=7,
            ),
            IncidentRecord(
                "INC-2024-018", datetime(2024, 3, 11), "Rourkela Steel Plant", "Chemical Storage",
                "INJURY",
                "Pressure relief valve (PRV) on acid storage tank failed during routine operations. Tank pressure had been trending upward for 6 hours. PRV was 34 days overdue for inspection. Three workers suffered chemical burns during emergency depressurization.",
                root_causes=["Overdue PRV inspection not flagged as critical risk", "No automated alert correlating sensor trend with maintenance backlog"],
                contributing_factors=["Maintenance schedule not integrated with process monitoring", "Pressure trend visible in SCADA but not correlated to inspection due date", "Weekend skeleton crew on site"],
                regulations_violated=["OISD 118 Section 8.4 (pressure vessel inspection intervals)", "Factory Act 1948 Section 31 (pressure plants)"],
                corrective_actions=["Automated maintenance-sensor correlation alerts", "Mandatory downgrade to reduced operations when inspection overdue"],
                fatalities=0, injuries=3, recurrence_count=5,
            ),
            IncidentRecord(
                "INC-2023-092", datetime(2023, 11, 5), "IISCO Steel Plant", "Confined Space",
                "FATALITY",
                "One worker asphyxiated during cleaning of gas duct. Oxygen reading at duct entry was 17.8%. Worker entered without SCBA despite oxygen deficiency reading. Permit-to-work did not explicitly mandate SCBA for O2 levels below 19.5%.",
                root_causes=["PTW did not translate oxygen reading into mandatory PPE requirement", "No automated PPE mandate trigger on O2 deficiency"],
                contributing_factors=["SCBA availability (2 units for 8 workers)", "Worker not trained on oxygen deficiency signs", "Supervisor signed off PTW without verifying O2 level against OISD standard"],
                regulations_violated=["OISD 116 Section 4.1 (breathing apparatus requirement)", "Factory Act 1948 Section 36A", "DGMS Circular 2019-03"],
                corrective_actions=["Automated SCBA mandate when O2 < 19.5%", "PTW system integration with real-time atmospheric readings"],
                fatalities=1, injuries=0, recurrence_count=4,
            ),
            IncidentRecord(
                "INC-2023-031", datetime(2023, 4, 18), "Tata Steel Jamshedpur", "Hot Strip Mill",
                "DANGEROUS_OCCURRENCE",
                "Simultaneous hot work (welding) and confined space entry permits active in adjacent zones separated by 12 meters. Flash fire occurred when welding sparks ignited vapors from confined space cleaning solvents. Full evacuation required.",
                root_causes=["No SIMOPs (Simultaneous Operations) assessment conducted", "Permit issuing officers for two operations were different safety officers with no cross-communication"],
                contributing_factors=["No centralized permit visibility system", "12-meter separation considered adequate without atmospheric testing", "Wind direction not factored into SIMOPs assessment"],
                regulations_violated=["OISD 105 Section 7.2 (simultaneous operations)", "Factory Act 1948 Section 40 (further precautions by inspectors)"],
                corrective_actions=["Centralized PTW system with automatic SIMOPs flagging", "Mandatory atmospheric testing for all adjacent zone operations"],
                fatalities=0, injuries=5, recurrence_count=6,
            ),
        ]
 
    def _load_seed_regulations(self) -> list[RegulatoryClause]:
        """Key regulatory clauses from OISD, Factory Act, DGMS."""
        return [
            RegulatoryClause("OISD105-4.3", "OISD_105", "4.3", "Permit to Work — Confined Space Entry",
                "No person shall enter a confined space without a valid permit. The permit shall specify: (a) atmospheric testing results for O2, H2S, CO, and combustibles; (b) isolation status; (c) rescue equipment location; (d) communication protocol. Atmospheric testing must be repeated every 2 hours during occupancy.",
                ["CONFINED_SPACE", "PTW"]),
            RegulatoryClause("OISD105-6.1", "OISD_105", "6.1", "Isolation Verification",
                "Before commencing any hot work, electrical, or confined space operation, the area shall be physically isolated. The issuing authority shall verify and sign off isolation. Permit shall not be issued until isolation certificate is attached.",
                ["HOT_WORK", "CONFINED_SPACE", "ELECTRICAL_ISOLATION"]),
            RegulatoryClause("OISD116-4.1", "OISD_116", "4.1", "Respiratory Protective Equipment",
                "Breathing apparatus (SCBA) is mandatory when O2 concentration is below 19.5% or H2S exceeds 10ppm or CO exceeds 200ppm. Minimum 2 standby persons must be present at entry point when SCBA is in use.",
                ["OXYGEN_DEFICIENCY", "GAS_HAZARD", "CONFINED_SPACE"]),
            RegulatoryClause("OISD105-7.2", "OISD_105", "7.2", "Simultaneous Operations (SIMOPs)",
                "A formal SIMOPs assessment must be conducted when high-risk permits (confined space, hot work, electrical isolation) are issued within 25 meters of each other. Assessment must identify hazardous interactions and establish minimum separation or temporal offset.",
                ["SIMOPS", "HOT_WORK", "CONFINED_SPACE"]),
            RegulatoryClause("FA1948-36A", "FACTORY_ACT_1948", "36A", "Precautions Against Dangerous Fumes",
                "In any factory where any operation may produce dangerous fumes, the occupier shall provide: (a) means of testing atmosphere before entry; (b) reviving apparatus; (c) trained first-aid attendant. No person shall be required to enter any chamber where dangerous fumes may be present unless wearing breathing apparatus.",
                ["GAS_HAZARD", "CONFINED_SPACE", "FUMES"]),
            RegulatoryClause("OISD118-8.4", "OISD_118", "8.4", "Pressure Vessel Inspection",
                "All pressure vessels including pressure relief valves shall be inspected at intervals not exceeding: (a) External: 12 months; (b) Internal: 24 months; (c) Hydraulic test: 60 months. Where inspection is overdue, the vessel shall be operated at reduced pressure (max 75% design) pending inspection.",
                ["PRESSURE_VESSEL", "MAINTENANCE"]),
        ]
 
 
# ─── Main Agent ───────────────────────────────────────────────────────────────
 
class IncidentPatternAgent:
    """
    RAG-powered incident pattern intelligence agent.
 
    Uses historical incident corpus + regulatory corpus to:
    1. Identify current conditions that match past incident patterns
    2. Surface recurring failures that manual investigation misses
    3. Generate prevention priorities grounded in actual incident data
    4. Provide regulatory compliance context for each pattern
    """
 
    def __init__(self, anthropic_api_key: str | None = None):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.vector_store = VectorStore()
 
    def _build_search_query(self, condition: CurrentCondition) -> str:
        """Build a semantic search query from current plant conditions."""
        parts = []
        if condition.active_permit_types:
            parts.append(" ".join(condition.active_permit_types).lower())
        if condition.sensor_anomalies:
            parts.extend(a["type"].lower() for a in condition.sensor_anomalies)
        if condition.maintenance_gaps:
            parts.extend(condition.maintenance_gaps)
        parts.append(condition.zone.lower())
        if condition.time_of_day == "SHIFT_CHANGE":
            parts.append("shift changeover handover")
        return " ".join(parts)
 
    async def analyze_patterns(
        self,
        condition: CurrentCondition,
        max_patterns: int = 3,
    ) -> list[PatternMatch]:
        """
        Main analysis: retrieve similar incidents and identify patterns.
        """
        query = self._build_search_query(condition)
        logger.info(f"Pattern search query: {query}")
 
        # Retrieve similar incidents
        similar_incidents = self.vector_store.search_incidents(query, n_results=6)
        relevant_regulations = self.vector_store.search_regulations(query, n_results=4)
 
        if not similar_incidents:
            logger.info("No similar historical incidents found.")
            return []
 
        logger.info(f"Found {len(similar_incidents)} similar incidents. Analyzing patterns with AI.")
 
        # Use Claude to identify patterns across incidents
        patterns = await self._identify_patterns_with_ai(
            condition, similar_incidents, relevant_regulations, max_patterns
        )
 
        return patterns
 
    async def _identify_patterns_with_ai(
        self,
        condition: CurrentCondition,
        incidents: list[IncidentRecord],
        regulations: list[RegulatoryClause],
        max_patterns: int,
    ) -> list[PatternMatch]:
        """
        Use Claude to identify recurring patterns across retrieved incidents
        and map them to current plant conditions.
        """
 
        incident_summaries = [
            {
                "id": inc.incident_id,
                "date": inc.date.strftime("%Y-%m-%d"),
                "plant": inc.plant,
                "type": inc.incident_type,
                "description": inc.description[:400],
                "root_causes": inc.root_causes,
                "contributing_factors": inc.contributing_factors[:3],
                "fatalities": inc.fatalities,
                "injuries": inc.injuries,
                "recurrence_count": inc.recurrence_count,
            }
            for inc in incidents
        ]
 
        reg_summaries = [
            {
                "source": reg.source,
                "section": reg.section,
                "title": reg.title,
                "key_requirement": reg.content[:250],
            }
            for reg in regulations
        ]
 
        current_summary = {
            "zone": condition.zone,
            "active_permit_types": condition.active_permit_types,
            "sensor_anomalies": condition.sensor_anomalies,
            "maintenance_gaps": condition.maintenance_gaps,
            "time_of_day": condition.time_of_day,
            "workforce_size": condition.workforce_size,
        }
 
        prompt = f"""You are an industrial safety AI analyzing incident patterns for an Indian steel plant.
 
CURRENT PLANT CONDITIONS:
{json.dumps(current_summary, indent=2)}
 
RETRIEVED SIMILAR HISTORICAL INCIDENTS:
{json.dumps(incident_summaries, indent=2)}
 
RELEVANT REGULATORY CLAUSES:
{json.dumps(reg_summaries, indent=2)}
 
Your task: Identify up to {max_patterns} recurring PATTERNS across these incidents that match the current plant conditions. Focus on systemic patterns that manual investigation misses.
 
Respond ONLY with valid JSON (no markdown) in this exact format:
{{
  "patterns": [
    {{
      "pattern_name": "Brief name of the recurring pattern",
      "description": "What this pattern is and why it keeps recurring",
      "recurrence_count": 5,
      "severity_potential": "FATAL|SERIOUS_INJURY|DANGEROUS_OCCURRENCE",
      "similar_incident_ids": ["INC-2025-001", "INC-2023-092"],
      "current_condition_match": 0.85,
      "regulatory_gaps": [
        "OISD 105 Section X.Y not being complied with: specific gap",
        "Factory Act 1948 Section XX: specific compliance failure"
      ],
      "prevention_priorities": [
        "Specific actionable prevention measure 1",
        "Specific actionable prevention measure 2",
        "Specific actionable prevention measure 3"
      ],
      "ai_analysis": "Deep analysis of why this pattern persists, the systemic organizational or technical failure it represents, and why it evades manual detection. Reference specific mechanisms from the incident data."
    }}
  ]
}}
"""
 
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
                system="You are a world-class industrial safety expert specializing in Indian heavy industry incident pattern analysis. Always respond in valid JSON only.",
            )
 
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
 
            patterns = []
            for p in data.get("patterns", [])[:max_patterns]:
                pattern_id = hashlib.md5(p["pattern_name"].encode()).hexdigest()[:8].upper()
                reg_clauses = [
                    reg for reg in regulations
                    if any(ref_text[:10] in (reg.source + " " + reg.section) for ref_text in p.get("regulatory_gaps", []))
                ]
                patterns.append(PatternMatch(
                    pattern_id=f"PAT-{pattern_id}",
                    pattern_name=p["pattern_name"],
                    description=p["description"],
                    recurrence_count=p.get("recurrence_count", len(p.get("similar_incident_ids", []))),
                    severity_potential=p.get("severity_potential", "SERIOUS_INJURY"),
                    similar_incidents=p.get("similar_incident_ids", []),
                    current_condition_match=p.get("current_condition_match", 0.7),
                    regulatory_gaps=p.get("regulatory_gaps", []),
                    prevention_priorities=p.get("prevention_priorities", []),
                    regulatory_refs=reg_clauses,
                    ai_analysis=p.get("ai_analysis", ""),
                ))
 
            return patterns
 
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Pattern analysis parse error: {e}")
            return []
        except anthropic.APIError as e:
            logger.error(f"API error in pattern analysis: {e}")
            return []
 
    def to_api_response(self, patterns: list[PatternMatch]) -> dict[str, Any]:
        """Serialize for REST API."""
        return {
            "total_patterns": len(patterns),
            "high_match_patterns": sum(1 for p in patterns if p.current_condition_match >= 0.75),
            "patterns": [
                {
                    "pattern_id": p.pattern_id,
                    "pattern_name": p.pattern_name,
                    "description": p.description,
                    "recurrence_count": p.recurrence_count,
                    "severity_potential": p.severity_potential,
                    "current_condition_match": p.current_condition_match,
                    "similar_incidents": p.similar_incidents,
                    "regulatory_gaps": p.regulatory_gaps,
                    "prevention_priorities": p.prevention_priorities,
                    "ai_analysis": p.ai_analysis,
                    "timestamp": p.timestamp.isoformat(),
                }
                for p in sorted(patterns, key=lambda x: x.current_condition_match, reverse=True)
            ],
        }
 
 
# ─── Demo ─────────────────────────────────────────────────────────────────────
 
async def demo():
    import asyncio
    condition = CurrentCondition(
        zone="Coke Oven Battery A",
        active_permit_types=["CONFINED_SPACE", "HOT_WORK"],
        sensor_anomalies=[
            {"type": "H2S", "value": 18.4, "unit": "ppm", "trend": "rising"},
            {"type": "CO", "value": 312, "unit": "ppm", "trend": "rising"},
        ],
        maintenance_gaps=["PRV-004 inspection overdue 17 days"],
        time_of_day="SHIFT_CHANGE",
        workforce_size=53,
    )
 
    agent = IncidentPatternAgent()
    patterns = await agent.analyze_patterns(condition)
 
    print(f"\n{'='*60}")
    print(f"Incident Pattern Analysis — {len(patterns)} patterns identified")
    print(f"{'='*60}\n")
    for p in patterns:
        print(f"[{p.severity_potential}] {p.pattern_name}")
        print(f"  Match: {p.current_condition_match:.0%} | Recurrences: {p.recurrence_count}")
        print(f"  Similar incidents: {', '.join(p.similar_incidents)}")
        print(f"  Top prevention: {p.prevention_priorities[0] if p.prevention_priorities else 'N/A'}")
        print()
 
 
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(demo())
 