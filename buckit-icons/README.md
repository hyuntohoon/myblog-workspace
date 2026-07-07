# buckit-icons — brand app-icon source

Master source assets for the buckit **'b.'** app icon (Newsreader serif *b* in
cream `#f5f1ec` + brand-red period `#c8332b` on the `#141312` ground, matching
the masthead wordmark).

The `myblog_front/public/` icons are **exports of these** — regenerate from here
if the mark changes, then copy the exported files into `myblog_front/public/`
under their existing names (filenames are load-bearing: the Astro PWA manifest
and `layout.astro` icon links reference them directly).

| file                        | used by                                             |
| --------------------------- | --------------------------------------------------- |
| `icon-master.svg`           | vector master — edit this, re-export the rest        |
| `favicon.svg`               | → `front/public/favicon.svg`                         |
| `pwa-192x192.png`           | → `front/public/pwa-192x192.png` (also apple-touch)  |
| `pwa-512x512.png`           | → `front/public/pwa-512x512.png`                     |
| `maskable-icon-512x512.png` | → `front/public/maskable-icon-512x512.png`           |
| `apple-touch-icon.png`      | spare 180px export (front reuses pwa-192 today)      |
| `favicon-32.png`            | spare 32px raster export (front ships the SVG today) |
