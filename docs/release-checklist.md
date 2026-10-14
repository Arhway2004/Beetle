# Release checklist

## Before tagging
- [ ] `make test` and `make lint` pass locally; all CI workflows green.
- [ ] `flutter analyze` clean; generated code up to date (`make mobile-gen` → no diff).
- [ ] Version bumped in `apps/mobile/pubspec.yaml` (`x.y.z+build`).
- [ ] If the Drift schema changed: `schemaVersion` bumped, `onUpgrade` step added,
      `make mobile-schema` run, generated migration tests pass, upgrade tested from the previous release on a device with real data.
- [ ] If server schema changed: new `V00N__*.sql` only; `migrate.py --check` passes on staging.
- [ ] Backup from the previous release restores into the new build.
- [ ] Contracts changed? `packages/shared-types/generate.sh` run; both OpenAPI contract tests pass.

## Device verification
- [ ] Fresh install → zh UI, empty states, add beetle, add each record type, photos, charts.
- [ ] Airplane mode: everything except AI works; AI shows the "no model" message.
- [ ] Reminder: accept a suggestion → permission prompt → notification fires with app closed; reboot (Android) still fires.
- [ ] Time-zone change → reminders still fire at the same instant; displayed times update.
- [ ] Mac AI (if used): HTTPS with pinned fingerprint, wrong token rejected, consent prompt, answers labelled with evidence.
- [ ] Backup export → restore on a second device; re-import reports "already restored".

## Android
- [ ] `android/key.properties` with the upload keystore (never committed).
- [ ] `flutter build appbundle --release` (Play) or `flutter build apk --release` (sideload).
- [ ] Test on Android 13+ (notification permission) and 12 (exact alarms).

## iOS
- [ ] Team + bundle id set in Xcode; capabilities unchanged.
- [ ] `flutter build ipa --release`; install via TestFlight on iPhone 14 Pro Max.
- [ ] Permission strings (camera, photos, local network) reviewed in all languages.
