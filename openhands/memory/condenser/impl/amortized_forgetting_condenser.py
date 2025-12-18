from __future__ import annotations

from openhands.core.config.condenser_config import AmortizedForgettingCondenserConfig
from openhands.events.action.agent import CondensationAction
from openhands.llm.llm_registry import LLMRegistry
from openhands.memory.condenser.condenser import (
    Condensation,
    RollingCondenser,
    TokenCounter,
    View,
)


class AmortizedForgettingCondenser(RollingCondenser):
    """A condenser that maintains a condensed history and forgets old events when it grows too large."""

    def __init__(
        self,
        max_size: int = 100,
        keep_first: int = 0,
        max_tokens: int | None = None,
        token_counter: TokenCounter | None = None,
    ):
        """Initialize the condenser.

        Args:
            max_size: Maximum size of history before forgetting.
            keep_first: Number of initial events to always keep.

        Raises:
            ValueError: If keep_first is greater than max_size, keep_first is negative, or max_size is non-positive.
        """
        if keep_first >= max_size // 2:
            raise ValueError(
                f'keep_first ({keep_first}) must be less than half of max_size ({max_size})'
            )
        if keep_first < 0:
            raise ValueError(f'keep_first ({keep_first}) cannot be negative')
        if max_size < 1:
            raise ValueError(f'max_size ({keep_first}) cannot be non-positive')

        self.max_size = max_size
        self.keep_first = keep_first
        self.max_tokens = max_tokens

        super().__init__(token_counter=token_counter)

    def get_condensation(self, view: View) -> Condensation:
        target_size = self.max_size // 2
        head = view[: self.keep_first]

        events_from_tail = target_size - len(head)
        tail = view[-events_from_tail:]

        event_ids_to_keep = {event.id for event in head + tail}
        event_ids_to_forget = {event.id for event in view} - event_ids_to_keep

        event = CondensationAction(
            forgotten_events_start_id=min(event_ids_to_forget),
            forgotten_events_end_id=max(event_ids_to_forget),
        )

        return Condensation(action=event)

    def should_condense(self, view: View) -> bool:
        if view.unhandled_condensation_request:
            return True

        if len(view) > self.max_size:
            return True

        if self.max_tokens is None:
            return False

        return self._view_token_count(view) > self.max_tokens

    @classmethod
    def from_config(
        cls,
        config: AmortizedForgettingCondenserConfig,
        llm_registry: LLMRegistry,
    ) -> AmortizedForgettingCondenser:
        token_counter: TokenCounter | None = None
        if llm_registry is not None:
            try:
                llm = llm_registry.get_active_llm()

                def _counter(texts: list[str]) -> int:
                    from openhands.core.message import Message, TextContent

                    messages = [
                        Message(role='user', content=[TextContent(text=text)])
                        for text in texts
                    ]
                    return llm.get_token_count(messages)

                token_counter = _counter
            except Exception:
                token_counter = None

        return AmortizedForgettingCondenser(
            **config.model_dump(exclude={'type'}),
            token_counter=token_counter,
        )


AmortizedForgettingCondenser.register_config(AmortizedForgettingCondenserConfig)
