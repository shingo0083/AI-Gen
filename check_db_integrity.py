#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
from pathlib import Path

# 你可以按需改这个路径
DATA_JS = Path("static/js/data.js")

# 你项目里“应该存在”的 DB 顶层 key（按你现状）
REQUIRED_KEYS = [
    "styles_master",
    "styles_studio",
    "styles_unique",
    "CLOTHING",
    "accessories",
    "actions",
    "scenes",
    "effects",
    "shots",   # 你要求保留 inline
    "SHAPES",  # 保留 inline
    "CUPS",    # 保留 inline
]

IMPORT_RE = re.compile(r"import\s*\{\s*([A-Za-z0-9_$]+)\s*\}\s*from\s*'([^']+)'\s*;")
EXPORT_CONST_RE = re.compile(r"export\s+const\s+([A-Za-z0-9_$]+)\s*=")
DB_KEY_RE = re.compile(r"export\s+const\s+DB\s*=\s*\{([\s\S]*?)\}\s*;", re.M)


def fatal(msg: str, code: int = 1):
    print("FAIL:", msg)
    sys.exit(code)


def warn(msg: str):
    print("WARN:", msg)


def ok(msg: str):
    print("OK:", msg)


def count_top_level_entries(value_src: str) -> int:
    """
    Very rough counter for object literal entries:
    counts top-level ":" occurrences (not inside strings/brackets/braces).
    Works as a heuristic for "did this category suddenly shrink to 0?"
    """
    s = value_src
    # remove strings to reduce noise
    s = re.sub(r"('([^'\\]|\\.)*')", "''", s)
    s = re.sub(r'("([^"\\]|\\.)*")', '""', s)
    s = re.sub(r"(`([^`\\]|\\.)*`)", "``", s)

    depth_c = depth_b = depth_p = 0
    cnt = 0
    i = 0
    while i < len(s):
        c = s[i]
        if c == "{":
            depth_c += 1
        elif c == "}":
            depth_c = max(0, depth_c - 1)
        elif c == "[":
            depth_b += 1
        elif c == "]":
            depth_b = max(0, depth_b - 1)
        elif c == "(":
            depth_p += 1
        elif c == ")":
            depth_p = max(0, depth_p - 1)
        elif c == ":" and depth_c == 1 and depth_b == 0 and depth_p == 0:
            # depth_c==1 means inside the first-level object literal
            cnt += 1
        i += 1
    return cnt


def main():
    print("=== DB Integrity Check ===")

    if not DATA_JS.exists():
        fatal(f"Cannot find {DATA_JS}. Please run from project root or update DATA_JS path.")

    data_js_text = DATA_JS.read_text(encoding="utf-8")

    # 1) Parse imports and check module files exist
    imports = IMPORT_RE.findall(data_js_text)
    if not imports:
        warn("No imports found in data.js. If you didn't split, this might be OK. If you did split, something is wrong.")
    else:
        ok(f"Found {len(imports)} imports in {DATA_JS}")

    missing_files = []
    bad_exports = []
    module_stats = []

    for export_name, rel_path in imports:
        # resolve relative to data.js location
        mod_path = (DATA_JS.parent / rel_path).resolve()
        if not mod_path.exists():
            missing_files.append((export_name, rel_path, str(mod_path)))
            continue

        text = mod_path.read_text(encoding="utf-8", errors="replace")

        # sanity: must contain export const <export_name> =
        if not re.search(rf"export\s+const\s+{re.escape(export_name)}\s*=", text):
            bad_exports.append((export_name, str(mod_path)))

        # heuristic count
        # try to capture `export const X = ...;`
        m = re.search(rf"export\s+const\s+{re.escape(export_name)}\s*=\s*([\s\S]*?);\s*$", text.strip(), re.M)
        if m:
            value_src = m.group(1).strip()
            n = count_top_level_entries(value_src) if value_src.startswith("{") else -1
            module_stats.append((export_name, n))

    if missing_files:
        print("\nFAIL: Missing module files:")
        for exp, rel, full in missing_files:
            print(f"  - import {{{exp}}} from '{rel}'  => not found at: {full}")
        sys.exit(2)
    ok("All imported module files exist")

    if bad_exports:
        print("\nFAIL: Export name mismatch (module exists but doesn't export expected const):")
        for exp, full in bad_exports:
            print(f"  - {full}  (expected: export const {exp} = ...)")
        sys.exit(3)
    ok("All modules export expected const names")

    # 2) Check DB object contains required keys
    mdb = DB_KEY_RE.search(data_js_text)
    if not mdb:
        fatal("Cannot find `export const DB = { ... };` in data.js", 4)

    db_body = mdb.group(1)
    present_keys = set(re.findall(r"^\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*:", db_body, re.M))
    missing_keys = [k for k in REQUIRED_KEYS if k not in present_keys]
    if missing_keys:
        print("\nFAIL: DB is missing required top-level keys:")
        for k in missing_keys:
            print("  -", k)
        sys.exit(5)
    ok("DB contains all required top-level keys")

    # 3) Print simple stats
    if module_stats:
        print("\n--- Heuristic module entry counts (object literals only) ---")
        for name, n in sorted(module_stats, key=lambda x: x[0].lower()):
            if n >= 0:
                print(f"{name:16s} : ~{n} entries")
            else:
                print(f"{name:16s} : (non-object or couldn't estimate)")
        print("-----------------------------------------------------------")

    print("\n✅ Integrity check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())