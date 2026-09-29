# Working on Bellcraft

## The loop

1. **Issue first.** Every bug or feature gets an issue (use the templates). Put it on the board.
   Collaborators' issues get a plan from Claude automatically; add the `needs-plan` label to ask again.
2. **Branch + PR.** Change files under `servers/<server>/`. Keep a PR to one topic. Say in the PR
   which server(s) it touches and whether it needs a reload or restart.
   Or comment `@claude implement this` on the issue and review the branch it makes.
3. **Test on a dev backend when it matters.** Ask someone with server access to bring up `rpg`
   (`sudo /opt/bellcraft/bin/bellcraft-dev up rpg`), deploy there with *Actions → Deploy to servers →
   Run workflow → rpg*, and read the boot log. New Skript scripts **must** be boot-tested - Skript
   hides parse errors on reload.
4. **Merge = deploy.** Merging to `main` installs the changed files on the live server(s).
   Skript scripts reload by themselves; for other plugins run their reload command or restart the
   server (check players online first). The run summary lists what changed and what needs a reload.
5. **Close the issue** with a note on how it was verified in game.

## Rules

- **This repo is public.** Never commit a password, token, key or webhook. Files with `<<REDACTED>>`
  are edited on the server only; the deploy refuses them.
- Never commit plugin jars or paid assets - only our own config.
- Don't remove the `REDACTED` markers or hand-edit `servers/REDACTED.txt`; the sync regenerates it.
- If you changed something live over SSH, it will come back as a "Sync from live servers" commit
  within 6 hours. Prefer changing it through a PR.
- Deleting a file in git deletes it on the server at the next deploy (a backup is kept).
- Backups of everything a deploy overwrote: `/opt/bellcraft/_backups/deploy/<timestamp>/`.
  Nightly full backups: `/opt/backups/bellcraft/`.

## Server access (trusted developers)

The owner adds you with `sudo bellcraft-add-dev <username> "<your ssh public key>"`.
You get a normal account (not root) in group `bellcraft-dev`; see "Working on the live box" in
[CLAUDE.md](CLAUDE.md) for what it can do. Removing: `sudo bellcraft-add-dev --remove <username>`.
