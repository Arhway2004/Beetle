# ADR 0001 — Single monorepo with independent components

**Status:** accepted

**Context.** Frontend, backend, database and AI evolve together (shared contracts, shared test
vectors) but have different toolchains (Flutter, Python/uv, SQL).

**Decision.** One Git repository, no submodules. Each component (`apps/mobile`, `services/api`,
`services/ai-gateway`, `database`, `packages/*`) has its own dependencies, lockfile, tests, config
and README, and can be built from its own directory. Cross-component coupling is limited to
`packages/` (contracts, generated types) and is explicit (uv path dependency, fixture paths).
CI runs one workflow per component with `paths:` filters so unrelated changes do not rebuild it.

**Consequences.** Contract changes are atomic across components. Contributors need Flutter and uv.
