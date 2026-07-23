"""Provider router — task-based provider selection (Sprint 17A).

`AI_PROVIDER=router` selects this provider. Instead of one backend for the whole
pipeline, each *task* picks its own: perception (vision-heavy) and adjudication
(text reasoning) can run on different providers. Selection is driven entirely by
config (`ROUTER_PERCEPTION_PROVIDER` / `ROUTER_ADJUDICATION_PROVIDER`, each falling
back to `ROUTER_DEFAULT_PROVIDER` = "anthropic"), so out of the box the router
behaves exactly like the anthropic provider.

The router keeps the `AIProvider` abstraction clean: routing happens through the
`route(task)` seam (see `AIProvider.route`). The pipeline calls
`_active_provider().route(task).send_messages(...)`, so the delegate that actually
runs is a plain provider that never learns it was selected by a router — and no
sport code is involved at any point.
"""

from __future__ import annotations

from services import config
from services.ai.provider import AIProvider, MessageContent


class RouterProvider(AIProvider):
    """Selects a delegate provider per task from config."""

    def __init__(self) -> None:
        self._delegates: dict[str, AIProvider] = {}

    def provider_name(self) -> str:
        return "router"

    def supports_vision(self) -> bool:
        return True

    def route(self, task: str | None = None) -> AIProvider:
        """Return the delegate provider configured for `task`."""
        name = config.router_provider_for(task)
        if name == "router":
            # A router cannot delegate to itself — fail loudly on misconfiguration.
            raise ValueError(
                "provider router cannot route to 'router'; set "
                f"{config.ROUTER_DEFAULT_PROVIDER_ENV} and the per-task vars to a real provider"
            )
        delegate = self._delegates.get(name)
        if delegate is None:
            # Lazy import avoids a factory<->provider import cycle at module load.
            from services.ai.factory import get_provider

            delegate = get_provider(name)
            self._delegates[name] = delegate
        return delegate

    def describe_routing(self) -> dict[str, str]:
        """Task -> delegate provider name (for diagnostics/docs/tests)."""
        return {
            task: config.router_provider_for(task)
            for task in (config.TASK_PERCEPTION, config.TASK_ADJUDICATION)
        }

    def send_messages(
        self,
        *,
        system_prompt: str,
        user_content: MessageContent,
        temperature: float,
        max_tokens: int = 1200,
        response_schema: dict | None = None,
    ) -> str:
        # Direct-use fallback: the pipeline resolves the delegate via `route(task)`
        # and calls it, so this path only runs if the router is invoked without a task.
        return self.route(None).send_messages(
            system_prompt=system_prompt,
            user_content=user_content,
            temperature=temperature,
            max_tokens=max_tokens,
            response_schema=response_schema,
        )
