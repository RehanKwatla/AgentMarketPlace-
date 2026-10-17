"""Deterministic recommendations backed only by canonical ledger evidence."""
from datetime import datetime, timezone
from enum import Enum
from statistics import median
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from backend.shared.constants import ServiceCategory, base_units_to_usdc, usdc_to_base_units
from backend.registry.service import RegistryService, registry_service
from backend.ledger.models import LedgerRepository, ledger_repo


class EvidenceStatus(str, Enum):
    VERIFIED = "VERIFIED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    NEW = "NEW"


class RecommendationRequest(BaseModel):
    task_prompt: Optional[str] = Field(default=None, max_length=4000)
    task: Optional[str] = Field(default=None, max_length=4000)
    category: Optional[ServiceCategory] = None
    required_capabilities: List[str] = Field(default_factory=list, max_length=32)
    required_tags: List[str] = Field(default_factory=list, max_length=32)
    max_budget_usdc: Optional[str] = None
    max_budget_atomic: Optional[int] = Field(default=None, ge=0)
    max_acceptable_latency_ms: Optional[int] = Field(default=None, gt=0)
    required_freshness: Optional[str] = None

    @model_validator(mode="after")
    def validate_task_and_budget(self):
        if not (self.task_prompt or self.task or self.category or self.required_capabilities or self.required_tags):
            raise ValueError("Provide a task, category, or required capability")
        if self.max_budget_usdc is not None:
            units = usdc_to_base_units(self.max_budget_usdc)
            if units < 0:
                raise ValueError("Budget must be non-negative")
            if self.max_budget_atomic is not None and units != self.max_budget_atomic:
                raise ValueError("Budget amount fields disagree")
        return self


