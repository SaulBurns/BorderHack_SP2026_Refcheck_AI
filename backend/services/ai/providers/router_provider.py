"""Provider router — per-agent provider AND model selection (Sprint 17A + 17B).

`AI_PROVIDER=router` selects this provider. Instead of one backend for the whole
pipeline, each *task* picks its own provider **and** model: perception
(vision-heavy) and adjudication (text reasoning) can run on different providers
and different models. Selection is driven entirely by config —

    perception   -> PERCEPTION_PROVIDER  + PERCEPTION_MODEL
    adjudication -> ADJUDICATOR_PROVIDER + ADJUDICATOR_MODEL

(the legacy Sprint 17A `ROUTER_*` provider vars still work). A provider falls back
to `ROUTER_DEFAULT_PROVIDER` = "anthropic"; a model left unset lets the resolved
provider pick its own — so out of the box the router behaves exactly like the
anthropic provider.

The router keeps the `AIProvider` abstraction clean: routing happens through the
`route(task)` seam (see `AIProvider.route`). The pipeline calls
`_active_provider().route(task).send_messages(...)`, so the object that actually
runs is a plain provider (or a thin model-bound wrapper around one) that never
learns it was selected by a router — and no sport code is involved at any point.
"""

from __future__ import annotations

from services import config
from services.ai.provider import AIProvider, MessageContent


class _ModelBoundProvider(AIProvider):
    """A delegate provider pinned to one model for a task (Sprint 17B).

    Transparent wrapper: it forwards `send_messages` to the delegate with the
    task's model injected, and reports the delegate's real `provider_name`/`is_mock`
    so reliability diagnostics still name the concrete provider (never "router").
    Only `model_name` is overridden — to the pinned model — so health/diagnostics
    report the model that will actually run.
    """

    def __init__(self, delegate: AIProvider, model: str) -> None:
        self._delegate = delegate
        self._model = model

    def provider_name(self) -> str:
        return self._delegate.provider_name()

    def model_name(self) -> str:
        return self._model

    def supports_vision(self) -> bool:
        return self._delegate.supports_vision()

    @property
    def is_mock(self) -> bool:
        return self._delegate.is_mock

    def send_messages(
        self,
        *,
        system_prompt: str,
        user_content: MessageContent,
        temperature: float,
        max_tokens: int = 1200,
        response_schema: dict | None = None,
        model: str | None = None,
    ) -> str:
        # The pinned model wins over whatever a caller passes (it already reflects
        # this task's configuration).
        return self._delegate.send_messages(
            system_prompt=system_prompt,
            user_content=user_content,
            temperature=temperature,
            max_tokens=max_tokens,
            response_schema=response_schema,
            model=self._model,
        )


class RouterProvider(AIProvider):
    """Selects a delegate provider (and optional model) per task from config."""

    def __init__(self) -> None:
        self._delegates: dict[str, AIProvider] = {}

    def provider_name(self) -> str:
        return "router"

    def supports_vision(self) -> bool:
        return True

    def _delegate_for(self, task: str | None) -> AIProvider:
        """Resolve (and cache) the concrete provider configured for `task`."""
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

    def route(self, task: str | None = None) -> AIProvider:
        """Return the provider (delegate, optionally model-bound) for `task`.

        When a per-task model is configured (Sprint 17B) the delegate is wrapped so
        the task's model is injected into every call; otherwise the bare delegate is
        returned — byte-for-byte the Sprint 17A behavior.
        """
        delegate = self._delegate_for(task)
        model = config.router_model_for(task)
        if model is None:
            return delegate
        return _ModelBoundProvider(delegate, model)

    def describe_routing(self) -> dict[str, dict[str, str | None]]:
        """Task -> {provider, model} it routes to (for diagnostics/docs/tests)."""
        return {
            task: {
                "provider": config.router_provider_for(task),
                "model": config.router_model_for(task),
            }
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
        model: str | None = None,
    ) -> str:
        # Direct-use fallback: the pipeline resolves the delegate via `route(task)`
        # and calls it, so this path only runs if the router is invoked without a task.
        return self.route(None).send_messages(
            system_prompt=system_prompt,
            user_content=user_content,
            temperature=temperature,
            max_tokens=max_tokens,
            response_schema=response_schema,
            model=model,
        )
