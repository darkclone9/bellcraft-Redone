# Bellcraft - notes for Claude and for developers

Bellcraft (`bellcraft.online`) is a Minecraft network: a Velocity proxy in front of several Paper 26.2
backends, with Bedrock crossplay through Geyser/Floodgate. This repo holds the **text configuration**
of every server and is the way changes reach them. Read this file before planning or changing anything.

## Where things run

One Linux box runs the whole Minecraft stack under `/opt/bellcraft/<server>`, each a systemd unit
`bellcraft-<server>`, running as user `minecraft`.

| Repo folder | Velocity name | What it is |
|---|---|---|
| `servers/proxy` | - | Velocity 4.2 proxy. Geyser + Floodgate (Bedrock), MCXboxBroadcast, LuckPerms, TAB, vMessage, VelocityDiscord |
| `servers/lobby` | `lobby` | Hub. GUIPlus "Realm Portal" menu (`/guiplus:hub`) sends players to the other servers |
| `servers/survival` | `survival` | **RPG survival**: MMOCore classes, skills, quests, MythicMobs, Nexo items, zone levels, Towny, economy |
| `servers/classic` | `classic` | **Classic survival** (added 2026-09-29): same QoL plugins, *no* MMOCore/MythicLib/Nexo/classes. Own world, inventories and economy |
| `servers/creative` | `build` | Creative copy of the survival world. Players build in creative; inventories stay on this server. Not the BellcraftBuild plot grid (`ops/bellcraft-creative-world`) |
| `servers/rpg`, `servers/test` | `rpg`, `test` | **Dev backends**, normally stopped. Use them to test before touching live servers |

The websites (join.bellcraft.online, the radio) live on a different host and are **not** in this repo.

## How a change reaches a server

1. Edit files under `servers/<server>/` on a branch, open a PR. CI parses changed YAML/JSON/TOML.
2. **Merging to `main` deploys.** `.github/workflows/deploy.yml` sends the changed files to the box,
   where `ops/bellcraft-deploy` installs them (backing up what it overwrites).
3. Changed Skript scripts are `sk reload`ed automatically. **Everything else needs a plugin reload
   or a restart** - the deploy summary lists which plugin folders changed. The deploy never restarts.
4. Every 6 hours `sync-live.yml` exports the live config back into `main`, so edits made directly on
   the server show up as "Sync from live servers" commits.

What can be deployed: text config under `config/`, `plugins/`, `world/datapacks/`, plus
`bukkit.yml`, `spigot.yml`, `commands.yml`, `help.yml`, `permissions.yml`, `velocity.toml`.
**Not** deployable from git: plugin jars, `server.properties`, `start.sh`, worlds, player data,
databases, the generated resource pack.

**`<<REDACTED>>`** marks a credential the export removed (DB passwords, bot tokens, RCON, license
keys). A file containing it is refused by the deploy - change those files on the server itself.
Never put a real secret in this repo: **it is public.** `servers/REDACTED.txt` lists those files.

## Traps that have already cost real time

### Console / RCON
- **RCON only shows legacy-text replies.** Anything a plugin sends as an Adventure Component
  (Skript messages, Paper's "Unknown command", `/list`, most modern plugins) comes back **empty**.
  To test whether a command exists: `bukkit:help <name>` - an *empty* reply means it exists.
- `pause-when-empty-seconds` must be `-1`: a paused empty server silently drops every RCON command.
- Nexo regenerates its resource pack on boot and blocks the main thread ~30 s; RCON is dropped then.
- `bellcraft-dev up` can report a false "Done" from the previous boot's log - check `latest.log`'s
  first line against the clock. Paper timestamps have no date.
- CMI commands over RCON often return nothing and do not apply; prefer doing it via Skript.

### Skript (2.16.1)
- **Parse errors only appear in the console at boot**, not on `sk reload` (that report goes to the
  invisible RCON sender). An invalid structure is silently skipped: `on right click air:` was never
  valid, so for months the class-armor right-click block did not exist. Test new scripts by booting
  the `rpg` backend and reading its log.
- A single bad alias silently kills a whole `command /x:` (e.g. `/char`, `/stats` were already taken).
- Biomes stringify with spaces (`dripstone caves`) - normalise with `replace all " " with "_"`.
- Functions have no varargs; `is not a X, Y or Z` is ambiguous - write the positive form.
- `on armor change:` + `new armor item` exist and fire for every equip path.
- Skript health values are in hearts; use `max health attribute of e` for raw attribute values.

### MMOCore / MythicLib (classes, skills)
- Class stat names come from MMOCore's `StatType` (`MAGIC_DAMAGE`, not MythicLib's `MAGICAL_DAMAGE`).
  Unknown stats are ignored with no log line (`HEALING_RATING` and `saturation` were dead for months).
