# ADR 0003 — AI tools run on the phone; the gateway is a stateless relay

**Status:** accepted

**Context.** The model must read real records before answering, but breeding data lives on the
phone, and the AI component must not be able to modify records.

**Decision.** The app sends messages and tool definitions to `POST /api/v1/chat`. The gateway relays
one turn to Ollama and returns either text or `tool_calls`. The app executes the requested tools
locally (read-only, deterministic) and sends results in the next turn (max 6 rounds). The gateway
has no database connection.

Answers must label each statement (`[VERIFIED]`, `[CALCULATED]`, `[OBSERVATION]`, `[HYPOTHESIS]`,
`[RECOMMENDATION]`, `[UNKNOWN]`). Unlabelled text is shown as "unlabelled", never as fact.

Proactive interpretation uses Ollama structured output (`format` = JSON Schema) and strict validation
at three layers: gateway (drops invalid items), app (also checks evidence IDs against the context it
sent), backend `/api/v1/ai/suggestions/validate` (evidence must exist and belong to the beetle) for
anything persisted server-side.

**Consequences.** Data minimisation: only what the model asks for is sent. Latency grows with tool
rounds. Works identically for a future on-device provider.
