"""Result Aggregator combining validated outputs and provenance."""
from typing import Any, Dict, List
from backend.buyer.schemas import CallStatus, ServiceCallRecord


class ResultAggregator:
    """Combines heterogeneous responses from multiple seller agents into unified result payload."""

    def aggregate_results(
        self,
        task_prompt: str,
        calls: List[ServiceCallRecord]
    ) -> Dict[str, Any]:
        """Aggregate outputs from all succeeded calls with provenance tracking."""
        successful_calls = [c for c in calls if c.status == CallStatus.SUCCEEDED and c.output]

        combined: Dict[str, Any] = {
            "summary": "",
            "market_data": {},
            "web_sources": [],
            "provenance": []
        }

        inference_summaries: List[str] = []

        for c in successful_calls:
            category_val = c.category.value if hasattr(c.category, "value") else str(c.category)
            out = c.output or {}

            combined["provenance"].append({
                "service_id": c.service_id,
                "category": category_val,
                "call_id": c.call_id
            })

            if category_val == "data":
                sym = out.get("symbol", "UNKNOWN")
                combined["market_data"][sym] = {
                    "price": out.get("price"),
                    "volume_24h": out.get("volume_24h"),
                    "timestamp": out.get("timestamp")
                }
            elif category_val == "scraping":
                combined["web_sources"].append({
                    "url": out.get("url"),
                    "title": out.get("title"),
                    "content": out.get("content")
                })
            elif category_val == "inference":
                inference_summaries.append(out.get("response", ""))

        if inference_summaries:
            combined["summary"] = "\n\n".join(inference_summaries)
        else:
            # Fallback synthesis summary if inference call was omitted
            data_parts = []
            if combined["market_data"]:
                for s, d in combined["market_data"].items():
                    data_parts.append(f"{s}: ${d.get('price')} (24h Vol: ${d.get('volume_24h')})")
            sources_parts = [w.get("title", w.get("url")) for w in combined["web_sources"] if w]

            summary_lines = [f"Synthesized task execution for: '{task_prompt}'"]
            if data_parts:
                summary_lines.append(f"Market Data: {', '.join(data_parts)}")
            if sources_parts:
                summary_lines.append(f"Scraped Sources: {', '.join(sources_parts)}")

            combined["summary"] = "\n".join(summary_lines)

        return combined