- Every MythicLib skill needs **both** `source: default:<HANDLER>` and a `triggers:` block.
  `source: mythicmobs:X` never resolves (load order).
- `potion`, `stat`, `heal`, `damage` target the *trigger's* entity: every self-buff needs `target=caster`.
- Particle names must be modern Bukkit enums (`INSTANT_EFFECT`, not `SPELL_INSTANT`) or nothing draws.
- `force-class-selection` must stay `false`; MMOCore has rewritten it to `true` on reload.
- MMOCore parses **every** file in its folders - never leave `*.bak` copies inside plugin dirs.
- MMOProfiles is installed but deliberately shares all data (`synced-data` all false).
- Balance framework: 20 attribute points at base + 4.0/level for every class, one primary damage stat
  each, throughput targeted at level 50 after cooldown reduction.

### Zones and mobs (survival)
- Level zones are distance rings from 0,0: Hearthvale 1-10 (0-1000), Thornwold March 10-20
  (1000-2200), Ashenmoor Expanse 20-32 (2200-3600), Stormhollow Frontier 32-45 (3600-5000),
  The Sundered Wilds 45-60 (5000+). Harsh biomes +8. Nether = Cinderreach 55-70, deep dark =
  The Hollowing Choir 70-80, End = The Pale Crown 80-99. The same table is duplicated in
  `bellcraft-mobxp.sk`, `bellcraft-graves.sk`, `bellcraft-mobscale.sk` and the `bellcraft_zones`
  datapack - change them together.
- MythicMobs' `WorldScaling` does **not** scale vanilla mobs here. `bellcraft-mobscale.sk` does:
  health set at spawn, damage multiplied per hit, by zone level. Named/plugin-spawned mobs are skipped.
- `killmythicmob` quest objectives take `name="<id>"`, not `type=`.
- The deep dark has no vanilla spawn list: MythicMobs spawns there need `Action: ADD`.

### Items, packs, models
- Nexo builds the resource pack and obfuscates asset names inside `pack.zip`; verify by following
  the item JSON's model path, not by grepping for the item id.
- MythicArmors must keep `disable-shader: false` and `vulkan-3d-armor: false`, or the 3D armor breaks.
- A ModelEngine `hitbox` bone's pivot Y is the eye height.

### Files and permissions
- Files on the server must be owned by `minecraft`. Root-owned files break plugins that save their
  own config (GUIPlus failed to save a menu this way). The deploy tool installs as `minecraft`.
- Never `cp` over a loaded jar; copy to a temp name and `mv` it over.
- The build server's permissions are scoped with LuckPerms context `server=build`; classic uses
  `server=classic`; lobby/survival use `global`.

## Working on the live box (trusted developers)

Developers with an account (`ops/bellcraft-add-dev`) can SSH in. They are not root, but can:
`sudo -u minecraft -i` (edit server files), `sudo systemctl restart bellcraft-<server>`,
`sudo journalctl --no-pager -u bellcraft-<server>`, `sudo bellcraft-rcon <server> <command>`,
`sudo /opt/bellcraft/bin/bellcraft-dev status|up|down <rpg|test>`.
Check `python3 /opt/bellcraft/bin/mcstatus.py 127.0.0.1 25565` (players online) before restarting
anything; restarting the proxy disconnects everyone. Anything edited live is pulled back into git
by the next sync - commit through the repo when you can.

## Planning checklist

- Which server(s)? RPG survival and classic are separate on purpose - a class fix must not leak into classic.
- Does it need a reload or a restart after merge? Say which.
- Can it be tested on `rpg`/`test` first? (They are stopped by default; RAM is limited.)
- Does the change touch a `<<REDACTED>>` file? Then it cannot be done through git.
