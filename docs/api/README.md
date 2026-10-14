# API documentation

| Service | Contract | Base URL | Auth |
|---|---|---|---|
| Backend API | [`api.v1.yaml`](../../packages/api-contracts/openapi/api.v1.yaml) | `http://localhost:8000/api/v1` | none yet (bind to localhost / private network; auth arrives with sync) |
| Mac AI gateway | [`ai-gateway.v1.yaml`](../../packages/api-contracts/openapi/ai-gateway.v1.yaml) | `https://<mac>:8443/api/v1` | `Authorization: Bearer <GATEWAY_TOKEN>` |

Shared schema: [`ai-suggestion.v1.schema.json`](../../packages/api-contracts/schemas/ai-suggestion.v1.schema.json).

Versioning: paths are prefixed `/api/v1`. Additive changes (new optional fields, new endpoints) stay
in v1; removals or semantic changes require `/api/v2`. Both services have a test that fails if their
routes diverge from the contract.

## Chat tool loop (gateway)
```
app → POST /chat {messages, tools}
    ← {message: {content: "", tool_calls: [{id, name: "get_growth_metrics", arguments: {beetle_id: "CCK-001"}}]}}
app runs the tool locally, appends {role: "tool", tool_name, content: <json>}
app → POST /chat {messages + tool result, tools}
    ← {message: {content: "[CALCULATED] …\n[HYPOTHESIS] …", tool_calls: []}}
```
Tools (all read-only except a draft that stores nothing): `list_beetles`, `get_beetle_profile`,
`get_weight_history`, `get_growth_metrics`, `compare_growth`, `get_temperature_history`,
`get_substrate_changes`, `get_container_changes`, `get_observations`, `get_life_stage_events`,
`propose_reminder_draft`.