class RecommendationEngine:
    FACTOR_WEIGHTS = {
        "capability_match": 0.25, "output_validity": 0.20, "reliability": 0.15,
        "success_rate": 0.15, "price_efficiency": 0.10, "response_time": 0.10,
        "historical_validity": 0.05,
    }
    MIN_VERIFIED_SAMPLES = 20

    def __init__(self, registry: RegistryService = registry_service, repository: LedgerRepository = ledger_repo):
        self.registry, self.repo = registry, repository

    def metrics(self, service):
        records = self.repo.list_records(service_id=service.service_id, limit=1000)
        # Only settled or outcome-bearing calls contribute. Refused preflight calls are not executions.
        outcomes = [r for r in records if str(getattr(r.status, "value", r.status)) in
                    {"paid", "paid output rejected", "failed and not charged"}]
        successful = [r for r in outcomes if str(getattr(r.status, "value", r.status)) == "paid"]
        invalid = [r for r in outcomes if str(getattr(r.status, "value", r.status)) == "paid output rejected"]
        latencies = [float(r.latency_ms) for r in outcomes if r.latency_ms and r.latency_ms > 0]
        n = len(outcomes)
        timeouts = sum(1 for r in outcomes if "timeout" in str(r.error_reason or "").lower())
        errors = sum(1 for r in outcomes if str(getattr(r.status, "value", r.status)) == "failed and not charged")
        non_timeout_errors = max(0, errors - timeouts)
        evidence = EvidenceStatus.VERIFIED if n >= self.MIN_VERIFIED_SAMPLES else (EvidenceStatus.INSUFFICIENT_DATA if n else EvidenceStatus.NEW)
        success_rate = len(successful) / n if n else None
        output_validity = len(successful) / (len(successful) + len(invalid)) if successful or invalid else None
        # Reliability is an outcome rate; it includes timeout/error failures, separately from schema validity.
        reliability = max(0.0, 1.0 - (0.6 * timeouts + 0.4 * non_timeout_errors) / n) if n else None
        category = service.category.value
        return {
            "sample_size": n,
            "observation_window": "last_1000_ledger_records",
            "evidence_status": evidence.value,
            "success_rate": success_rate,
            "success_rate_sample_size": n,
            "schema_validity_rate": output_validity,
            "schema_validity_sample_size": len(successful) + len(invalid),
            "reliability_score": reliability,
            "timeout_count": timeouts,
            "error_count": non_timeout_errors,
            "median_latency_ms": median(latencies) if latencies else None,
            "latency_p95_ms": sorted(latencies)[min(len(latencies)-1, int(0.95 * len(latencies)))] if latencies else None,
            "latency_sample_size": len(latencies),
            "historical_validity": None,
            "validity_kind": {"data": "source freshness", "scraping": "source provenance", "inference": "input provenance"}[category],
        }

    def evaluate_and_rank(self, request: RecommendationRequest) -> Dict[str, Any]:
        budget = request.max_budget_atomic
        if budget is None and request.max_budget_usdc is not None:
            budget = usdc_to_base_units(request.max_budget_usdc)
        required = request.required_capabilities + request.required_tags
        cat = request.category.value if request.category else None
        services = self.registry.list_services(category=cat, active=True, limit=100).items
        candidate_data, rejected = [], []
        for svc in services:
            perf = self.metrics(svc)
            declared = set(svc.capabilities or [])
            if svc.capability_metadata:
                declared.update(svc.capability_metadata.tags or [])
            matched = [r for r in required if r in declared or any(r.lower() in c.lower() for c in declared)]
            reasons = []
            if budget is not None and svc.price_atomic > budget:
                reasons.append(f"Price {svc.price_atomic} base units exceeds budget {budget}")
            if any(r not in matched for r in required):
                reasons.append("Missing required capability: " + ", ".join(r for r in required if r not in matched))
            if request.max_acceptable_latency_ms and svc.capability_metadata and svc.capability_metadata.sla_latency_p95_ms and svc.capability_metadata.sla_latency_p95_ms > request.max_acceptable_latency_ms:
                reasons.append("Declared latency SLA exceeds maximum")
            if request.required_freshness:
                reasons.append("Freshness requirement cannot be verified from available execution evidence")
            if reasons:
                rejected.append({"service_id": svc.service_id, "name": svc.name, "eligible": False, "rejection_reasons": reasons, "price_atomic": svc.price_atomic})
                continue
            candidate_data.append((svc, perf, matched))

        prices = [svc.price_atomic for svc, _, _ in candidate_data]
        minimum, maximum = (min(prices), max(prices)) if prices else (0, 0)
        ranked = []
        for svc, perf, matched in candidate_data:
            cap = len(matched) / len(required) if required else 0.5
            schema = perf["schema_validity_rate"]
            rel = perf["reliability_score"]
            succ = perf["success_rate"]
            latency = perf["median_latency_ms"]
            price_score = (1.0 if maximum == minimum else (maximum - svc.price_atomic) / (maximum - minimum))
            expected_p95 = svc.capability_metadata.sla_latency_p95_ms if svc.capability_metadata else None
            time_score = (max(0.0, min(1.0, 1 - (latency / request.max_acceptable_latency_ms))) if latency is not None and request.max_acceptable_latency_ms else (0.5 if expected_p95 is not None else 0.0))
            factors = {
                "capability_match": cap, "output_validity": schema if schema is not None else 0.0,
                "reliability": rel if rel is not None else 0.0, "success_rate": succ if succ is not None else 0.0,
                "price_efficiency": price_score, "response_time": time_score,
                "historical_validity": 0.0,
            }
            weighted = sum(factors[k] * self.FACTOR_WEIGHTS[k] for k in self.FACTOR_WEIGHTS)
            ranked.append({
                "service_id": svc.service_id, "name": svc.name, "category": svc.category.value,
                "eligible": True, "rank": None, "price_atomic": svc.price_atomic,
                "price_usdc": svc.price_usdc, "capabilities": svc.capabilities,
                "endpoint_url": svc.endpoint_url, "input_schema": svc.input_schema,
                "output_schema": svc.output_schema, "performance": perf,
                "factor_scores": factors, "weights": self.FACTOR_WEIGHTS,
                "weighted_score": round(weighted, 6),
                "explanation": "Scores use ledger observations where available. NEW or insufficient factors score 0; expected SLA is labelled as a planning estimate, never an observed latency.",
            })
        ranked.sort(key=lambda x: (-x["weighted_score"], -x["factor_scores"]["capability_match"], x["price_atomic"], x["service_id"]))
        for rank, item in enumerate(ranked, 1):
            item["rank"] = rank
        return {
            "task_prompt": request.task_prompt or request.task or "",
            "requirements": {"category": cat, "required_capabilities": required, "max_budget_atomic": budget,
                             "max_budget_usdc": base_units_to_usdc(budget) if budget is not None else None,
                             "max_acceptable_latency_ms": request.max_acceptable_latency_ms},
            "candidates_discovered": len(services), "hard_filters_applied": ["registry active status", "category", "capabilities/tags", "integer base-unit budget", "declared latency SLA"],
            "recommendations": ranked, "rejected_candidates": rejected,
            "top_recommendation": ranked[0] if ranked else None,
            "explanation_summary": f"Evaluated {len(services)} registry candidates; {len(ranked)} eligible and {len(rejected)} rejected. Performance fields derive from ledger records; empty history is NEW.",
        }


recommendation_engine = RecommendationEngine()
