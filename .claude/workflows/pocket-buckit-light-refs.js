export const meta = {
  name: 'pocket-buckit-light-refs',
  description: 'Gather diverse "lighter feel" design references for the Pocket Buckit bottom tray',
  phases: [{ title: 'Reference sweep', detail: 'parallel multi-angle search for light/airy/unobtrusive design references' }],
}

const CTX = `CONTEXT — what we are designing for:
"Pocket Buckit" is a PERSISTENT, HORIZONTAL, BOTTOM tray on a music-criticism website. A user drags an album/track/review/listening-record into a row of visible "bucket" drop-targets. House style is editorial (serif headings, album art as imagery). The user wants a LIGHTER feel: airy, low-chrome, unobtrusive (doesn't fight the page), restrained motion, generous whitespace, hairline/soft borders, translucency/blur, content-first — NOT a heavy dock/toolbar.

GOAL of your search: find REAL, CURRENT references (with working URLs) that inspire a "lighter" feel. They do NOT need to be music apps or even have the same function — the user explicitly said "doesn't have to be similar function, doesn't even have to be a site." Physical/industrial/editorial design counts.

For EACH reference give: name, url, what it is, WHY it feels light (the specific device — translucency, whitespace, hairline borders, low-chrome, restraint, motion), the TRANSFERABLE LESSON for a light bottom drop-tray, and a CAUTION (what NOT to copy). Be concrete and opinionated; prefer a few excellent picks over a long shallow list. Your returned object IS data for a downstream curation, not a human message. Use WebSearch + WebFetch (load via ToolSearch "select:WebSearch,WebFetch" if needed); cite real URLs.`

const REF_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    category: { type: 'string' },
    summary: { type: 'string', description: '2-4 sentence read on what this category offers for a lighter tray' },
    references: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
      name: { type: 'string' },
      url: { type: 'string' },
      what_it_is: { type: 'string' },
      why_light: { type: 'string' },
      transferable_lesson: { type: 'string', description: 'specific to a light, unobtrusive bottom drop-tray' },
      caution: { type: 'string' },
    }, required: ['name', 'url', 'what_it_is', 'why_light', 'transferable_lesson', 'caution'] } },
  },
  required: ['category', 'summary', 'references'],
}

const CATS = [
  { key: 'light-sheet-tray-components', focus: `Lightweight bottom-sheet / drawer / command / toast COMPONENTS and their LIVE DEMOS you can literally feel — these are the most actionable. Cover at least: Vaul (emilkowalski's light bottom drawer for React), Sonner (light toast), cmdk (command menu), Radix UI / Base UI primitives, react-aria, Emil Kowalski's animation work/essays (animations.dev), and any "light bottom sheet" pattern libraries. Note demo URLs.` },
  { key: 'light-quickaccess-bars', focus: `Light, unobtrusive QUICK-ACCESS / command bars & floating layers in real products: Linear (command palette + general restraint), Arc browser (command bar / Little Arc / the way its chrome recedes), Raycast, macOS Spotlight, Superhuman, Notion Calendar (ex-Cron), Things 3 quick-entry, Height. Focus on how a persistent/summonable layer stays light and gets out of the way.` },
  { key: 'music-light-miniplayer', focus: `Music apps with a LIGHT now-playing / queue / mini-player BAR or bottom layer (domain-matched): Apple Music mini-player, Spotify's bottom bar (and what's heavy vs light about it), NTS Radio's persistent player, Bandcamp, Sonos, Plexamp, SoundCloud. What makes a persistent bottom music bar feel light vs heavy.` },
  { key: 'light-collection-board-tools', focus: `Light, content-first COLLECTION / board / save tools (bucket-adjacent but airy): Are.na (restraint, content-first, hairline UI), Cosmos, Mymind, Raindrop's light save popover, Pinterest's lighter moments, Milanote (what's light vs cluttered), Eagle. How a "drop into a collection" surface stays light.` },
  { key: 'editorial-music-airy-sites', focus: `EDITORIAL / music-criticism sites with airy, restrained, light design (house-style inspiration): NTS, Bandcamp Daily, Aeon, The Pudding, Resident Advisor, The Quietus, Pitchfork, Polygon/Verge editorial features, Kinfolk online, It's Nice That. What typographic/whitespace/imagery choices make editorial feel light.` },
  { key: 'design-galleries-systems', focus: `WHERE to keep browsing + design-SYSTEM references for "light": galleries (Mobbin, Godly, Land-book, Savee, Refactoring UI examples, Lawsofux, pageflows) and light design systems (Vercel/Geist, Linear's system, Stripe, Apple HIG materials/vibrancy, Untitled UI). Give the best 1-2 galleries to browse + 2-3 systems whose "lightness" (vibrancy/blur, hairlines, spacing scale, muted palette, restrained motion) is worth studying.` },
  { key: 'nondigital-light-language', focus: `NON-DIGITAL / physical / print design languages that embody "light/airy/restrained" (the user said it doesn't have to be a site): Dieter Rams / Braun, Muji, Teenage Engineering (light-but-playful minimalism), Swiss / International Typographic Style, Kinfolk / Cereal magazine editorial, Japanese minimalism (ma / negative space), Kenya Hara / MUJI's "emptiness". Translate each into a concrete UI cue for a light bottom tray (palette, spacing, materiality, restraint).` },
]

phase('Reference sweep')
const results = (await parallel(CATS.map(c => () => agent(
  `${CTX}\n\n=== YOUR ANGLE: ${c.key} ===\n${c.focus}`,
  { label: c.key, phase: 'Reference sweep', schema: REF_SCHEMA, effort: 'high' },
)))).filter(Boolean)
log(`Reference categories: ${results.length}/${CATS.length}`)
return { results }
