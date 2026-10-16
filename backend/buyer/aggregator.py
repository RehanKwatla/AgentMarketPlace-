"""Result Aggregator combining validated outputs, explaining rejections, and tracking provenance."""
from typing import Any, Dict, List
from backend.buyer.schemas import CallStatus, ServiceCallRecord


class ResultAggregator:
    """Combines heterogeneous responses from multiple seller agents into a unified, provenanced result payload."""

    def aggregate_results(
        self,
        task_prompt: str,
        calls: List[ServiceCallRecord]
    ) -> Dict[str, Any]:
        """Aggregate outputs from all succeeded calls with field-level provenance and rejection tracking.

        Guarantees:
        - Only schema-validated outputs (CallStatus.SUCCEEDED) are aggregated into findings.
        - Rejected outputs (CallStatus.PAID_OUTPUT_REJECTED) are quarantined in rejected_outputs.
        - Failures and uncertain reconciliations are quarantined in failed_calls.
        - Deterministic field-level provenance links every finding to its producing service ID,
          call ID, schema version, timestamp, and payment reference.
        - Zero fact fabrication: missing data is reported as unfulfilled rather than hallucinated.
        """
        successful_calls = [c for c in calls if c.status == CallStatus.SUCCEEDED and c.output]
        rejected_calls = [c for c in calls if c.status == CallStatus.PAID_OUTPUT_REJECTED]
        other_failed = [
            c for c in calls
            if c.status in [CallStatus.FAILED_AND_NOT_CHARGED, CallStatus.REFUSED, CallStatus.PENDING_RECONCILIATION]
        ]

        combined: Dict[str, Any] = {
            "summary": "",
            "market_data": {},
            "web_sources": [],
            "rejected_outputs": [],
            "failed_calls": [],
            "provenance": []
        }

        # 1. Quarantine and explain rejected outputs
        for c in rejected_calls:
            category_val = c.category.value if hasattr(c.category, "value") else str(c.category)
            combined["rejected_outputs"].append({
                "service_id": c.service_id,
                "call_id": c.call_id,
                "category": category_val,
                "step_id": c.step_id,
                "status": "paid output rejected",
                "amount_paid_usdc": c.amount_paid_usdc,
                "payment_reference": c.transaction_hash or c.payment_reference,
                "schema_version": c.schema_version,
                "rejection_reason": c.error,
                "timestamp": c.created_at,
                "validation_status": c.validation_status
            })

        # 2. Record non-paid failures and reconciliations
        for c in other_failed:
            category_val = c.category.value if hasattr(c.category, "value") else str(c.category)
            combined["failed_calls"].append({
                "service_id": c.service_id,
                "call_id": c.call_id,
                "category": category_val,
                "step_id": c.step_id,
                "status": c.status.value,
                "amount_paid_usdc": c.amount_paid_usdc,
                "payment_reference": c.transaction_hash or c.payment_reference,
                "error_reason": c.error,
                "timestamp": c.created_at
            })

        # 3. Aggregate validated outputs and attach field-level provenance
        inference_summaries: List[str] = []

        # Sort successful calls deterministically by step_id or call_id
        sorted_success = sorted(successful_calls, key=lambda x: (x.step_id or 0, x.call_id))

        for c in sorted_success:
            category_val = c.category.value if hasattr(c.category, "value") else str(c.category)
            out = c.output or {}
            pay_ref = c.transaction_hash or c.payment_reference

            if category_val == "data":
                sym = out.get("symbol", "UNKNOWN")
                field_key = f"market_data.{sym}"
                combined["market_data"][sym] = {
                    "price": out.get("price"),
                    "volume_24h": out.get("volume_24h"),
                    "timestamp": out.get("timestamp")
                }
                combined["provenance"].append({
                    "target_field": field_key,
                    "service_id": c.service_id,
                    "call_id": c.call_id,
                    "step_id": c.step_id,
                    "category": category_val,
                    "schema_version": c.schema_version,
                    "timestamp": c.created_at,
                    "payment_reference": pay_ref,
                    "validation_status": c.validation_status,
                    "status": c.status.value
                })

            elif category_val == "scraping":
                source_idx = len(combined["web_sources"])
                field_key = f"web_sources[{source_idx}]"
                combined["web_sources"].append({
                    "url": out.get("url"),
                    "title": out.get("title"),
                    "content": out.get("content"),
                    "word_count": out.get("word_count")
                })
                combined["provenance"].append({
                    "target_field": field_key,
                    "service_id": c.service_id,
                    "call_id": c.call_id,
                    "step_id": c.step_id,
                    "category": category_val,
                    "schema_version": c.schema_version,
                    "timestamp": c.created_at,
                    "payment_reference": pay_ref,
                    "validation_status": c.validation_status,
                    "status": c.status.value
                })

            elif category_val == "inference":
                resp_text = out.get("response", "")
                inference_summaries.append(resp_text)
                combined["provenance"].append({
                    "target_field": "summary",
                    "service_id": c.service_id,
                    "call_id": c.call_id,
                    "step_id": c.step_id,
                    "category": category_val,
                    "schema_version": c.schema_version,
                    "timestamp": c.created_at,
                    "payment_reference": pay_ref,
                    "validation_status": c.validation_status,
                    "status": c.status.value
                })

        # 4. Construct honest, non-fabricated synthesis
        if inference_summaries:
            base_summary = "\n\n".join(inference_summaries)
        else:
            # Deterministic synthesis from accepted data without inventing facts
            summary_parts = []
            if combined["market_data"]:
                data_snippets = [
                    f"{sym}: ${d.get('price')} (24h Vol: ${d.get('volume_24h')})"
                    for sym, d in sorted(combined["market_data"].items())
                ]
                summary_parts.append(f"Market Findings: {', '.join(data_snippets)}")

            if combined["web_sources"]:
                source_snippets = [
                    f"'{w.get('title', w.get('url'))}'" for w in combined["web_sources"] if w.get("title") or w.get("url")
                ]
                summary_parts.append(f"Scraped Sources: {', '.join(source_snippets)}")

            if summary_parts:
                base_summary = f"Synthesized findings for task '{task_prompt}':\n" + "\n".join(summary_parts)
            else:
                base_summary = f"Task execution completed without successful data findings."

        # Append transparent rejection and failure disclosures to summary
        disclosures = []
        if rejected_calls:
            rej_notes = [f"{r.service_id} (schema error: {r.error})" for r in rejected_calls]
            disclosures.append(f"Output Warnings: {len(rejected_calls)} paid output(s) were rejected due to schema non-compliance: {'; '.join(rej_notes)}")

        if other_failed:
            fail_notes = [f"{f.service_id} ({f.error})" for f in other_failed]
            disclosures.append(f"Execution Failures: {len(other_failed)} call(s) failed or pending reconciliation: {'; '.join(fail_notes)}")

        if disclosures:
            combined["summary"] = f"{base_summary}\n\n[Transparent Execution Disclosures]\n" + "\n".join(disclosures)
        else:
            combined["summary"] = base_summary

        return combined
