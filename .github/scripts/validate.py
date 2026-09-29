#!/usr/bin/env python3
"""Fail if any YAML, JSON or TOML file under servers/ does not parse.

A config that does not parse is the most common way a plugin silently falls back to defaults
(or, like BellcraftBuild's plugin.yml once did, quietly stops doing its job).

With BASE set (CI), only files changed since BASE are checked, so files that were already broken
on the live servers do not fail every unrelated change. Run without BASE to check everything.
"""
import json, os, pathlib, subprocess, sys, tomllib
import yaml


class Loader(yaml.SafeLoader):
    pass


# Bukkit serialises ItemStacks with `==: org.bukkit...` keys and custom tags; accept any tag.
Loader.add_multi_constructor('', lambda loader, suffix, node: None)

base = os.environ.get('BASE', '').strip()
if base and set(base) != {'0'}:
    names = subprocess.run(['git', 'diff', '--name-only', '--diff-filter=ACMR', base, 'HEAD', '--', 'servers/'],
                           check=True, capture_output=True, text=True).stdout.splitlines()
    files = [pathlib.Path(n) for n in names if n]
else:
    files = sorted(pathlib.Path('servers').rglob('*'))

bad = []
for p in files:
    if not p.is_file():
        continue
    ext = p.suffix.lower()
    try:
        text = p.read_text(encoding='utf-8-sig')
        if ext in ('.yml', '.yaml'):
            list(yaml.load_all(text, Loader=Loader))
        elif ext in ('.json', '.mcmeta'):
            json.loads(text)
        elif ext == '.toml':
            tomllib.loads(text)
    except Exception as e:  # noqa: BLE001 - report every parser's error the same way
        msg = str(e).replace('\n', ' ')[:300]
        bad.append((p, msg))
        print(f'::error file={p}::{msg}')

print(f'checked {len(files)} file(s), {len(bad)} failed to parse')
sys.exit(1 if bad else 0)
