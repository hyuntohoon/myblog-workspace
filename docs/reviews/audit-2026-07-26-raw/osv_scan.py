#!/usr/bin/env python3
"""Query OSV.dev for known vulns in this workspace's ACTUAL resolved dependencies.

Independent of `pnpm audit` (its legacy /audits endpoint times out here) and of
Dependabot (disabled on all 6 repos).

Two corrections over the naive approach, both of which change the answer:
  1. Python versions come from each service's real venv, NOT from requirements.txt.
     Several pins are wildcards (`SQLAlchemy==2.*`); feeding "2.*" to OSV matches
     ancient 0.x/1.x CVEs and produces bogus CRITICALs.
  2. npm hits are split by whether the package can reach the browser bundle
     (package.json `dependencies`) or is build-tooling only (`devDependencies`).
     This is a prebuilt static site on S3 — no npm code runs on a server.

Read-only.
"""
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

WS = Path("/Users/park_hyun/myblog-workspace")
BATCH, ONE = "https://api.osv.dev/v1/querybatch", "https://api.osv.dev/v1/vulns/"
PY_REPOS = ("myblog_backend", "myblog_music", "myblog_worker", "myblog_shared_db")


def post(url, payload, timeout=90):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def npm_universe():
    """(name, version) for every resolved package, plus the direct-runtime name set."""
    lock = (WS / "myblog_front" / "pnpm-lock.yaml").read_text()
    pkgs, in_pkgs = set(), False
    for line in lock.split("\n"):
        if line.startswith("packages:"):
            in_pkgs = True
            continue
        if in_pkgs and line and not line.startswith(" "):
            break
        if not in_pkgs:
            continue
        m = re.match(r"^  '?([^']+?)'?:\s*$", line)
        if not m:
            continue
        spec = m.group(1)
        i = spec.rfind("@")
        if i <= 0:
            continue
        name, ver = spec[:i], spec[i + 1:].split("(")[0]
        if re.match(r"^\d", ver):
            pkgs.add((name, ver))
    pj = json.loads((WS / "myblog_front" / "package.json").read_text())
    return sorted(pkgs), set((pj.get("dependencies") or {}).keys())


def py_universe():
    """(name, version, repo) from each service's real venv; falls back to exact pins."""
    out = set()
    for repo in PY_REPOS:
        venv = WS / repo / ".venv" / "bin" / "python"
        if venv.exists():
            try:
                raw = subprocess.run(
                    [str(venv), "-c",
                     "import json,importlib.metadata as m;"
                     "print(json.dumps([[d.metadata['Name'],d.version] for d in m.distributions()]))"],
                    capture_output=True, text=True, timeout=90).stdout
                for n, v in json.loads(raw):
                    if n:
                        out.add((n.lower(), v, repo))
                continue
            except Exception as e:  # noqa: BLE001
                print(f"  !! {repo} venv introspection failed: {e}", file=sys.stderr)
        for req in (WS / repo).glob("requirements*.txt"):
            for line in req.read_text().split("\n"):
                line = line.split("#")[0].strip()
                m = re.match(r"^([A-Za-z0-9._-]+)\s*==\s*(\d+(?:\.\d+)*)\s*$", line)
                if m:  # exact pins only — wildcards like 2.* are unusable
                    out.add((m.group(1).lower(), m.group(2), repo))
    return sorted(out)


def scan(queries, labels, eco):
    hits = {}
    for i in range(0, len(queries), 200):
        try:
            res = post(BATCH, {"queries": queries[i:i + 200]})
        except Exception as e:  # noqa: BLE001
            print(f"  !! {eco} batch @{i} failed: {e}", file=sys.stderr)
            continue
        for label, r in zip(labels[i:i + 200], res.get("results", [])):
            ids = [v["id"] for v in (r.get("vulns") or [])]
            if ids:
                hits.setdefault(label, []).extend(ids)
    return hits


def detail_of(ids):
    out = {}
    for vid in ids:
        try:
            d = get(ONE + vid)
            sev = d.get("database_specific", {}).get("severity")
            if not sev:
                for s in d.get("severity", []) or []:
                    sev = s.get("score", "")
            out[vid] = {"summary": (d.get("summary") or "").strip(),
                        "severity": (sev or "?"),
                        "withdrawn": bool(d.get("withdrawn")),
                        "aliases": d.get("aliases", [])}
        except Exception as e:  # noqa: BLE001
            out[vid] = {"summary": f"<lookup failed: {e}>", "severity": "?",
                        "withdrawn": False, "aliases": []}
    return out


SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3}


def render(title, hits, detail, note_fn=None):
    print("\n" + "=" * 76)
    print(f"{title} — {len(hits)} package(s) with advisories")
    print("=" * 76)
    rows = []
    for pkg, ids in hits.items():
        worst = min((SEV_ORDER.get(detail[i]["severity"], 9) for i in ids), default=9)
        rows.append((worst, pkg, ids))
    for _, pkg, ids in sorted(rows):
        note = f"   <-- {note_fn(pkg)}" if note_fn else ""
        print(f"\n{pkg}{note}")
        for vid in sorted(set(ids), key=lambda v: SEV_ORDER.get(detail[v]["severity"], 9)):
            d = detail[vid]
            if d["withdrawn"]:
                continue
            cve = next((a for a in d["aliases"] if a.startswith("CVE-")), "")
            print(f"   [{d['severity']:9s}] {vid} {cve}")
            if d["summary"]:
                print(f"               {d['summary'][:120]}")


def main():
    npm, runtime_names = npm_universe()
    py = py_universe()
    print(f"npm packages resolved in lockfile : {len(npm)}")
    print(f"  of which direct runtime deps    : {len(runtime_names)}")
    print(f"python packages in service venvs  : {len(py)}")

    npm_hits = scan([{"package": {"name": n, "ecosystem": "npm"}, "version": v} for n, v in npm],
                    [f"{n}@{v}" for n, v in npm], "npm")
    py_hits = scan([{"package": {"name": n, "ecosystem": "PyPI"}, "version": v} for n, v, _ in py],
                   [f"{n}@{v} [{r}]" for n, v, r in py], "PyPI")

    detail = detail_of(sorted({i for v in list(npm_hits.values()) + list(py_hits.values()) for i in v}))

    # split npm by browser-reachability
    ship = {k: v for k, v in npm_hits.items() if k.rsplit("@", 1)[0] in runtime_names}
    build = {k: v for k, v in npm_hits.items() if k.rsplit("@", 1)[0] not in runtime_names}

    render("NPM — DIRECT RUNTIME DEPENDENCY (can reach the browser bundle)", ship, detail)
    render("NPM — transitive / build-tooling only (never served to a user)", build, detail)
    render("PyPI — runs inside the Lambdas", py_hits, detail)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
