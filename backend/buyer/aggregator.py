"""Result Aggregator combining validated seller outputs with strict provenance."""
from typing import Any, Dict, List
from backend.buyer.schemas import CallStatus, ServiceCallRecord


class ResultAggregator:
    """Aggregates multi-service outputs into a structured final response with provenance."""

    def aggregate(
        self,
        task_prompt: str,
        calls: List[ServiceCallRecord]
    ) -> Dict[str, Any]:
        """Aggregate output payloads with source provenance."""
        accepted_calls = [c for c in calls if c.status == CallStatus.SUCCEEDED and c.output]

        extracted_data = {}
        scraped_content = []
        inference_synthesis = []
        sources = []

        for c in accepted_calls:
            out = c.output or {}
            sources.append({
                "service_id": c.service_id,
                "category": c.category.value,
                "call_id": c.call_id
            })

            if c.category.value == "data":
                extracted_data[out.get("symbol", "ASSET")] = {
                    "price": out.get("price"),
                    "volume_24h": out.get("volume_24h"),
                    "timestamp": out.get("timestamp")
                }
            elif c.category.value == "scraping":
                scraped_content.append({
                    "url": out.get("url"),
                    "title": out.get("title"),
                    "content": out.get("content")
                })
            elif c.category.value == "inference":
                inference_synthesis.append(out.get("response", ""))

        # Synthesize overview
        summary_parts = []
        if inference_synthesis:
            summary_parts.extend(inference_synthesis)
        if extracted_data:
            data_strs = [f"{sym}: ${d.get('price')} (24h Vol: ${d.get('volume_24h')})" for sym, d in extracted_data.items()]
            summary_parts.append(f"Market Data: {'; '.join(data_strs)}")
        if scraped_content:
            titles = [s.get("title", s.get("url", "")) for s in scraped_content]
            summary_parts.append(f"Scraped Web Sources: {', '.join(titles)}")

        combined_summary = "\n\n".join(summary_parts) if summary_parts else "No validated outputs available."

        return {
            "summary": combined_summary,
            "market_data": extracted_data,
            "web_sources": scraped_content,
            "provenance": sources,
            "total_services_executed": len(accepted_calls)
        }
