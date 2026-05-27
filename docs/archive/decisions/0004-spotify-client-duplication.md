# ADR-0004: Accept Spotify Client Duplication

**Date**: 2026-05-25  
**Status**: Accepted

## Context

Two separate `SpotifyClient` implementations exist:

| File | Repo | Focus |
|------|------|-------|
| `app/clients/spotify_client.py` | `myblog_music` | Search & discovery (`search`, `search_albums`, `get_album`, `get_album_tracks_all`) |
| `worker/clients/spotify_client.py` | `myblog_worker` | Bulk data sync (`get_albums` batch ≤20, `get_artists` batch ≤50) |

The two clients share the auth logic (`_get_token`, `_headers`) and differ meaningfully in the API surface they expose.

## Decision

Accept the duplication. Do not extract to a shared package (`myblog_shared`).

## Rationale

1. **Different primary purposes.** The music client is request-driven (search). The worker client is batch-driven (sync 20 albums at a time). Forcing one interface on both would add complexity with no benefit.

2. **Independent Lambda deployments.** Each repo builds and deploys its own zip. A shared package would require publishing (private PyPI, GitHub Packages, or git submodule) and coordinated version bumps — operational overhead for a 2-file overlap.

3. **Auth logic is stable.** The `_get_token` / `_headers` portion is ~20 lines and unlikely to change. The maintenance cost of keeping it in sync is low.

## Consequences

- **Spotify API credential or token-endpoint changes** must be applied to both files. Each file contains a comment pointing to the other.
- If the shared surface grows significantly (e.g., a third consumer emerges), revisit this decision.

## Cross-reference comment

Each `spotify_client.py` should contain:
```python
# Parallel implementation in myblog_music/app/clients/spotify_client.py
# (or myblog_worker/worker/clients/spotify_client.py).
# Auth logic (_get_token/_headers) must stay in sync. See ADR-0004.
```
