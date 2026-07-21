"""
SafetyIQ — Centralized Configuration
======================================
All environment variables and application settings in one place.
Uses pydantic-settings so every value can be overridden via .env or
environment variable without changing code.

Usage:
    from backend.core.config import settings

    settings.anthropic_api_key   # str
    settings.cors_origins         # list[str]
    settings.ws_broadcast_interval_seconds  # float

Production deployment:
    Set variables in your cloud secret manager (AWS SSM, GCP Secret Manager, etc.)
    or mount a .env file at project root.

Author: SafetyIQ Team
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Project root (two levels up from this file: backend/core/config.py → SafetyIQ/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """
    Application settings loaded from environment / .env file.
    All fields have sensible defaults for local development.
    """

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",          # Ignore unknown env vars
    )

    # ── Anthropic ──────────────────────────────────────────────────────────────
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key. Required for all AI agent features.",
    )
    anthropic_model: str = Field(
        default="claude-sonnet-4-6",
        description="Claude model used by all agents.",
    )
    anthropic_max_tokens: int = Field(
        default=1500,
        description="Default max_tokens for agent API calls.",
    )

    # ── Database ───────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql://safetyiq:safetyiq@localhost:5432/safetyiq",
        description="PostgreSQL connection string.",
    )
    database_pool_size: int = Field(default=10)
    database_max_overflow: int = Field(default=20)

    # ── Redis ──────────────────────────────────────────────────────────────────
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string for real-time state and pub/sub.",
    )
    redis_sensor_ttl_seconds: int = Field(
        default=300,
        description="How long sensor readings are cached in Redis before expiry.",
    )

    # ── MQTT ──────────────────────────────────────────────────────────────────
    mqtt_broker_host: str = Field(default="localhost")
    mqtt_broker_port: int = Field(default=1883)
    mqtt_username: str = Field(default="")
    mqtt_password: str = Field(default="")
    mqtt_sensor_topic_prefix: str = Field(
        default="safetyiq/plant/sensors",
        description="Base MQTT topic. Sensors publish to {prefix}/{zone}/{sensor_id}.",
    )

    # ── ChromaDB (RAG Vector Store) ────────────────────────────────────────────
    chroma_persist_dir: str = Field(
        default=str(_PROJECT_ROOT / "data" / "chroma_db"),
        description="Directory where ChromaDB persists embeddings.",
    )
    chroma_collection_incidents: str = Field(default="incidents")
    chroma_collection_regulations: str = Field(default="regulations")
    embedding_model: str = Field(
        default="voyage-3",
        description="Embedding model for RAG vector store (Anthropic voyage-3 recommended).",
    )

    # ── API Server ─────────────────────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_reload: bool = Field(default=True, description="uvicorn --reload flag.")
    api_workers: int = Field(
        default=1,
        description="Number of uvicorn workers. Use 1 with WebSocket in dev.",
    )
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="Allowed CORS origins for the React frontend.",
    )

    # ── WebSocket ──────────────────────────────────────────────────────────────
    ws_broadcast_interval_seconds: float = Field(
        default=2.0,
        description="How often the live sensor broadcast fires.",
    )
    ws_ping_interval_seconds: float = Field(
        default=20.0,
        description="Server-side WebSocket keepalive interval.",
    )

    # ── Risk Engine ────────────────────────────────────────────────────────────
    risk_compound_analysis_interval_seconds: float = Field(
        default=30.0,
        description="How often CompoundRiskAgent re-analyzes the full plant state.",
    )
    risk_critical_score_threshold: int = Field(
        default=91,
        description="Plant risk score above which status becomes CRITICAL.",
    )
    risk_danger_score_threshold: int = Field(default=76)
    risk_elevated_score_threshold: int = Field(default=56)
    risk_caution_score_threshold: int = Field(default=31)

    # ── Compliance ─────────────────────────────────────────────────────────────
    compliance_check_interval_minutes: int = Field(
        default=15,
        description="How often ComplianceAgent re-runs all checks.",
    )
    compliance_audit_alert_days_ahead: int = Field(
        default=30,
        description="Warn about upcoming audits this many days in advance.",
    )

    # ── Plant Config ───────────────────────────────────────────────────────────
    plant_name: str = Field(default="Visakhapatnam Steel Complex")
    plant_address: str = Field(
        default="Steel Plant Road, Ukkunagaram, Visakhapatnam, Andhra Pradesh 530031"
    )
    plant_dgfasli_reg_number: str = Field(default="AP/VSP/2024/001")
    plant_factory_licence_number: str = Field(default="APFACT/2024/VSP/0042")

    # ── Emergency Contacts ─────────────────────────────────────────────────────
    emergency_safety_officer_phones: list[str] = Field(
        default=["+91-891-2518000"]
    )
    emergency_fire_station_phones: list[str] = Field(
        default=["+91-891-2752000"]
    )
    emergency_hospital_phones: list[str] = Field(
        default=["+91-891-2744000"]
    )
    emergency_dgfasli_email: str = Field(default="dgfasli-hq@nic.in")
    emergency_notification_emails: list[str] = Field(
        default=["safety@plant.com", "gm@plant.com"]
    )

    # ── Feature Flags ──────────────────────────────────────────────────────────
    feature_cctv_analytics: bool = Field(
        default=False,
        description="Enable computer vision CCTV pipeline (requires GPU).",
    )
    feature_mqtt_ingestion: bool = Field(
        default=False,
        description="Enable live MQTT sensor ingestion (False = use simulator).",
    )
    feature_ai_permit_validation: bool = Field(
        default=True,
        description="Use Claude for permit validation AI layer.",
    )
    feature_emergency_sms: bool = Field(
        default=False,
        description="Enable real SMS notifications on emergency trigger.",
    )
    demo_mode: bool = Field(
        default=True,
        description="Use simulated sensor data instead of live SCADA/MQTT feeds.",
    )

    # ── Logging ────────────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")
    log_format: str = Field(
        default="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    # ── Validators ─────────────────────────────────────────────────────────────

    @field_validator("anthropic_api_key")
    @classmethod
    def warn_missing_api_key(cls, v: str) -> str:
        if not v:
            logger.warning(
                "ANTHROPIC_API_KEY is not set. AI agent features will be unavailable. "
                "Set it in your .env file or as an environment variable."
            )
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level must be one of {valid}, got '{v}'")
        return upper

    @field_validator("ws_broadcast_interval_seconds")
    @classmethod
    def validate_broadcast_interval(cls, v: float) -> float:
        if v < 0.5:
            raise ValueError("ws_broadcast_interval_seconds must be >= 0.5 to avoid overloading clients")
        return v

    @model_validator(mode="after")
    def configure_logging(self) -> "Settings":
        logging.basicConfig(level=self.log_level, format=self.log_format)
        return self

    # ── Computed properties ────────────────────────────────────────────────────

    @property
    def is_ai_enabled(self) -> bool:
        """True if the Anthropic API key is configured."""
        return bool(self.anthropic_api_key)

    @property
    def anthropic_client_kwargs(self) -> dict[str, Any]:
        """Kwargs to pass directly to anthropic.Anthropic()."""
        return {"api_key": self.anthropic_api_key} if self.anthropic_api_key else {}

    @property
    def chroma_persist_path(self) -> Path:
        path = Path(self.chroma_persist_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def as_safe_dict(self) -> dict[str, Any]:
        """
        Return settings as dict with sensitive values masked.
        Safe to log or expose via a /api/v1/config/debug endpoint.
        """
        d = self.model_dump()
        sensitive = {
            "anthropic_api_key", "database_url", "redis_url",
            "mqtt_password", "mqtt_username",
        }
        for key in sensitive:
            if d.get(key):
                d[key] = "***"
        return d


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the singleton Settings instance.
    Cached after first call — safe to call anywhere without performance cost.

    Example:
        from backend.core.config import get_settings
        settings = get_settings()
    """
    s = Settings()
    logger.info(
        f"SafetyIQ settings loaded | plant={s.plant_name} | "
        f"demo_mode={s.demo_mode} | ai_enabled={s.is_ai_enabled}"
    )
    return s


# Convenience singleton for direct import
settings = get_settings()