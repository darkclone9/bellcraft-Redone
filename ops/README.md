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

The deploy key's `authorized_keys` line (user `ghdeploy`):
`restrict,command="sudo -n /usr/local/sbin/bellcraft-deploy" ssh-ed25519 ...`

Install: `sudo install -o root -g root -m 755 <file> /usr/local/sbin/`; for sudoers always check
with `sudo visudo -cf <file>` before `install -m 440`.

Repo secrets used by the workflows: `BELLCRAFT_DEPLOY_KEY` (private key), `BELLCRAFT_KNOWN_HOSTS`,
`BELLCRAFT_HOST`, `CLAUDE_CODE_OAUTH_TOKEN`.
