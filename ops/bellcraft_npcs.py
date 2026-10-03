#!/usr/bin/env python3
"""NPC registry for RPG survival, and the reclaim rules the Grim Reaper uses.

plugins/Skript/npcs.yml is the list people edit. Skript cannot read that YAML,
so `python3 ops/bellcraft_npcs.py --write` copies it into the marked block in
bellcraft-npcs.sk. `--check` fails when the two disagree.

The payment rules here are the contract bellcraft-graves.sk and
bellcraft-npcs.sk implement. They are pure so the unit tests can run them
without a Minecraft server.
"""
import argparse
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
NPC_YAML = ROOT / "servers" / "survival" / "plugins" / "Skript" / "npcs.yml"
NPC_SKRIPT = ROOT / "servers" / "survival" / "plugins" / "Skript" / "scripts" / "bellcraft-npcs.sk"
GRAVE_SKRIPT = ROOT / "servers" / "survival" / "plugins" / "Skript" / "scripts" / "bellcraft-graves.sk"

BEGIN = "# BEGIN NPC REGISTRY"
END = "# END NPC REGISTRY"

ENTITIES = ("villager", "wither_skeleton", "skeleton", "husk", "zombie")
HELMETS = ("wither_skeleton_skull", "skeleton_skull", "netherite_helmet", "carved_pumpkin")
CHESTS = ("netherite_chestplate", "leather_chestplate")
HANDS = ("netherite_hoe", "netherite_sword", "stick", "bone")
ACTIONS = ("reclaim-grave", "say")
LINE_KEYS = ("confirm", "paid", "none", "cooldown", "funds")
RECLAIM_LINES = LINE_KEYS
SETTINGS = ("confirm-seconds", "reach", "near-blocks", "ensure-seconds")
NPC_FIELDS = (
    "name", "world", "x", "y", "z", "yaw", "pitch", "entity", "skin",
    "helmet", "chest", "hand", "action", "price", "confirm", "dialogue", "lines",
)


def reclaim_cost(tier, per_tier):
    """Zone tier times the per-tier price. Missing or low tiers count as 1."""
    try:
        tier_n = int(tier)
    except (TypeError, ValueError):
        tier_n = 1
    if tier_n < 1:
        tier_n = 1
    try:
        per = int(per_tier)
    except (TypeError, ValueError):
        per = 0
    if per < 0:
        per = 0
    return tier_n * per


def price_cost(price, tier, per_tier):
    """`tier` uses the grave formula. A number is a flat coin price."""
    if price == "tier":
        return reclaim_cost(tier, per_tier)
    try:
        flat = int(price)
    except (TypeError, ValueError):
        return reclaim_cost(tier, per_tier)
    if flat < 0:
        return 0
    return flat


def oldest_grave(ids):
    """The oldest grave is the first id stored for that player."""
    if not ids:
        return None
    return ids[0]


def decide_reclaim(grave_id, balance, cost, cooling, offer_grave, offer_until, now, confirm, confirm_seconds, offer_ready=None):
    """What one click on a reclaim NPC does.

    Returns (status, offer_grave, offer_until, offer_ready, charged).
    status is none, cooldown, quote, hold, funds, or ok.
    A fresh offer is required before money moves when confirm is set.
    The offer matches one grave id, cannot be paid until offer_ready
    (one second after the quote, so a double right-click does not pay),
    and expires at offer_until.
    """
    if not grave_id:
        return ("none", None, None, None, False)
    if cooling:
        return ("cooldown", offer_grave, offer_until, offer_ready, False)
    try:
        cost_n = int(cost)
    except (TypeError, ValueError):
        cost_n = 0
    if cost_n < 0:
        cost_n = 0
    try:
        balance_n = float(balance)
    except (TypeError, ValueError):
        balance_n = 0
    if confirm and offer_grave == grave_id and offer_ready is not None and now < offer_ready:
        return ("hold", offer_grave, offer_until, offer_ready, False)
    fresh = offer_grave != grave_id or offer_until is None or now >= offer_until
    if confirm and fresh:
        return ("quote", grave_id, now + confirm_seconds, now + 1, False)
    if balance_n < cost_n:
        return ("funds", offer_grave, offer_until, offer_ready, False)
    return ("ok", None, None, None, True)


def _text(value, field):
    if not isinstance(value, str):
        return f"{field} must be text"
    if '"' in value or "\n" in value or "\\" in value:
        return f"{field} cannot contain quotes, backslashes, or new lines"
    return None


