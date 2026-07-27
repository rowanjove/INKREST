import logging
from typing import Any
import uuid

logger = logging.getLogger("novel_agent.services.cost_tracker")

class CostTracker:
    def __init__(self, orchestrator: Any):
        self.orchestrator = orchestrator

    def clear_call_logs(self) -> None:
        for client in self.orchestrator.config.llm_registry.values():
            if hasattr(client, "call_log"):
                client.call_log.clear()
        if hasattr(self.orchestrator.config.llm, "call_log"):
            self.orchestrator.config.llm.call_log.clear()

    def reset_round_token_accumulator(self) -> None:
        """Start a fresh autopilot round: drop stale call_log from failed chapters."""
        self.orchestrator._round_tokens_acc = 0
        self.clear_call_logs()

    def consume_round_tokens(self) -> int:
        used = int(getattr(self.orchestrator, "_round_tokens_acc", 0) or 0)
        self.orchestrator._round_tokens_acc = 0
        return used

    def persist_llm_cost(self, chapter_id: str) -> None:
        try:
            from novel_agent.pricing import resolve_model_prices_usd, usd_to_cny

            logs = self.orchestrator.config.get_call_log()
            round_tokens = 0
            for log in logs:
                round_tokens += int(
                    log.get("total_tokens")
                    or (log.get("prompt_tokens", 0) + log.get("completion_tokens", 0))
                    or 0
                )
            self.orchestrator._round_tokens_acc = int(getattr(self.orchestrator, "_round_tokens_acc", 0) or 0) + round_tokens
            for log in logs:
                model_name = log.get("model", "")
                prompt_tokens = log.get("prompt_tokens", 0)
                completion_tokens = log.get("completion_tokens", 0)
                in_price, out_price = resolve_model_prices_usd(model_name)
                input_cost = usd_to_cny((prompt_tokens / 1000) * in_price)
                output_cost = usd_to_cny((completion_tokens / 1000) * out_price)

                call_id = f"call_{uuid.uuid4().hex[:8]}"
                self.orchestrator.store.log_llm_cost(
                    call_id=call_id,
                    model=model_name,
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                    input_cost=input_cost,
                    output_cost=output_cost,
                    project_id=str(self.orchestrator.root_dir.name)
                )

            self.clear_call_logs()
            logger.info("Successfully persisted and cleared %d LLM cost logs for chapter %s", len(logs), chapter_id)
        except Exception as e:
            logger.warning("Failed to persist LLM cost logs: %s", e)
