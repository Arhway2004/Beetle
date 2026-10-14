# On-device AI (llama.cpp via llamadart)

**Status: experimental.** The user downloads the model in Settings → On-device AI and switches the
provider on. Answers are tagged *Experimental* in the assistant.

## How it works
* Runtime: [`llamadart`](https://pub.dev/packages/llamadart) `0.11.x`; its build hook bundles the
  llama.cpp library. Requires Flutter ≥ 3.38 and iOS ≥ 16.4. Metal on iOS, CPU on Android.
  The SwiftPM companion `llamadart_llama_cpp_flutter` is not used: Flutter 3.38 generates its
  plugin Swift package for iOS 13, which the companion (iOS 16.4) rejects.
* Model: Qwen3 1.7B Q4_K_M GGUF (Apache-2.0, 1.107 GB) from `unsloth/Qwen3-1.7B-GGUF`, pinned to
  revision `d7f544e…` and SHA-256 `b139949c…` (`lib/infrastructure/ai/model_store.dart`).
  Downloaded on demand into Application Support (`models/`), resumable, verified once, never part
  of app backups, never bundled or committed (`*.gguf` is git-ignored).
* `LlamaDartRuntime` keeps one engine loaded (context 6144 tokens, thinking disabled) and runs one
  turn at a time; it unloads when the app goes to the background or the provider is switched off.
* `MobileLlamaProvider` offers `{chat, toolCalling, proactiveInterpretation}` with
  `experimental: true`. Tool calls are parsed by llamadart from the model's chat template; calls with
  non-JSON arguments are dropped. The app's orchestrator still runs every tool and validates evidence,
  exactly as for the Mac provider.
* Proactive interpretation ("AI 解读近况") uses the gateway's prompt (`proactive_prompt.dart`, kept
  identical to `prompts.py` by a test) and grammar-constrained output from the bundled
  `assets/schemas/ai-suggestion.v1.schema.json` (kept identical to `packages/api-contracts` by a
  test), at most 3 suggestions. Records are trimmed to the newest ones until they fit ~9 000 chars.
  The result goes through the same `CareSuggestionValidator` and evidence check as the Mac's.
* Routing: `auto` uses the Mac first and falls back to the phone; `mobile` uses only the phone.

## Still to do before calling it stable
1. Benchmark on iPhone 14 Pro Max and a mid-range Android: tokens/s, peak memory, thermal
   throttling, tool-call JSON validity rate, label compliance on a fixed question set.
2. Exclude `models/` from iCloud backup explicitly (`NSURLIsExcludedFromBackupKey`).
3. Before App Store submission: add `ios/Runner/PrivacyInfo.xcprivacy` declaring
   `NSPrivacyAccessedAPICategoryFileTimestamp` with reason `C617.1` (required because the
   hook-bundled llama.cpp framework carries no privacy manifest), or switch to the SwiftPM
   companion once Flutter honours the app's deployment target.
4. Optional Wi-Fi-only download; background download (URLSession / WorkManager).
5. Android Vulkan backend once llamadart marks it stable.
