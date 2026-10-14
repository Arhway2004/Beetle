# Known limitations

| Area | Limitation |
|---|---|
| On-device AI | llama.cpp is **not integrated**; the provider reports "unavailable". See [architecture/mobile-ai.md](architecture/mobile-ai.md). |
| Vision AI | No multimodal model; `UnavailableVisionProvider` only. Photos are stored but never analyzed. |
| Mac AI quality | Tool-calling and label compliance of Qwen3-8B were **not evaluated** here: no model was downloaded in this environment. The gateway was tested against a mocked Ollama and smoke-tested against a real Ollama without a model (503 path). |
| Sync | Designed (ADR 0004), not implemented. The API is not used by the app yet. |
| API auth | The backend API has no authentication yet; keep it bound to localhost (compose does). |
| Sensors | Bluetooth / Wi-Fi sensors are modelled (`kind`, `external_id`) but no hardware integration exists. |
| Notifications | iOS allows 64 pending notifications; the app keeps the soonest 60 and schedules the rest when the app is next opened. Android without exact-alarm permission may deliver a few minutes late. Force-stopping the app on some Android OEMs cancels alarms until next launch. |
| Photo backup | Large photo libraries make large ZIPs (held in memory during export/restore). |
| Biology | No species defaults for temperature, substrate, container size or pupal duration are shipped — the keeper configures them. Rule thresholds are generic defaults (10 % weight change, 30-day gap). |
| Localization | Thai and English strings were written without native-speaker review. |
| Admin web | `apps/admin` is a placeholder. |
| Drift migration tests | Only schema v1 exists; step-by-step upgrade tests are generated when v2 is introduced. |
| Release signing | Android uses the debug key unless `android/key.properties` exists; iOS needs an Apple Developer team. |
