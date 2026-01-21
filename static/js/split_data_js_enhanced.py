#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced splitter for data.js (ESM):

Input:
  export const DB = { ... };

Output:
  - Split each top-level key into a module file under /data (grouped dirs)
  - Keep excluded keys inline (default: SHAPES, CUPS, shots)
  - Rewrite data.js as an aggregator importing modules + inline excluded
  - Create backup: data.js.bak (once)

Grouping rules (customizable in code):
  styles_* -> data/styles/
  clothing/accessories/actions/scenes/effects/shots/cups/shapes -> data/catalog/
  others -> data/misc/
"""

from __future__ import annotations
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict

DEFAULT_EXCLUDES = {"SHAPES", "CUPS", "shots"}  # <- 按你要求：shots 也排除

# ---------- JS parsing helpers (no AST; string/comment aware) ----------

def strip_js_comments_keep_strings(src: str) -> str:
    """
    Returns a same-length string where comments are replaced by spaces,
    but string contents are preserved (so brace scanning won't be fooled).
    Handles // and /* */ comments and simple ', ", ` strings.
    """
    out = list(src)
    i = 0
    n = len(src)

    def is_escaped(j: int) -> bool:
        k = j - 1
        cnt = 0
        while k >= 0 and src[k] == '\\':
            cnt += 1
            k -= 1
        return (cnt % 2) == 1

    while i < n:
        ch = src[i]
        nxt = src[i + 1] if i + 1 < n else ''

        # strings
        if ch in ("'", '"', '`'):
            quote = ch
            i += 1
            while i < n:
                c = src[i]
                if c == quote and not is_escaped(i):
                    i += 1
                    break
                i += 1
            continue

        # line comment
        if ch == '/' and nxt == '/':
            j = i
            while j < n and src[j] != '\n':
                out[j] = ' '
                j += 1
            i = j
            continue

        # block comment
        if ch == '/' and nxt == '*':
            j = i
            out[j] = ' '
            if j + 1 < n:
                out[j + 1] = ' '
            j += 2
            while j + 1 < n and not (src[j] == '*' and src[j + 1] == '/'):
                out[j] = ' '
                j += 1
            if j + 1 < n:
                out[j] = ' '
                out[j + 1] = ' '
                j += 2
            i = j
            continue

        i += 1

    return ''.join(out)


def find_db_object_range(src: str) -> Tuple[int, int]:
    """
    Find { ... } range for `export const DB = { ... };`
    returns (index_of_open_brace, index_of_close_brace)
    """
    m = re.search(r'export\s+const\s+DB\s*=\s*\{', src)
    if not m:
        raise ValueError("Cannot find `export const DB = {` in the file.")
    start = m.end() - 1  # '{'
    masked = strip_js_comments_keep_strings(src)

    depth = 0
    i = start
    n = len(src)
    while i < n:
        c = masked[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return start, i
        i += 1
    raise ValueError("Unmatched braces while scanning DB object.")


def split_top_level_properties(src: str, obj_start: int, obj_end: int) -> List[Tuple[str, str]]:
    """
    Split DB object top-level properties: key: value,
    Return list of (key, value_expression_string).
    """
    masked = strip_js_comments_keep_strings(src)
    i = obj_start + 1
    end = obj_end
    props: List[Tuple[str, str]] = []

    def skip_ws(j: int) -> int:
        while j < end and masked[j].isspace():
            j += 1
        return j

    def read_key(j: int) -> Tuple[str, int]:
        j = skip_ws(j)
        if j >= end:
            return "", j

        if masked[j] in ("'", '"'):
            quote = masked[j]
            j += 1
            k = j
            while k < end:
                if masked[k] == quote and src[k - 1] != '\\':
                    return src[j:k], k + 1
                k += 1
            raise ValueError("Unclosed quoted key")
        else:
            k = j
            while k < end and re.match(r'[A-Za-z0-9_$]', masked[k]):
                k += 1
            return src[j:k].strip(), k

    def expect_colon(j: int) -> int:
        j = skip_ws(j)
        if j >= end or masked[j] != ':':
            raise ValueError(f"Expected ':' at position {j}")
        return j + 1

    def read_value(j: int) -> Tuple[str, int]:
        j = skip_ws(j)
        start_val = j
        depth_curly = depth_brack = depth_paren = 0

        while j < end:
            c = masked[j]

            # strings: skip
            if c in ("'", '"', '`'):
                quote = c
                j += 1
                while j < end:
                    if masked[j] == quote and src[j - 1] != '\\':
                        j += 1
                        break
                    j += 1
                continue

            if c == '{':
                depth_curly += 1
            elif c == '}':
                if depth_curly > 0:
                    depth_curly -= 1
            elif c == '[':
                depth_brack += 1
            elif c == ']':
                if depth_brack > 0:
                    depth_brack -= 1
            elif c == '(':
                depth_paren += 1
            elif c == ')':
                if depth_paren > 0:
                    depth_paren -= 1

            # top-level comma ends this value
            if c == ',' and depth_curly == 0 and depth_brack == 0 and depth_paren == 0:
                return src[start_val:j].strip(), j + 1

            j += 1

        return src[start_val:end].strip(), end

    while True:
        i = skip_ws(i)
        if i >= end:
            break
        if masked[i] == ',':
            i += 1
            continue

        key, i2 = read_key(i)
        if not key:
            break

        i3 = expect_colon(i2)
        val, i4 = read_value(i3)
        props.append((key, val))
        i = i4

    return props


def is_ident(key: str) -> bool:
    return re.match(r'^[A-Za-z_$][A-Za-z0-9_$]*$', key) is not None


def safe_ident_from_key(key: str) -> str:
    """
    For module export const name.
    If key is a valid JS identifier, keep it.
    Else generate a safe identifier.
    """
    if is_ident(key):
        return key
    # turn into lower_snake-ish
    name = re.sub(r'[^A-Za-z0-9_]+', '_', key).strip('_')
    if not name:
        name = "module"
    # identifiers can't start with digit
    if re.match(r'^[0-9]', name):
        name = "_" + name
    return name


def safe_module_filename(key: str) -> str:
    name = re.sub(r'[^A-Za-z0-9_]+', '_', key).strip('_')
    return (name or "module").lower()


def pick_subdir(key: str) -> str:
    """
    Decide output folder under /data.
    """
    if key.startswith("styles_"):
        return "styles"
    if key in {"CLOTHING", "accessories", "actions", "scenes", "effects", "shots", "CUPS", "SHAPES"}:
        return "catalog"
    return "misc"


def main():
    if len(sys.argv) < 2:
        print("Usage: python split_data_js_enhanced.py path/to/data.js [output_dir=data] [--exclude=SHAPES,CUPS,shots]")
        sys.exit(1)

    in_path = Path(sys.argv[1]).resolve()

    # output_dir
    out_dir = None
    excludes = set(DEFAULT_EXCLUDES)

    for arg in sys.argv[2:]:
        if arg.startswith("--exclude="):
            excludes = set(x.strip() for x in arg.split("=", 1)[1].split(",") if x.strip())
        elif not arg.startswith("--") and out_dir is None:
            out_dir = Path(arg).resolve()

    if out_dir is None:
        out_dir = in_path.parent / "data"

    src = in_path.read_text(encoding="utf-8")
    obj_start, obj_end = find_db_object_range(src)
    props = split_top_level_properties(src, obj_start, obj_end)
    if not props:
        raise ValueError("No top-level properties found in DB object.")

    # backup once
    bak = in_path.with_suffix(in_path.suffix + ".bak")
    if not bak.exists():
        bak.write_text(src, encoding="utf-8")

    out_dir.mkdir(parents=True, exist_ok=True)

    # write modules + build aggregator imports/db
    imports: List[str] = []
    db_lines: List[str] = ["export const DB = {"]

    for key, value in props:
        # keep excluded inline
        if key in excludes:
            k = key if is_ident(key) else repr(key)
            db_lines.append(f"  {k}: {value},")
            continue

        subdir = pick_subdir(key)
        mod_dir = out_dir / subdir
        mod_dir.mkdir(parents=True, exist_ok=True)

        file_name = safe_module_filename(key) + ".js"
        file_path = mod_dir / file_name

        export_name = safe_ident_from_key(key)

        module_code = (
            "/** Auto-split from data.js */\n"
            f"export const {export_name} = {value};\n"
        )
        file_path.write_text(module_code, encoding="utf-8")

        # compute relative import path from data.js
        rel = f"./data/{subdir}/{file_name}"
        imports.append(f"import {{ {export_name} }} from '{rel}';")

        k = key if is_ident(key) else repr(key)
        db_lines.append(f"  {k}: {export_name},")

    db_lines.append("};")

    header = "/** Auto-generated aggregator. Original backed up as data.js.bak */"
    new_data_js = "\n".join([header] + imports + [""] + db_lines + [""])
    in_path.write_text(new_data_js, encoding="utf-8")

    print("✅ Split complete.")
    print(f"- Excluded (kept inline): {sorted(excludes)}")
    print(f"- Modules root: {out_dir}")
    print(f"- Aggregator updated: {in_path}")
    print(f"- Backup: {bak}")


if __name__ == "__main__":
    main()
