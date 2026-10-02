#!/usr/bin/env python3
"""Ownership guarantees for ops/bellcraft-deploy.

Run as root (the deploy script chowns):

    sudo python3 ops/test_deploy_ownership.py

Files are chowned to the unprivileged `ubuntu` account so the test does not need a minecraft user.
"""
import importlib.util
import io
import os
import pwd
import stat
import subprocess
import tarfile
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_loader = SourceFileLoader('bellcraft_deploy', str(ROOT / 'ops' / 'bellcraft-deploy'))
_spec = importlib.util.spec_from_loader('bellcraft_deploy', _loader)
mod = importlib.util.module_from_spec(_spec)
_loader.exec_module(mod)


def _ubuntu():
    ent = pwd.getpwnam('ubuntu')
    return ent.pw_uid, ent.pw_gid


def _ids(path):
    st = os.lstat(path)
    return st.st_uid, st.st_gid, stat.S_IMODE(st.st_mode)


def _tar(members):
    """members: {arcname: bytes}"""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w') as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class OwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.geteuid() != 0:
            raise unittest.SkipTest('chown tests must run as root')
        cls.uid, cls.gid = _ubuntu()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = os.path.join(self.tmp.name, 'srv')
        os.mkdir(self.base)
        self.logs = []
        self._old_log = mod.log
        self._old_root = mod.ROOT
        self._old_ids = mod.minecraft_ids
        self._old_stdin = mod.sys.stdin
        mod.log = self.logs.append
        mod.ROOT = self.tmp.name
        mod.minecraft_ids = lambda: (self.uid, self.gid)

    def tearDown(self):
        mod.log = self._old_log
        mod.ROOT = self._old_root
        mod.minecraft_ids = self._old_ids
        mod.sys.stdin = self._old_stdin

    def test_new_file_and_directories_are_owned_and_modes_ignore_umask(self):
        old = os.umask(0o077)
        try:
            mod.install_file(self.base, 'plugins/GUIPlus/CustomGuis/info-panel-p2.yml', b'id: p2\n', self.uid, self.gid)
        finally:
            os.umask(old)
        leaf = os.path.join(self.base, 'plugins/GUIPlus/CustomGuis/info-panel-p2.yml')
        self.assertEqual(_ids(leaf), (self.uid, self.gid, 0o644))
        self.assertEqual(Path(leaf).read_bytes(), b'id: p2\n')
        self.assertFalse(os.path.exists(leaf + '.deploy-tmp'))
        self.assertEqual(_ids(self.base)[:2], (self.uid, self.gid))
        for rel in ('plugins', 'plugins/GUIPlus', 'plugins/GUIPlus/CustomGuis'):
            self.assertEqual(_ids(os.path.join(self.base, rel)), (self.uid, self.gid, 0o755))
        mod.install_file(self.base, 'bukkit.yml', b'settings:\n', self.uid, self.gid)
        self.assertEqual(_ids(os.path.join(self.base, 'bukkit.yml')), (self.uid, self.gid, 0o644))

    def test_existing_directory_mode_is_kept_and_sibling_is_untouched(self):
        plugin = os.path.join(self.base, 'plugins', 'GUIPlus')
        os.makedirs(plugin)
        os.chmod(plugin, 0o700)
        sibling = os.path.join(plugin, 'untouched.yml')
        with open(sibling, 'wb') as f:
            f.write(b'leave me\n')
        os.chown(sibling, 0, 0)
        mod.install_file(self.base, 'plugins/GUIPlus/menu.yml', b'menu\n', self.uid, self.gid)
        self.assertEqual(_ids(plugin), (self.uid, self.gid, 0o700))
        self.assertEqual(_ids(os.path.join(plugin, 'menu.yml')), (self.uid, self.gid, 0o644))
        self.assertEqual(_ids(sibling)[:2], (0, 0))
        self.assertEqual(Path(sibling).read_bytes(), b'leave me\n')

    def test_repair_keeps_content_mode_and_mtime(self):
        rel = 'plugins/GUIPlus/CustomGuis/info-panel-p2.yml'
        path = os.path.join(self.base, rel)
        os.makedirs(os.path.dirname(path))
        os.chmod(os.path.dirname(path), 0o750)
        with open(path, 'wb') as f:
            f.write(b'id: p2\n')
        os.chmod(path, 0o640)
        os.chown(path, 0, 0)
        before = os.stat(path).st_mtime_ns
        n = mod.repair_ownership(self.base, rel, self.uid, self.gid)
        self.assertGreaterEqual(n, 1)
        st = os.lstat(path)
        self.assertEqual((st.st_uid, st.st_gid, stat.S_IMODE(st.st_mode)), (self.uid, self.gid, 0o640))
        self.assertEqual(st.st_mtime_ns, before)
        self.assertEqual(Path(path).read_bytes(), b'id: p2\n')
        self.assertEqual(stat.S_IMODE(os.lstat(os.path.dirname(path)).st_mode), 0o750)
        # group-only mismatch is still repaired
        os.chown(path, self.uid, 0)
        self.assertTrue(mod.own(path, self.uid, self.gid))
        self.assertEqual(_ids(path)[:2], (self.uid, self.gid))

    def test_symlink_directory_is_refused_and_target_stays_root(self):
        outside = os.path.join(self.tmp.name, 'outside')
        os.mkdir(outside)
        os.symlink(outside, os.path.join(self.base, 'plugins'))
        with self.assertRaises(mod.Refused):
            mod.install_file(self.base, 'plugins/GUIPlus/menu.yml', b'x\n', self.uid, self.gid)
        self.assertEqual(os.lstat(outside).st_uid, 0)
        self.assertEqual(list(os.listdir(outside)), [])

    def _apply(self, server, members):
        mod.sys.stdin = type('S', (), {'buffer': io.BytesIO(_tar(members))})()
        mod.apply(server)

    def test_apply_repairs_unchanged_files_on_lobby_creative_and_proxy(self):
        body = b'id: info-panel-p2\n'
        rel = 'plugins/GUIPlus/CustomGuis/info-panel-p2.yml'
        for server in ('lobby', 'creative', 'proxy', 'survival', 'classic', 'rpg', 'test'):
            path = os.path.join(self.tmp.name, server, rel)
            os.makedirs(os.path.dirname(path))
            with open(path, 'wb') as f:
                f.write(body)
            os.chown(path, 0, 0)
            os.chown(os.path.dirname(path), 0, 0)
            before = os.stat(path).st_mtime_ns
            self.logs.clear()
            self._apply(server, {f'servers/{server}/{rel}': body})
            summary = '\n'.join(self.logs)
            self.assertIn('0 changed', summary, summary)
            self.assertIn('ownership repaired', summary, summary)
            self.assertEqual(_ids(path)[:2], (self.uid, self.gid))
            self.assertEqual(_ids(os.path.dirname(path))[:2], (self.uid, self.gid))
            self.assertEqual(_ids(os.path.join(self.tmp.name, server))[:2], (self.uid, self.gid))
            self.assertEqual(os.stat(path).st_mtime_ns, before)
            self.assertEqual(Path(path).read_bytes(), body)

    def test_apply_changed_file_is_minecraft_owned_and_root_sibling_is_not(self):
        server = 'lobby'
        base = os.path.join(self.tmp.name, server, 'plugins', 'GUIPlus')
        os.makedirs(base)
        sibling = os.path.join(base, 'other.yml')
        with open(sibling, 'wb') as f:
            f.write(b'root\n')
        os.chown(sibling, 0, 0)
        rel = 'plugins/GUIPlus/menu.yml'
        self._apply(server, {f'servers/{server}/{rel}': b'new\n'})
        installed = os.path.join(self.tmp.name, server, rel)
        self.assertEqual(_ids(installed), (self.uid, self.gid, 0o644))
        self.assertEqual(Path(installed).read_bytes(), b'new\n')
        self.assertEqual(_ids(base)[:2], (self.uid, self.gid))
        self.assertEqual(_ids(sibling)[:2], (0, 0))
        self.assertFalse(os.path.exists(installed + '.deploy-tmp'))

    def test_apply_refuses_redacted_without_chowning(self):
        server = 'proxy'
        rel = 'plugins/Geyser-Velocity/config.yml'
        path = os.path.join(self.tmp.name, server, rel)
        os.makedirs(os.path.dirname(path))
        with open(path, 'wb') as f:
            f.write(b'password: real\n')
        os.chown(path, 0, 0)
        os.chown(os.path.dirname(path), 0, 0)
        with self.assertRaises(SystemExit) as caught:
            self._apply(server, {f'servers/{server}/{rel}': b'password: <<REDACTED>>\n'})
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(_ids(path)[:2], (0, 0))
        self.assertEqual(_ids(os.path.dirname(path))[:2], (0, 0))
        self.assertEqual(Path(path).read_bytes(), b'password: real\n')


