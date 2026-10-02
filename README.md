# Bellcraft Redone

Configuration, scripts and tooling for the **Bellcraft** Minecraft network (`bellcraft.online`),
and the place to report, plan, and collect behind-the-scenes system work and bug fixes.

- **Found a bug or want a feature?** [Open an issue](../../issues/new/choose). When a team member opens
  one, Claude reads it and posts a plan; comment `@claude implement this` to have it open a branch.
- **Want to change the server?** Read [CONTRIBUTING.md](CONTRIBUTING.md), then [CLAUDE.md](CLAUDE.md)
  for how the servers are laid out and the traps that have already bitten us.

## Layout

```
servers/<server>/     live config of each server (text only, secrets redacted)
  proxy lobby survival classic creative rpg test
ops/                  the tools installed on the server box (deploy receiver, exporter, dev accounts)
.github/workflows/    deploy on merge, sync from live, config validation, Claude planner
```

| Server | Join from the lobby | Purpose |
|---|---|---|
| survival | Realm Portal → RPG Survival | Classes, skills, quests, zones, towns, economy |
| classic | Realm Portal → Classic Survival | Plain survival, no class system |
| build (`servers/creative`) | Realm Portal → Creative | Creative copy of the RPG survival world |
| rpg, test | - | Dev backends for testing |

## Automation

| Workflow | When | What |
|---|---|---|
| Deploy to servers | push to `main` touching `servers/**`, or run by hand | installs changed files on the live servers, reloads Skript |
| Sync from live servers | every 6 h, or run by hand | commits whatever changed on the servers outside git |
| Validate configs | PRs and pushes | changed YAML/JSON/TOML must parse |
| Claude issue planner | issue opened by a collaborator, or `needs-plan` label | posts a plan comment |
| Claude | `@claude` in a comment | answers, or implements on a `claude/*` branch |
