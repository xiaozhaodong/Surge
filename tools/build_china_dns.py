#!/usr/bin/env python3
"""Merge the upstream DOMAIN-SET, local additions and reviewed exclusions.

Only writes new candidate/report files. Review their diff before replacing the
deployed list. No Git, Surge runtime or network-routing state is changed.
"""

import argparse
import hashlib
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = (
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/"
    "master/rule/Surge/China/China_Domain.list"
)
LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")


def parse(text, source, domain_set=False):
    rules = []
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith(("#", "//")):
            continue
        if domain_set:
            kind = "DOMAIN-SUFFIX" if line.startswith(".") else "DOMAIN"
            domain = line[1:] if line.startswith(".") else line
        else:
            parts = line.split(",")
            if len(parts) != 2:
                raise ValueError(f"{source}:{number}: expected TYPE,domain: {line}")
            kind, domain = parts
        domain = domain.lower().rstrip(".")
        if kind not in {"DOMAIN", "DOMAIN-SUFFIX"}:
            raise ValueError(f"{source}:{number}: unsupported rule type: {kind}")
        if len(domain) > 253 or any(not LABEL.fullmatch(p) for p in domain.split(".")):
            raise ValueError(f"{source}:{number}: invalid domain: {domain}")
        if "." not in domain or domain in {"com.cn", "net.cn", "org.cn", "edu.cn"}:
            raise ValueError(f"{source}:{number}: overly broad domain: {domain}")
        rules.append((kind, domain))
    if not rules:
        raise ValueError(f"{source}: no domain rules found")
    return rules


def contains(parent, child):
    """Whether every hostname matched by child is also matched by parent."""
    pk, pd = parent
    ck, cd = child
    if pk == "DOMAIN":
        return ck == "DOMAIN" and pd == cd
    return cd == pd or cd.endswith("." + pd)


def merge(upstream, extra, excluded):
    unique = set(upstream + extra)
    removed = []
    kept = set()
    for rule in sorted(unique, key=lambda r: (r[1], r[0])):
        blockers = [block for block in excluded if contains(block, rule)]
        if blockers:
            removed.append({"rule": ",".join(rule), "excluded_by": ",".join(blockers[0])})
            continue
        # A positive suffix cannot express a hole for an excluded child.
        conflicts = [block for block in excluded if contains(rule, block)]
        if conflicts:
            raise ValueError(
                f"Exclusion {conflicts[0]} is covered by {rule}; "
                "remove or narrow the parent rule before building"
            )
        kept.add(rule)
    suffixes = {d for k, d in kept if k == "DOMAIN-SUFFIX"}
    final, redundant = [], []
    for kind, domain in sorted(kept, key=lambda r: (r[1], r[0])):
        labels = domain.split(".")
        ancestors = [".".join(labels[i:]) for i in range(1, len(labels))]
        covered = (kind == "DOMAIN" and domain in suffixes) or any(
            parent in suffixes for parent in ancestors
        )
        (redundant if covered else final).append((kind, domain))
    if not final:
        raise ValueError("No output rules remain")
    return final, removed, redundant


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, help="Use a saved upstream file instead of HTTPS")
    parser.add_argument("--extra", type=Path, default=ROOT / "rule/ChinaDNS.extra.list")
    parser.add_argument("--exclude", type=Path, default=ROOT / "rule/ChinaDNS.exclude.list")
    parser.add_argument("--output", type=Path, required=True, help="New candidate file (must not exist)")
    parser.add_argument("--report", type=Path, help="New JSON report file (must not exist)")
    args = parser.parse_args()
    targets = [args.output] + ([args.report] if args.report else [])
    if len({p.resolve() for p in targets}) != len(targets):
        parser.error("output and report must use different paths")
    for target in targets:
        if target.exists() or target.is_symlink():
            parser.error(f"refusing to overwrite {target}; generate a new candidate and review its diff")
        if not target.parent.is_dir():
            parser.error(f"output directory does not exist: {target.parent}")
    if args.upstream:
        raw = args.upstream.read_bytes()
    else:
        request = urllib.request.Request(UPSTREAM, headers={"User-Agent": "Surge-ChinaDNS-builder/1.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
    upstream = parse(raw.decode("utf-8-sig"), "upstream", domain_set=True)
    extra_raw = args.extra.read_bytes()
    exclude_raw = args.exclude.read_bytes()
    extra = parse(extra_raw.decode("utf-8-sig"), str(args.extra))
    excluded = parse(exclude_raw.decode("utf-8-sig"), str(args.exclude))
    final, removed, redundant = merge(upstream, extra, excluded)
    digest = hashlib.sha256(raw).hexdigest()
    counts = dict(Counter(k for k, _ in final))
    header = [
        "# NAME: ChinaDNS",
        "# MAINTAINER: xiaozhaodong/Surge",
        "# SPDX-License-Identifier: GPL-2.0-only",
        "# Derived from blackmatrix7/ios_rule_script; see ChinaDNS.LICENSE and ChinaDNS.md.",
        "# LOCAL-MODIFICATIONS: format conversion, exclusions and additions; first adapted 2026-11-06.",
        f"# UPSTREAM: {UPSTREAM}",
        f"# UPSTREAM-SHA256: {digest}",
        f"# TOTAL: {len(final)}",
        "# Generated by tools/build_china_dns.py; use RULE-SET:, not DOMAIN-SET:.",
        "# Maintain ChinaDNS.extra.list / ChinaDNS.exclude.list, then rebuild and review.",
        "# Domain rules for DNS mapping and traffic routing; policies are set in the profile.",
        "# Retained upstream entries are not an individually verified all-China inventory.",
        "",
    ]
    output = "\n".join(header + [",".join(rule) for rule in final]) + "\n"
    report = {
        "upstream_url": UPSTREAM,
        "upstream_sha256": digest,
        "extra_sha256": hashlib.sha256(extra_raw).hexdigest(),
        "exclude_sha256": hashlib.sha256(exclude_raw).hexdigest(),
        "upstream_entries": len(upstream),
        "extra_entries": len(extra),
        "exclusion_selectors": len(excluded),
        "duplicate_entries_removed": len(upstream + extra) - len(set(upstream + extra)),
        "excluded_entries": len(removed),
        "redundant_entries_removed": len(redundant),
        "output_entries": len(final),
        "output_types": counts,
        "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
        "removed": removed,
        "redundant": [",".join(r) for r in redundant],
    }
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(output)
    if args.report:
        with args.report.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in {"removed", "redundant"}}, indent=2))


if __name__ == "__main__":
    main()