class FixOwnershipScriptTests(unittest.TestCase):
    """The one-time host repair, pointed at a scratch tree instead of /opt/bellcraft."""

    created_user = False
    created_group = False

    @classmethod
    def setUpClass(cls):
        if os.geteuid() != 0:
            raise unittest.SkipTest('chown tests must run as root')
        if subprocess.run(['getent', 'group', 'minecraft'], capture_output=True).returncode != 0:
            subprocess.run(['groupadd', 'minecraft'], check=True)
            cls.created_group = True
        if subprocess.run(['getent', 'passwd', 'minecraft'], capture_output=True).returncode != 0:
            subprocess.run(['useradd', '-r', '-M', '-g', 'minecraft', 'minecraft'], check=True)
            cls.created_user = True

    @classmethod
    def tearDownClass(cls):
        if cls.created_user and subprocess.run(['getent', 'passwd', 'minecraft'], capture_output=True).returncode == 0:
            subprocess.run(['userdel', 'minecraft'], check=True)
        # userdel removes a primary group that has no other members.
        if cls.created_group and subprocess.run(['getent', 'group', 'minecraft'], capture_output=True).returncode == 0:
            subprocess.run(['groupdel', 'minecraft'], check=True)

    def test_script_repairs_every_server_and_skips_symlink_targets(self):
        uid = pwd.getpwnam('minecraft').pw_uid
        gid = grp_minecraft()
        with tempfile.TemporaryDirectory() as tmp:
            outside = os.path.join(tmp, 'outside')
            os.mkdir(outside)
            secret = os.path.join(outside, 'secret')
            with open(secret, 'wb') as f:
                f.write(b'secret\n')
            os.chown(secret, 0, 0)
            for server, rel in (
                ('lobby', 'plugins/GUIPlus/info-panel-p2.yml'),
                ('creative', 'plugins/BellcraftBuild/config.yml'),
                ('proxy', 'plugins/Geyser-Velocity/config.yml'),
            ):
                path = os.path.join(tmp, server, rel)
                os.makedirs(os.path.dirname(path))
                with open(path, 'wb') as f:
                    f.write(b'root-owned\n')
                os.chown(path, 0, 0)
            # user minecraft, group root: still wrong
            group_wrong = os.path.join(tmp, 'lobby', 'plugins', 'GUIPlus', 'group-wrong.yml')
            with open(group_wrong, 'wb') as f:
                f.write(b'group\n')
            os.chown(group_wrong, uid, 0)
            os.symlink(secret, os.path.join(tmp, 'lobby', 'plugins', 'escape'))
            script = ROOT / 'ops' / 'bellcraft-fix-ownership'
            first = subprocess.run(['bash', str(script), tmp], check=True, capture_output=True, text=True)
            self.assertIn('lobby: chown minecraft:minecraft', first.stdout)
            self.assertIn('creative: chown minecraft:minecraft', first.stdout)
            self.assertIn('proxy: chown minecraft:minecraft', first.stdout)
            self.assertIn('survival: skip', first.stdout)
            for server, rel in (
                ('lobby', 'plugins/GUIPlus/info-panel-p2.yml'),
                ('creative', 'plugins/BellcraftBuild/config.yml'),
                ('proxy', 'plugins/Geyser-Velocity/config.yml'),
            ):
                st = os.lstat(os.path.join(tmp, server, rel))
                self.assertEqual((st.st_uid, st.st_gid), (uid, gid))
            st = os.lstat(group_wrong)
            self.assertEqual((st.st_uid, st.st_gid), (uid, gid))
            self.assertEqual(os.lstat(secret).st_uid, 0)
            self.assertTrue(os.path.islink(os.path.join(tmp, 'lobby', 'plugins', 'escape')))
            second = subprocess.run(['bash', str(script), tmp], check=True, capture_output=True, text=True)
            self.assertIn('lobby: already minecraft:minecraft', second.stdout)
            self.assertIn('creative: already minecraft:minecraft', second.stdout)
            self.assertIn('proxy: already minecraft:minecraft', second.stdout)


def grp_minecraft():
    import grp
    return grp.getgrnam('minecraft').gr_gid


if __name__ == '__main__':
    unittest.main()
