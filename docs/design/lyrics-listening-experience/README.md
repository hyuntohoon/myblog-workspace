# Approved listening player design

Owner-approved on **2026-09-08** for [FEAT-lyrics-listening-experience](../../rfcs/FEAT-lyrics-listening-experience.md).

## Open the reference

- [Approved dark preview](player-approved.html): standalone page; open the local file in a browser.
- [Approved light preview](player-approved-light.html): same controls/layout with the existing light-theme option selected.
- [Exact approved source fragment](player-approved.fragment.html): editable source retained byte-for-byte from the conversation.

The standalone pages embed their styling and behavior. They need no application server, login,
Spotify connection or Codex host. Fonts and the pinned icon runtime load from the documented CDN
URLs embedded in the pages; fully offline icon/font availability is not guaranteed. There are no
Spotify/backend/model requests. Resize the browser to inspect the responsive design.

The fragment's default is `theme: dark`, `device: desktop`, `finish: integrated`. The conversation
host also offered mobile/theme/comparison controls; standalone readers can use the separate light
page and resize their window without that host. The alternate raised/paper treatment is a comparison,
**not the selected default**.

Source SHA-256:

```text
afd78c5de3b33ce8bc16df2e43840cb6e518f6a8fc2eb9f3da58b8b35f3c657e
```

The previews were exported with the visualize skill's `scripts/render.py` on 2026-09-08. Dark uses
the exact source. Light changes only `theme:'dark'` to `theme:'light'` in the design initializer before
export. Future edits should create a clearly dated revision and update the RFC decision record rather
than silently overwriting the approved baseline.

## What is fixed

- Full-feature expanded player, with no generic More gate for heart, modes, queue or device selection.
- Warm site-aligned surfaces, off-white/dark ink, restrained red active states and fine dividing rules.
- Integrated background as the selected treatment; consistent device, volume, queue and collapsed surfaces.
- Desktop identity/heart, central transport/seek, and direct lyrics/playback tools. Mobile reflows these into three groups.
- Visible current device name and explicit lyrics entry. Spotify heart stays beside the current song.
- Collapse remains an intentional way to regain page space; opening lyrics does not require opening the queue.

| Token | Dark | Light |
|---|---|---|
| Page/player background | `#141312` | `#f5f3ee` |
| Raised panel | `#211f1c` | `#ebe7df` |
| Main text | `#ede8e0` | `#1a1a1a` |
| Secondary text | `#aaa197` | `#6b6359` |
| Rules | `#39342e` | `#d4cec3` |
| Accent | `#df524a` | `#c8332b` |

Use the site's established tokens/fonts when integrating; these values document the visual reference,
not permission to introduce a parallel design system. The serif editorial surroundings and compact
sans-serif controls serve different reading roles. Keep actual site content/navigation intact.

## Function and compatibility contract

The [RFC preservation matrix](../../rfcs/FEAT-lyrics-listening-experience.md#1-approved-player-contract)
is normative when the prototype lacks a full production flow. Start from the actual components and
shared session; do not replace them with the prototype's local JavaScript.

- Spotify heart means saved **track**, not album save or site rating. Preserve permission recovery and failed-save rollback.
- Device selection includes discovery, current output, transfer, no-device/error/pending feedback and the existing browser fallback label.
- Preserve repeat's three states, shuffle, previous/play/next and keyboard/pointer seek.
- Keep wide-screen inline volume and narrow-screen popover. The reference's 1024px layout demonstrates the compact volume form.
- Preserve the existing full queue's reorder/remove/play, album entry, dock/float and mobile behavior.
- Preserve provider/ownership/capability gates and existing media/navigation behavior. Current main adds YouTube mapping selection and suppresses Spotify-only controls in YouTube mode; the mock's Spotify-only example does not revoke those functions.
- Apply matching styling to portaled device menus as well as the bar. Preserve focus, dismissal and feedback.
- The new mobile bar is taller than the old 112px layout. Derive actual page clearance from rendered height plus safe-area padding; inspect Pocket/queue/lyrics overlay interactions. Do not retain the old inset blindly or remove functions to force the old height.

## What the prototype simulates

Local interactions: per-example-track heart, shuffle, three-state repeat, pause/play, previous/next,
seek, volume/mute, three example devices and refresh feedback, queue row selection, collapse/expand,
and opening/closing the current-song lyrics preparation view.

Not implemented here: audio playback/clock progression, real device availability/transfer, Spotify
permissions or network recovery, persisted preferences, full queue editing/docking, YouTube mapping,
source retrieval or translation. The sample queue and album artwork are placeholders. The home shell
is context, not a redesign of the homepage. The lyrics preparation view does not mean production
must hide an available original while translation is pending.

## Implementation starting points

Within `myblog_front`:

- `src/components/member/playback/GlobalPlaybackBar.tsx`
- `src/components/member/playback/PlaybackControls.tsx`
- `src/components/member/playback/PlaybackPanel.tsx`
- `src/components/member/playback/playbackEntryActions.ts`
- `src/components/member/pocket/pocket.css`
- `src/lib/playback/session.ts`, `provider.ts` and the current lyrics host

Read current main and the component registry before editing. The initial inspected checkout was
`a8d9eef`; compatibility was later checked against available `9aea4d7`. Do not start a new branch from
the old checkout just to match this reference. Backend/member discovery and translation state are
separate RFC steps, not behavior implemented by the player mock.

## Verification record

Before approval, the reference was inspected in a real browser at 320/360, 736 and 1024px content
widths across dark/light examples. Heart, device choice, repeat, seek, volume, queue selection,
collapse/expand and direct lyrics entry changed local state. Browser error log was empty during the
final check. This is prototype verification, not proof of live Spotify behavior.

The committed standalone exports were additionally opened from this directory on 2026-09-08:
dark device selection updated the output name; light heart and direct lyrics actions updated the
page. Both exports rendered, and the browser error log was empty. The source hash, JavaScript syntax
and relative document links were also checked.

For integration, repeat the RFC's complete desktop/mobile and provider/recovery matrix against the
actual frontend, then run the frontend suite and post-deploy production smoke. No production UI has
been changed by preserving this design.
