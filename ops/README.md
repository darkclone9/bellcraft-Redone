# ops/ - tools installed on the Minecraft box

These are copies of what runs on the server; install changes by hand (they are not deployed by the
workflow, on purpose - the deploy key must not be able to change its own rules).

| File | Installed at | Purpose |
|---|---|---|
| `bellcraft-deploy` | `/usr/local/sbin/` | The only program the GitHub deploy key can run (`export`, `apply <server>`, `status`). `apply` leaves files and their parent directories owned by `minecraft:minecraft` on every server |
| `bellcraft-fix-ownership` | `/usr/local/sbin/` | One-time (re-runnable) repair of paths not owned by `minecraft:minecraft`. Not for the deploy key |
| `bellcraft-export` | `/usr/local/sbin/` | Streams the tracked, redacted config as a tar |
| `bellcraft-rcon` | `/usr/local/sbin/` | `bellcraft-rcon <server> <command>` without knowing RCON passwords |
| `bellcraft-add-dev` | `/usr/local/sbin/` | Add/remove a trusted developer's SSH account |
| `sudoers-bellcraft-dev` | `/etc/sudoers.d/bellcraft-dev` | What `bellcraft-dev` members and `ghdeploy` may run |

The deploy key's `authorized_keys` line (user `ghdeploy`):
`restrict,command="sudo -n /usr/local/sbin/bellcraft-deploy" ssh-ed25519 ...`

Install: `sudo install -o root -g root -m 755 <file> /usr/local/sbin/`; for sudoers always check
with `sudo visudo -cf <file>` before `install -m 440`.

## One-time ownership repair

Deploys that ran as root, before `bellcraft-deploy` chowned what it wrote, left root-owned files
under the servers. Survival was repaired on 2026-09-29. Lobby, creative (the build server) and
proxy were still root-owned, and any server tree can be checked the same way. Plugin saves fail
until those paths are `minecraft:minecraft`.

Copy `ops/bellcraft-fix-ownership` to the box and install it with the others, then:

```bash
sudo bellcraft-fix-ownership
```

The same repair, with nothing to install, from a root shell (missing server directories are
skipped; symlinks are not followed; nothing is restarted):

```bash
sudo bash -c 'for s in proxy lobby survival creative classic rpg test; do
  d=/opt/bellcraft/$s
  [ -d "$d" ] || continue
  find "$d" -xdev \( ! -user minecraft -o ! -group minecraft \) ! -type l -exec chown minecraft:minecraft {} +
done'
```

Future deploys keep ownership only after the updated `bellcraft-deploy` is installed on the box.
The workflow does not install `ops/` (the deploy key must not be able to change its own rules).

Repo secrets used by the workflows: `BELLCRAFT_DEPLOY_KEY` (private key), `BELLCRAFT_KNOWN_HOSTS`,
`BELLCRAFT_HOST`, `CLAUDE_CODE_OAUTH_TOKEN`.
