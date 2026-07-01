# ADR 0008: Lengthen launchd poller cadence to 30 min (Neon compute quota)

- **Date**: 2026-06-26
- **Status**: accepted (live)
- **Commit**: `c0f5eec` (landed on `main` via the PR #466 squash)

## Context

Two local launchd pollers — `com.myblog.research-poller` (editorial research-note backfill) and `com.myblog.genre-heal-poller` (on-demand genre-heal from the 분석 버킷 분류하기 button) — fired every 5 min (`StartInterval=300`).

Neon's free tier **auto-suspends compute after 5 min idle**. A 5-min poll cadence keeps the compute awake ~24/7: ~720 compute-hours/month vs the ~191 free allowance → the compute quota exhausts → the **prod DB goes down** until the month rolls over.

The pollers' work (research notes, genre labels) tolerates tens-of-minutes latency; only urgent genre work uses the on-demand 분류하기 path, which is unaffected by the poller cadence itself.

## Decision

Lengthen both pollers' `StartInterval` from `300` (5 min) to `1800` (30 min). At 30 min the compute idles and suspends between fires: wakes drop from ~288/day to ~48/day each, well within the free allowance. The 30-min latency is acceptable for both workloads.

The LaunchAgent copies were updated and reloaded live on 2026-06-26; the repo source-of-truth plists (`scripts/com.myblog.research-poller.plist`, `scripts/com.myblog.genre-heal-poller.plist`) were committed to match.

## Consequences

- Prod DB compute stays within Neon's free-tier quota.
- Research-note and genre-heal latency is bounded at ~30 min (was ~5 min). Urgent genre work still has the synchronous 분류하기 path.
- The fully cloud-independent genre heal (cloud iTunes-only pass, the deferred FEAT-genre-autoheal variant) is unaffected — it remains gated on the album-ingest batch, a separate concern.

## Note

This change rode into `main` inside the PR #466 squash (titled "artist buckit contract + Step 2 plan close") rather than under its own plan.md row or RFC. It is recorded here so the decision rationale is discoverable independently of that commit message.
