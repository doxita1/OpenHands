from __future__ import annotations

from openhands.core.config.condenser_config import LLMSummarizingCondenserConfig
from openhands.core.message import Message, TextContent
from openhands.events.action.agent import CondensationAction
from openhands.events.observation.agent import AgentCondensationObservation
from openhands.events.serialization.event import truncate_content
from openhands.llm.llm import LLM
from openhands.llm.llm_registry import LLMRegistry
from openhands.memory.condenser.condenser import (
    Condensation,
    RollingCondenser,
    TokenCounter,
    View,
)


class LLMSummarizingCondenser(RollingCondenser):
    """A condenser that summarizes forgotten events.

    Maintains a condensed history and forgets old events when it grows too large,
    keeping a special summarization event after the prefix that summarizes all previous summarizations
    and newly forgotten events.
    """

    def __init__(
        self,
        llm: LLM,
        max_size: int = 100,
        keep_first: int = 1,
        max_event_length: int = 10_000,
        max_tokens: int | None = None,
        max_event_tokens: int | None = None,
        token_counter: TokenCounter | None = None,
    ):
        if keep_first >= max_size // 2:
            raise ValueError(
                f'keep_first ({keep_first}) must be less than half of max_size ({max_size})'
            )
        if keep_first < 0:
            raise ValueError(f'keep_first ({keep_first}) cannot be negative')
        if max_size < 1:
            raise ValueError(f'max_size ({max_size}) cannot be non-positive')

        self.max_size = max_size
        self.keep_first = keep_first
        self.max_event_length = max_event_length
        self.max_tokens = max_tokens
        self.max_event_tokens = max_event_tokens
        self.llm = llm

        if token_counter is None:

            def _counter(texts: list[str]) -> int:
                messages = [
                    Message(role='user', content=[TextContent(text=text)])
                    for text in texts
                ]
                return self.llm.get_token_count(messages)

            token_counter = _counter

        super().__init__(token_counter=token_counter)

    def _truncate(self, content: str) -> str:
        """Truncate the content to fit within the specified maximum token budget."""

        if not content:
            return content

        if self.max_event_tokens is None:
            return truncate_content(content, max_chars=self.max_event_length)

        truncated = content
        max_chars = len(content)
        attempts = 0
        while self._count_tokens(truncated) > self.max_event_tokens and max_chars > 0:
            max_chars = max(1, int(max_chars * 0.8))
            truncated = truncate_content(content, max_chars=max_chars)
            attempts += 1
            if attempts > 10:
                break

        return truncated

    def _event_text(self, event: AgentCondensationObservation | object) -> str:
        return self._truncate(str(event))

    def _event_token_count(self, event: object) -> int:
        return self._count_tokens(self._event_text(event))

    def _view_token_count(self, view: View) -> int:
        return self._count_tokens(self._event_text(event) for event in view)

    def get_condensation(self, view: View) -> Condensation:
        head = view[: self.keep_first]
        target_size = self.max_size // 2
        target_tokens = self.max_tokens // 2 if self.max_tokens else None

        summary_event = (
            view[self.keep_first]
            if isinstance(view[self.keep_first], AgentCondensationObservation)
            else AgentCondensationObservation('No events summarized')
        )
        summary_text = self._truncate(
            summary_event.message if summary_event.message else ''
        )
        summary_tokens = self._count_tokens(summary_text)

        head_tokens = self._count_tokens(self._event_text(event) for event in head)

        if target_tokens is None:
            events_from_tail = max(0, target_size - len(head) - 1)
            tail = view[-events_from_tail:] if events_from_tail > 0 else []
        else:
            available_tokens = max(0, target_tokens - head_tokens - summary_tokens)
            events = view.events
            tail: list[object] = []
            for event in reversed(events):
                if event in head or isinstance(event, AgentCondensationObservation):
                    continue
                event_tokens = self._event_token_count(event)
                if event_tokens <= available_tokens:
                    tail.append(event)
                    available_tokens -= event_tokens
                else:
                    break
            tail.reverse()

        tail_ids = {event.id for event in tail}
        head_ids = {event.id for event in head}
        summary_id = getattr(summary_event, 'id', None)

        forgotten_events = [
            event
            for event in view
            if not isinstance(event, AgentCondensationObservation)
            and event.id not in tail_ids
            and event.id not in head_ids
            and (summary_id is None or event.id != summary_id)
        ]

        if not forgotten_events:
            return Condensation(action=CondensationAction(forgotten_event_ids=[]))

        # Construct prompt for summarization
        prompt = """You are maintaining a context-aware state summary for an interactive agent.
You will be given a list of events corresponding to actions taken by the agent, and the most recent previous summary if one exists.
If the events being summarized contain ANY task-tracking, you MUST include a TASK_TRACKING section to maintain continuity.
When referencing tasks make sure to preserve exact task IDs and statuses.

Track:

USER_CONTEXT: (Preserve essential user requirements, goals, and clarifications in concise form)

TASK_TRACKING: {Active tasks, their IDs and statuses - PRESERVE TASK IDs}

COMPLETED: (Tasks completed so far, with brief results)
PENDING: (Tasks that still need to be done)
CURRENT_STATE: (Current variables, data structures, or relevant state)

For code-specific tasks, also include:
CODE_STATE: {File paths, function signatures, data structures}
TESTS: {Failing cases, error messages, outputs}
CHANGES: {Code edits, variable updates}
DEPS: {Dependencies, imports, external calls}
VERSION_CONTROL_STATUS: {Repository state, current branch, PR status, commit history}

PRIORITIZE:
1. Adapt tracking format to match the actual task type
2. Capture key user requirements and goals
3. Distinguish between completed and pending tasks
4. Keep all sections concise and relevant

SKIP: Tracking irrelevant details for the current task type

Example formats:

For code tasks:
USER_CONTEXT: Fix FITS card float representation issue
COMPLETED: Modified mod_float() in card.py, all tests passing
PENDING: Create PR, update documentation
CODE_STATE: mod_float() in card.py updated
TESTS: test_format() passed
CHANGES: str(val) replaces f"{val:.16G}"
DEPS: None modified
VERSION_CONTROL_STATUS: Branch: fix-float-precision, Latest commit: a1b2c3d

For other tasks:
USER_CONTEXT: Write 20 haikus based on coin flip results
COMPLETED: 15 haikus written for results [T,H,T,H,T,H,T,T,H,T,H,T,H,T,H]
PENDING: 5 more haikus needed
CURRENT_STATE: Last flip: Heads, Haiku count: 15/20"""

        prompt += '\n\n'

        prompt += f'<PREVIOUS SUMMARY>\n{summary_text}\n</PREVIOUS SUMMARY>\n'

        prompt += '\n\n'

        # Add all events that are being forgotten. We use the string
        # representation defined by the event, and truncate it if necessary.
        for forgotten_event in forgotten_events:
            event_content = self._event_text(forgotten_event)
            prompt += f'<EVENT id={forgotten_event.id}>\n{event_content}\n</EVENT>\n'

        prompt += 'Now summarize the events using the rules above.'

        messages = [Message(role='user', content=[TextContent(text=prompt)])]

        response = self.llm.completion(
            messages=self.llm.format_messages_for_llm(messages),
            extra_body={'metadata': self.llm_metadata},
        )
        summary = response.choices[0].message.content

        self.add_metadata('response', response.model_dump())
        self.add_metadata('metrics', self.llm.metrics.get())

        return Condensation(
            action=CondensationAction(
                forgotten_events_start_id=min(event.id for event in forgotten_events),
                forgotten_events_end_id=max(event.id for event in forgotten_events),
                summary=summary,
                summary_offset=self.keep_first,
            )
        )

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
        cls, config: LLMSummarizingCondenserConfig, llm_registry: LLMRegistry
    ) -> LLMSummarizingCondenser:
        # This condenser cannot take advantage of prompt caching. If it happens
        # to be set, we'll pay for the cache writes but never get a chance to
        # save on a read.
        llm_config = config.llm_config.model_copy()
        llm_config.caching_prompt = False
        llm = llm_registry.get_llm('condenser', llm_config)

        return LLMSummarizingCondenser(
            llm=llm,
            max_size=config.max_size,
            keep_first=config.keep_first,
            max_event_length=config.max_event_length,
            max_tokens=config.max_tokens,
            max_event_tokens=config.max_event_tokens,
        )


LLMSummarizingCondenser.register_config(LLMSummarizingCondenserConfig)
