// FIX-bug-audit-2026-07 WS-F: security response headers.
// CloudFront Free plan rejects a custom response_headers_policy (Business-tier),
// so the headers are stamped by this viewer-response Function instead (runs on
// every response of the associated behavior — default S3 behavior only; /api/*
// responses come from the backend and are not in scope here).
//
// CSP is ENFORCING (promoted from Report-Only 2026-07-07, owner-approved):
// shipped Report-Only in ws #557; zero violations in the ship-time authed
// Playwright sweep (home/reviews/detail/search/profile+SDK/write) and a
// pre-promotion public-page re-sweep. Rollback = rename the header back to
// content-security-policy-report-only and re-apply.
// Allowlist sources (verified against myblog_front/src 2026-07-07):
//   script/frame  sdk.scdn.co + *.spotify.com  (Spotify Web Playback SDK + EME iframe)
//   connect       *.spotify.com (Web API), *.amazoncognito.com (token endpoint),
//                 *.scdn.co / *.spotifycdn.com (cover CDNs — the service worker
//                 revalidates cover <img>s via fetch(), which CSP governs as
//                 connect-src, NOT img-src; omitting them net::ERR_FAILEDs every
//                 SW-cached cover, see FIX-csp-connect-src-cover-cdn)
//   style/font    fonts.googleapis.com / fonts.gstatic.com (layout.astro)
//   img           *.scdn.co (covers), *.spotifycdn.com, placehold.co, data:/blob:
// X-Frame-Options DENY governs who may frame THIS site; framing sdk.scdn.co
// ourselves is unaffected.

function handler(event) {
    var response = event.response;
    var headers = response.headers;

    headers['strict-transport-security'] = { value: 'max-age=63072000; includeSubDomains; preload' };
    headers['x-frame-options'] = { value: 'DENY' };
    headers['x-content-type-options'] = { value: 'nosniff' };
    headers['referrer-policy'] = { value: 'strict-origin-when-cross-origin' };
    headers['permissions-policy'] = { value: 'camera=(), microphone=(), geolocation=(), payment=(), usb=()' };
    headers['content-security-policy'] = { value:
        "default-src 'self'; " +
        "script-src 'self' 'unsafe-inline' https://sdk.scdn.co; " +
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; " +
        "font-src 'self' data: https://fonts.gstatic.com; " +
        "img-src 'self' data: blob: https://*.scdn.co https://*.spotifycdn.com https://placehold.co; " +
        "connect-src 'self' https://*.spotify.com https://*.amazoncognito.com https://sdk.scdn.co https://*.scdn.co https://*.spotifycdn.com; " +
        "frame-src https://sdk.scdn.co https://*.spotify.com; " +
        "media-src 'self' blob: https://*.scdn.co; " +
        "worker-src 'self' blob:; " +
        "base-uri 'self'; " +
        "form-action 'self'; " +
        "object-src 'none'" };

    return response;
}
