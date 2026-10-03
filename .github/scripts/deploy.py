#!/usr/bin/env python3
"""Ship changed files under servers/<name>/ to the live box, one server at a time.

Push to main:       deploys what changed between the push's before and after commits.
workflow_dispatch:  re-sends every file of the chosen server (identical contents are not rewritten,
                    but ownership is repaired; this is how to put a server back in line with main).

The server end is ops/bellcraft-deploy, reached through a restricted SSH key that can run nothing else.
It installs only text config, refuses files still holding <<REDACTED>>, backs up whatever it overwrites,
and sk-reloads changed Skript scripts. It never restarts a server. There is no rsync step. Ownership is
enforced on the server for every server: each installed file, and every directory from that server's
root down to the file, is left owned by minecraft:minecraft. Unchanged files are not rewritten, but
their ownership is repaired when they are part of the upload.
"""
import io, os, subprocess, sys, tarfile
from collections import defaultdict

SERVERS = ['proxy', 'lobby', 'survival', 'creative', 'classic', 'rpg', 'test']
HOST = os.environ['BELLCRAFT_HOST']
SSH = ['ssh', '-i', os.path.expanduser('~/.ssh/deploy'), '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
       '-o', 'StrictHostKeyChecking=yes', f'ghdeploy@{HOST}']


def git(*args):
    return subprocess.run(['git', *args], check=True, capture_output=True, text=True).stdout


def changes():
    """{server: (set_of_changed_paths, set_of_deleted_paths)} with repo-relative paths."""
    out = defaultdict(lambda: (set(), set()))
    if os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch':
        srv = os.environ['INPUT_SERVER']
        for p in git('ls-files', f'servers/{srv}/').splitlines():
            out[srv][0].add(p)
        return out
    before, after = os.environ['BEFORE'], os.environ['AFTER']
    if set(before) == {'0'}:
        sys.exit('First push to a new branch - use "Run workflow" to deploy a server explicitly.')
    for line in git('diff', '--name-status', '--no-renames', before, after, '--', 'servers/').splitlines():
        status, path = line.split('\t', 1)
        parts = path.split('/')
        if len(parts) < 3 or parts[1] not in SERVERS:
            continue
        (out[parts[1]][1] if status == 'D' else out[parts[1]][0]).add(path)
    return out


def main():
    plan = changes()
    summary = ['## Deploy', '']
    failed = False
    for srv in SERVERS:
        if srv not in plan:
            continue
        changed, deleted = plan[srv]
        redacted = {p for p in changed if b'<<REDACTED>>' in open(p, 'rb').read()}
        for p in sorted(redacted):
            print(f'::warning file={p}::Not deployed: this file holds <<REDACTED>> secrets, so it can only be '
                  f'changed on the server. The next live sync will put the server copy back in git.')
        changed = changed - redacted
        if not changed and not deleted:
            summary += [f'### {srv} ⚠️', f'Skipped {len(redacted)} redacted file(s); nothing else to deploy.', '']
            continue
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode='w') as tar:
            for p in sorted(changed):
                tar.add(p, arcname=p, recursive=False)
            if deleted:
                prefix = f'servers/{srv}/'
                data = '\n'.join(p[len(prefix):] for p in sorted(deleted)).encode()
                info = tarfile.TarInfo(f'{prefix}.deploy-delete')
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        print(f'::group::{srv}: {len(changed)} changed, {len(deleted)} deleted')
        r = subprocess.run(SSH + [f'apply {srv}'], input=buf.getvalue(), capture_output=True)
        text = (r.stdout + r.stderr).decode('utf-8', 'replace')
        print(text)
        print('::endgroup::')
        summary += [f'### {srv} ' + ('✅' if r.returncode == 0 else '❌'), '```', text.strip(), '```', '']
        if r.returncode != 0:
            failed = True
            print(f'::error title=Deploy to {srv}::Some files were refused or the deploy failed - see the log.')
    if len(summary) == 2:
        summary.append('Nothing under servers/ changed.')
    with open(os.environ.get('GITHUB_STEP_SUMMARY', os.devnull), 'a') as f:
        f.write('\n'.join(summary) + '\n')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
