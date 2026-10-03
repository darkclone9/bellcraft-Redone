#!/usr/bin/env python3
"""Registry and reclaim rules for the survival Grim Reaper NPC. No Minecraft server."""
import pathlib
import unittest

import bellcraft_npcs as npcs

ROOT = pathlib.Path(__file__).resolve().parents[1]


class ReclaimRuleTests(unittest.TestCase):
    def test_cost_uses_tier_and_treats_low_tiers_as_one(self):
        self.assertEqual(npcs.reclaim_cost(3, 20), 60)
        self.assertEqual(npcs.reclaim_cost(1, 20), 20)
        self.assertEqual(npcs.reclaim_cost(0, 20), 20)
        self.assertEqual(npcs.reclaim_cost(None, 20), 20)
        self.assertEqual(npcs.reclaim_cost(4, 0), 0)
        self.assertEqual(npcs.reclaim_cost(4, -5), 0)

    def test_flat_price_overrides_tier(self):
        self.assertEqual(npcs.price_cost("tier", 5, 20), 100)
        self.assertEqual(npcs.price_cost(40, 5, 20), 40)
        self.assertEqual(npcs.price_cost(0, 5, 20), 0)
        self.assertEqual(npcs.price_cost(-3, 5, 20), 0)

    def test_oldest_grave_is_the_first_id(self):
        self.assertIsNone(npcs.oldest_grave([]))
        self.assertEqual(npcs.oldest_grave(["4", "9"]), "4")

    def test_confirm_quotes_before_it_charges(self):
        status, offer, until, ready, charged = npcs.decide_reclaim(
            "4", 100, 40, False, None, None, now=0, confirm=True, confirm_seconds=25)
        self.assertEqual(status, "quote")
        self.assertEqual((offer, until, ready), ("4", 25, 1))
        self.assertFalse(charged)
        status, offer, until, ready, charged = npcs.decide_reclaim(
            "4", 100, 40, False, offer, until, now=0, confirm=True, confirm_seconds=25, offer_ready=ready)
        self.assertEqual(status, "hold")
        self.assertFalse(charged)
        status, offer, until, ready, charged = npcs.decide_reclaim(
            "4", 100, 40, False, offer, until, now=1, confirm=True, confirm_seconds=25, offer_ready=ready)
        self.assertEqual((status, offer, until, ready, charged), ("ok", None, None, None, True))

    def test_expired_offer_quotes_again(self):
        status, offer, until, ready, charged = npcs.decide_reclaim(
            "4", 100, 40, False, "4", 25, now=25, confirm=True, confirm_seconds=25, offer_ready=1)
        self.assertEqual(status, "quote")
        self.assertEqual((until, ready), (50, 26))
        self.assertFalse(charged)

    def test_short_balance_does_not_charge_or_drop_the_offer(self):
        status, offer, until, ready, charged = npcs.decide_reclaim(
            "4", 10, 40, False, "4", 25, now=10, confirm=True, confirm_seconds=25, offer_ready=1)
        self.assertEqual((status, offer, until, ready, charged), ("funds", "4", 25, 1, False))

    def test_cooldown_blocks_payment(self):
        status, offer, until, ready, charged = npcs.decide_reclaim(
            "4", 100, 40, True, "4", 25, now=10, confirm=True, confirm_seconds=25, offer_ready=1)
        self.assertEqual(status, "cooldown")
        self.assertFalse(charged)
        self.assertEqual((offer, ready), ("4", 1))

    def test_no_grave_clears_the_offer(self):
        self.assertEqual(
            npcs.decide_reclaim("", 100, 40, False, "4", 25, now=10, confirm=True, confirm_seconds=25, offer_ready=1),
            ("none", None, None, None, False))

    def test_confirm_off_pays_on_the_first_click(self):
        status, offer, until, ready, charged = npcs.decide_reclaim(
            "4", 40, 40, False, None, None, now=0, confirm=False, confirm_seconds=25)
        self.assertEqual((status, charged), ("ok", True))
        self.assertIsNone(offer)
        self.assertIsNone(ready)
        status, _, _, _, charged = npcs.decide_reclaim(
            "4", 39, 40, False, None, None, now=0, confirm=False, confirm_seconds=25)
        self.assertEqual((status, charged), ("funds", False))

    def test_a_different_grave_needs_a_new_quote(self):
        status, offer, _, ready, charged = npcs.decide_reclaim(
            "9", 100, 20, False, "4", 25, now=10, confirm=True, confirm_seconds=25, offer_ready=1)
        self.assertEqual((status, offer, ready, charged), ("quote", "9", 11, False))

    def test_free_reclaim_still_counts_as_paid(self):
        status, _, _, _, charged = npcs.decide_reclaim(
            "4", 0, 0, False, "4", 25, now=1, confirm=True, confirm_seconds=25, offer_ready=1)
        self.assertEqual((status, charged), ("ok", True))


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.config = npcs.load_config()

    def test_yaml_matches_the_skript_registry(self):
        self.assertIsNone(npcs.check(self.config))

    def test_grim_reaper_is_the_shipped_npc(self):
        reaper = self.config["npcs"]["grim-reaper"]
        self.assertEqual(reaper["action"], "reclaim-grave")
        self.assertEqual(reaper["price"], "tier")
        self.assertTrue(reaper["confirm"])
        self.assertEqual(reaper["entity"], "villager")
        self.assertEqual(reaper["world"], "world")
        self.assertEqual(reaper["helmet"], "wither_skeleton_skull")
        self.assertEqual(reaper["hand"], "netherite_hoe")
        self.assertGreaterEqual(len(reaper["dialogue"]), 1)
        for key in npcs.RECLAIM_LINES:
            self.assertTrue(reaper["lines"][key])

    def test_settings_match_the_skript_options(self):
        text = npcs.NPC_SKRIPT.read_text(encoding="utf-8")
        settings = self.config["settings"]
        for key in ("confirm-seconds", "reach", "near-blocks"):
            self.assertIn(f"{key}: {settings[key]}", text)
        self.assertIn(f"every {settings['ensure-seconds']} seconds:", text)
        self.assertIn("# ensure-seconds: %s" % settings["ensure-seconds"], text)

    def test_skript_uses_the_grave_payment_functions(self):
        text = npcs.NPC_SKRIPT.read_text(encoding="utf-8")
        for name in ("oldestGraveId", "reclaimCooling", "reclaimCharge", "reclaimCost"):
            self.assertIn(name, text)
        for kind in npcs.ENTITIES:
            phrase = "spawn a " + kind.replace("_", " ") + " at {_loc}"
            self.assertIn(phrase, text)
        for item in npcs.HELMETS + npcs.CHESTS + npcs.HANDS:
            self.assertIn(f'is "{item}"', text)

    def test_only_survival_has_the_npc_script(self):
        self.assertTrue(npcs.NPC_SKRIPT.is_file())
        for server in ("classic", "rpg", "lobby", "creative", "test", "proxy"):
            other = ROOT / "servers" / server / "plugins" / "Skript" / "scripts" / "bellcraft-npcs.sk"
            self.assertFalse(other.exists(), other)

    def test_rejects_a_broken_entry(self):
        broken = {
            "settings": dict(self.config["settings"]),
            "npcs": {
                "grim-reaper": dict(self.config["npcs"]["grim-reaper"]),
                "Bad Id": {"name": "x"},
            },
        }
        broken["npcs"]["grim-reaper"]["entity"] = "armor_stand"
        broken["npcs"]["grim-reaper"]["dialogue"] = ['he said "no"']
        errors = npcs.validate(broken)
        self.assertTrue(any("entity must be one of" in error for error in errors))
        self.assertTrue(any("quotes" in error for error in errors))
        self.assertTrue(any("lowercase" in error for error in errors))

    def test_write_roundtrip_is_stable(self):
        text = npcs.NPC_SKRIPT.read_text(encoding="utf-8")
        self.assertEqual(npcs.write_registry(text, self.config), text)


class GraveScriptTests(unittest.TestCase):
    def setUp(self):
        self.text = npcs.GRAVE_SKRIPT.read_text(encoding="utf-8")

    def test_prices_stay_configurable_and_unchanged(self):
        self.assertIn("reclaim-per-tier: 20", self.text)
        self.assertIn("reclaim-cooldown-minutes: 30", self.text)
        self.assertIn("reclaim-keeps-xp: true", self.text)
        self.assertIn("reclaim-radius: 40", self.text)

    def test_reclaim_command_uses_the_shared_charge(self):
        self.assertIn("function reclaimCharge", self.text)
        self.assertIn("function oldestGraveId", self.text)
        self.assertIn("reclaimCharge(player, {_id}, {_cost})", self.text)
        self.assertIn("The Reclaimer only works at spawn", self.text)
        self.assertIn("Grim Reaper", self.text)


if __name__ == "__main__":
    unittest.main()
