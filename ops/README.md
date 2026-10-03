# ops/ - tools installed on the Minecraft box

These are copies of what runs on the server; install changes by hand (they are not deployed by the
workflow, on purpose - the deploy key must not be able to change its own rules).

| File | Installed at | Purpose |
|---|---|---|
| `bellcraft-deploy` | `/usr/local/sbin/` | The only program the GitHub deploy key can run (`export`, `apply <server>`, `status`) |
| `bellcraft-export` | `/usr/local/sbin/` | Streams the tracked, redacted config as a tar |
| `bellcraft-rcon` | `/usr/local/sbin/` | `bellcraft-rcon <server> <command>` without knowing RCON passwords |
| `bellcraft-add-dev` | `/usr/local/sbin/` | Add/remove a trusted developer's SSH account |
| `sudoers-bellcraft-dev` | `/etc/sudoers.d/bellcraft-dev` | What `bellcraft-dev` members and `ghdeploy` may run |
| `bellcraft-creative-world` | `/usr/local/sbin/` | Copy a consistent survival snapshot onto the creative server |

The deploy key's `authorized_keys` line (user `ghdeploy`):
`restrict,command="sudo -n /usr/local/sbin/bellcraft-deploy" ssh-ed25519 ...`

Install: `sudo install -o root -g root -m 755 <file> /usr/local/sbin/`; for sudoers always check
with `sudo visudo -cf <file>` before `install -m 440`.

## Deploy secrets

`.github/workflows/deploy.yml` reads three repository Actions secrets
(Settings → Secrets and variables → Actions). Set these names; do not put the values in git.

| Secret | Role |
|---|---|
| `BELLCRAFT_DEPLOY_KEY` | Private key for user `ghdeploy`, stored as the raw key text |
| `BELLCRAFT_KNOWN_HOSTS` | `known_hosts` line for that host (strict host-key checking is on) |
| `BELLCRAFT_HOST` | Host name or IP. `deploy.py` connects as `ghdeploy@<this>` on SSH port 22 |

`BELLCRAFT_KNOWN_HOSTS` must be the host key of `BELLCRAFT_HOST`. The workflow writes the key to
`~/.ssh/deploy` and the host key to `~/.ssh/known_hosts`, which is where `deploy.py` looks.

A push to `main` that touches `servers/**` deploys only the servers with changed files. Deploys
share the `bellcraft-deploy` concurrency group and wait their turn. The job never restarts a
server; the proxy keeps running.

Manual deploy: Actions → **Deploy to servers** → **Run workflow**, choose branch **main**, and
set `server` to one folder name: `proxy`, `lobby`, `survival`, `creative`, `classic`, `rpg`, or
`test` (`creative` is the build server). That re-sends every tracked file for that server; the
host skips files that already match. Leave `server` blank and the run stops before SSH.

## Creative world snapshot

`bellcraft-creative-world` copies survival's overworld, nether and end onto the creative
(`build`) server so players can build there in creative mode. It does not deploy with the
workflow. Install it by hand, then run it on the box after the creative config from git is
on disk. See the script's header for the exact command. Reading a nightly
`survival_*.tar.zst` needs the `zstd` program.

Paper 26.1 stores the nether and end inside `world/dimensions/minecraft/`. The script copies
that tree and also the older `world_nether` / `world_the_end` folders when those exist.
Player data is not copied: `world/players/` on 26.1, and `playerdata` / `stats` /
`advancements` on older worlds. `--replace` puts creative's own copies of those trees back.
`raids.dat` and `scoreboard.dat` are left behind (they name survival players). Map files
stay, so maps in chests still work. Creative's Multiverse entries stay `minecraft:the_nether`
and `minecraft:the_end`; `legacy-world-name` is the Bukkit name (`world_nether`,
`world_the_end`), not a separate folder.

The copy is **one-time**. Creative builds diverge as soon as someone places a block, and a
later refresh deletes that work. Do not put it on a timer. Run it again only on purpose, with
`--replace`, which archives the current creative worlds first. Survival's live world is only
read, and only after `save-off` / `save-all flush` (or not at all, when the source is a backup).
Player inventories are not part of the copy and are never written back. `--from backup` uses
the newest extracted `survival/` tree under the backup root if one exists, otherwise the
newest `survival_*.tar.zst`. Pass `--source` for a specific archive or an extracted directory.
