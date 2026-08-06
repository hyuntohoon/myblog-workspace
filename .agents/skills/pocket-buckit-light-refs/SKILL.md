---
name: pocket-buckit-light-refs
description: Curate current, working design references for a lighter and more unobtrusive Pocket Buckit bottom tray. Use when researching airy bottom sheets, command bars, mini-players, collection tools, editorial systems, or non-digital design languages to inform the tray's visual direction.
---

# Pocket Buckit Light References

Gather evidence for a persistent horizontal bottom tray on a music-criticism site. The tray accepts dragged albums, tracks, reviews, and listening records into visible bucket targets. Favor editorial restraint: generous whitespace, low chrome, soft or hairline borders, translucent materials, content-first hierarchy, and restrained motion.

## Research workflow

1. Restate the design question in one sentence and preserve any user constraints.
2. Search the current web. Prefer official product pages, live demos, design-system docs, and credible editorial coverage.
3. Open every proposed URL. Exclude dead links, search-result pages, and references whose relevant behavior cannot be verified.
4. For a broad sweep, delegate independent categories to subagents in batches that respect the available concurrency limit. Give each agent only its category and the required output fields. For a narrow request, research directly.
5. Curate a few strong references per category. Quality and transferability matter more than count.
6. Synthesize the recurring devices into concrete recommendations for Pocket Buckit.

## Research angles

Use only the angles relevant to the request. For a full sweep, cover all seven.

- Light sheet and tray components: Vaul, Sonner, cmdk, Radix UI, Base UI, React Aria, and animation work such as animations.dev. Capture live demos when possible.
- Quick-access and command layers: Linear, Arc, Raycast, Spotlight, Superhuman, Notion Calendar, Things, and similarly restrained products.
- Music mini-players and queues: Apple Music, Spotify, NTS Radio, Bandcamp, Sonos, Plexamp, and SoundCloud. Contrast what feels light with what feels heavy.
- Collection and save tools: Are.na, Cosmos, Mymind, Raindrop, Pinterest, Milanote, and Eagle.
- Airy editorial and music sites: NTS, Bandcamp Daily, Aeon, The Pudding, Resident Advisor, The Quietus, Pitchfork, Kinfolk, and It's Nice That.
- Galleries and systems: Mobbin, Godly, Land-book, Savee, Page Flows, Geist, Stripe, Apple HIG materials, and similar systems.
- Non-digital languages: Braun and Dieter Rams, Muji and Kenya Hara, Teenage Engineering, Swiss typography, Kinfolk or Cereal, and Japanese ma or negative space.

Treat the names above as search seeds, not a quota. Replace stale or weak examples with better current evidence.

## Required fields

For each reference, provide:

- name
- canonical or live-demo URL
- what it is
- the specific device that makes it feel light
- a transferable lesson for the bottom drop tray
- a caution describing what not to copy

For each category, add a two-to-four sentence summary of what that angle contributes.

## Final synthesis

End with:

- the five to eight strongest references across categories
- three to six design principles stated as implementable UI decisions
- tensions or tradeoffs, especially persistence versus visual quiet and discoverability versus low chrome
- the next prototype or interaction test that would reduce uncertainty most

Use compact Markdown by default. If the caller needs downstream data, return a JSON object with a results array of category objects; each category contains category, summary, and references using the required fields above.

Do not invent visual details from memory. Distinguish direct evidence from inference, and cite each current claim with the opened source URL.