def _num(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return f"{field} must be a number"
    return None


def validate(config):
    """Return a list of human-readable problems. Empty means the file can ship."""
    errors = []
    if not isinstance(config, dict):
        return ["config must be a mapping"]
    settings = config.get("settings")
    npcs = config.get("npcs")
    if set(config) - {"settings", "npcs"}:
        errors.append("only settings and npcs are allowed at the top")
    if not isinstance(settings, dict):
        errors.append("settings must be a mapping")
        settings = {}
    else:
        missing = [key for key in SETTINGS if key not in settings]
        extra = [key for key in settings if key not in SETTINGS]
        if missing:
            errors.append("settings missing " + ", ".join(missing))
        if extra:
            errors.append("unknown settings " + ", ".join(sorted(extra)))
        for key in ("confirm-seconds", "reach", "near-blocks", "ensure-seconds"):
            if key in settings and (isinstance(settings[key], bool) or not isinstance(settings[key], int) or settings[key] < 1):
                errors.append(f"settings.{key} must be a whole number of at least 1")
    if not isinstance(npcs, dict) or not npcs:
        errors.append("npcs must list at least the grim-reaper")
        return errors
    for npc_id, npc in npcs.items():
        where = f"npcs.{npc_id}"
        if not isinstance(npc_id, str) or not npc_id.replace("-", "").isalnum() or npc_id != npc_id.lower():
            errors.append(f"{where} id must be lowercase letters, numbers, and dashes")
        if not isinstance(npc, dict):
            errors.append(f"{where} must be a mapping")
            continue
        extra = [key for key in npc if key not in NPC_FIELDS]
        if extra:
            errors.append(f"{where} unknown keys " + ", ".join(sorted(extra)))
        for key in ("name", "world", "entity", "action", "dialogue"):
            if key not in npc:
                errors.append(f"{where} missing {key}")
        name_err = _text(npc.get("name", ""), f"{where}.name")
        if npc.get("name", "") == "":
            errors.append(f"{where}.name must be text")
        elif name_err:
            errors.append(name_err)
        world = npc.get("world", "")
        if not isinstance(world, str) or not world.replace("_", "").isalnum():
            errors.append(f"{where}.world must be a world name")
        for key in ("x", "y", "z", "yaw", "pitch"):
            err = _num(npc.get(key), f"{where}.{key}")
            if err:
                errors.append(err)
        if isinstance(npc.get("y"), (int, float)) and not isinstance(npc.get("y"), bool):
            if not -64 <= npc["y"] <= 320:
                errors.append(f"{where}.y must be between -64 and 320")
        entity = npc.get("entity")
        if entity not in ENTITIES:
            errors.append(f"{where}.entity must be one of " + ", ".join(ENTITIES))
        skin = npc.get("skin", "")
        if skin != "" and (not isinstance(skin, str) or not skin.replace("_", "").isalnum() or len(skin) > 16):
            errors.append(f"{where}.skin must be empty or a Minecraft username")
        elif isinstance(skin, str) and ('"' in skin or "\\" in skin):
            errors.append(f"{where}.skin cannot contain quotes or backslashes")
        for key, allowed in (("helmet", HELMETS), ("chest", CHESTS), ("hand", HANDS)):
            item = npc.get(key, "")
            if item == "":
                continue
            if item not in allowed:
                errors.append(f"{where}.{key} must be empty or one of " + ", ".join(allowed))
        action = npc.get("action")
        if action not in ACTIONS:
            errors.append(f"{where}.action must be one of " + ", ".join(ACTIONS))
        price = npc.get("price", "tier")
        if price != "tier" and (isinstance(price, bool) or not isinstance(price, int) or price < 0):
            errors.append(f"{where}.price must be tier or a coin amount of at least 0")
        if "confirm" in npc and not isinstance(npc["confirm"], bool):
            errors.append(f"{where}.confirm must be true or false")
        dialogue = npc.get("dialogue")
        if not isinstance(dialogue, list) or not dialogue:
            errors.append(f"{where}.dialogue must be a list of lines")
        else:
            for index, line in enumerate(dialogue):
                err = _text(line, f"{where}.dialogue[{index}]")
                if line == "":
                    errors.append(f"{where}.dialogue[{index}] is empty")
                elif err:
                    errors.append(err)
        lines = npc.get("lines", {})
        if lines is None:
            lines = {}
        if not isinstance(lines, dict):
            errors.append(f"{where}.lines must be a mapping")
            lines = {}
        if action == "reclaim-grave":
            for key in RECLAIM_LINES:
                err = _text(lines.get(key, ""), f"{where}.lines.{key}")
                if not lines.get(key):
                    errors.append(f"{where}.lines.{key} is required for reclaim-grave")
                elif err:
                    errors.append(err)
        else:
            for key, line in lines.items():
                if key not in LINE_KEYS:
                    errors.append(f"{where}.lines.{key} is not a known line")
                else:
                    err = _text(line, f"{where}.lines.{key}")
                    if err:
                        errors.append(err)
    if "grim-reaper" not in npcs:
        errors.append("npcs.grim-reaper is required")
    elif isinstance(npcs.get("grim-reaper"), dict) and npcs["grim-reaper"].get("action") != "reclaim-grave":
        errors.append("npcs.grim-reaper action must be reclaim-grave")
    return errors


def _sk_string(value):
    return '"' + value + '"'


def _sk_num(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, float):
        return ("%f" % value).rstrip("0").rstrip(".")
    return str(int(value))


def render_registry(config):
    """Skript statements for the marked block. One indent level, trailing newline."""
    lines = []
    for npc_id, npc in config["npcs"].items():
        price = npc.get("price", "tier")
        price_text = "tier" if price == "tier" else str(int(price))
        confirm = "true" if npc.get("confirm", False) else "false"
        lines.append(f'    defineNpc("{npc_id}")')
        lines.append(f'    npcName("{npc_id}", {_sk_string(npc["name"])})')
        lines.append(
            '    npcPlace("%s", "%s", %s, %s, %s, %s, %s)' % (
                npc_id, npc["world"], _sk_num(npc["x"]), _sk_num(npc["y"]),
                _sk_num(npc["z"]), _sk_num(npc["yaw"]), _sk_num(npc["pitch"]),
            )
        )
        lines.append(
            '    npcLook("%s", "%s", %s, %s, %s, %s)' % (
                npc_id, npc["entity"], _sk_string(npc.get("skin", "")),
                _sk_string(npc.get("helmet", "")), _sk_string(npc.get("chest", "")),
                _sk_string(npc.get("hand", "")),
            )
        )
        lines.append(f'    npcJob("{npc_id}", "{npc["action"]}", "{price_text}", {confirm})')
        for line in npc["dialogue"]:
            lines.append(f'    npcLine("{npc_id}", "dialogue", {_sk_string(line)})')
        for key in LINE_KEYS:
            text = (npc.get("lines") or {}).get(key)
            if text:
                lines.append(f'    npcLine("{npc_id}", "{key}", {_sk_string(text)})')
    return "\n".join(lines) + "\n"


def registry_block(skript_text):
    lines = skript_text.splitlines(keepends=True)
    begin = end = None
    for index, line in enumerate(lines):
        if line.strip() == BEGIN:
            begin = index
        elif line.strip() == END:
            end = index
    if begin is None or end is None or end < begin:
        raise ValueError("NPC registry markers are missing")
    return lines, begin, end


def registry_inside(skript_text):
    lines, begin, end = registry_block(skript_text)
    return "".join(lines[begin + 1:end])


def write_registry(skript_text, config):
    lines, begin, end = registry_block(skript_text)
    rendered = render_registry(config)
    if not rendered.endswith("\n"):
        rendered += "\n"
    return "".join(lines[:begin + 1]) + rendered + "".join(lines[end:])


def load_config(path=NPC_YAML):
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    errors = validate(data)
    if errors:
        raise ValueError("\n".join(errors))
    return data


def check(config=None, skript_text=None):
    """Return a mismatch description, or None when the registry matches the YAML."""
    if config is None:
        config = load_config()
    if skript_text is None:
        skript_text = NPC_SKRIPT.read_text(encoding="utf-8")
    inside = registry_inside(skript_text)
    expected = render_registry(config)
    if inside != expected:
        return "registry block does not match npcs.yml\n--- skript ---\n%s\n--- yaml ---\n%s" % (inside, expected)
    return None


def main(argv):
    parser = argparse.ArgumentParser(description="Check or write the survival NPC registry.")
    parser.add_argument("--write", action="store_true", help="rewrite the registry block in bellcraft-npcs.sk")
    parser.add_argument("--check", action="store_true", help="fail if the registry block drifted from npcs.yml")
    args = parser.parse_args(argv)
    config = load_config()
    if args.write:
        text = NPC_SKRIPT.read_text(encoding="utf-8")
        NPC_SKRIPT.write_text(write_registry(text, config), encoding="utf-8")
        print(f"wrote {NPC_SKRIPT.relative_to(ROOT)}")
    if args.check or not args.write:
        mismatch = check(config)
        if mismatch:
            print(mismatch, file=sys.stderr)
            return 1
        if args.check:
            print("npc registry matches")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
