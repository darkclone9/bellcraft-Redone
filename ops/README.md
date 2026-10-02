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

Repo secrets used by the workflows: `BELLCRAFT_DEPLOY_KEY` (private key), `BELLCRAFT_KNOWN_HOSTS`,
`BELLCRAFT_HOST`, `CLAUDE_CODE_OAUTH_TOKEN`.

## Creative world snapshot

`bellcraft-creative-world` copies survival's overworld, nether and end onto the creative
(`build`) server so players can build there in creative mode. It does not deploy with the
workflow. Install it by hand, then run it on the box after the creative config from git is
on disk. See the script's header for the exact command.

The copy is **one-time**. Creative builds diverge as soon as someone places a block, and a
later refresh deletes that work. Do not put it on a timer. Run it again only on purpose, with
`--replace`, which archives the current creative worlds first. Survival's live world is only
read, and only after `save-off` / `save-all flush` (or not at all, when the source is a backup).
Player inventories are not part of the copy and are never written back.
