#!/usr/bin/env python3
"""Safety tests for ops/bellcraft-creative-world. No network and no /opt/bellcraft."""
import gzip, importlib.machinery, os, shutil, struct, subprocess, tempfile, unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
loader = importlib.machinery.SourceFileLoader('creative_world', os.path.join(ROOT, 'bellcraft-creative-world'))
cw = loader.load_module()


def nbt_name(name):
    raw = name.encode()
    return struct.pack('>H', len(raw)) + raw


def nbt_compound(name, body):
    return bytes([cw.TAG_COMPOUND]) + nbt_name(name) + body + bytes([cw.TAG_END])


def nbt_int(name, value):
    return bytes([cw.TAG_INT]) + nbt_name(name) + struct.pack('>i', value)


def nbt_byte(name, value):
    return bytes([cw.TAG_BYTE]) + nbt_name(name) + bytes([value & 0xFF])


def nbt_string(name, value):
    raw = value.encode()
    return bytes([cw.TAG_STRING]) + nbt_name(name) + struct.pack('>H', len(raw)) + raw


def sample_level_nbt():
    nested = nbt_compound('WorldGenSettings', nbt_int('seed', 123456))
    data = nbt_int('GameType', 0) + nbt_byte('Difficulty', 2) + nbt_string('LevelName', 'world') + nested
    return nbt_compound('', nbt_compound('Data', data))


def sample_level_nbt_26():
    """26.1 stores difficulty as a string under difficulty_settings, not a byte."""
    settings = nbt_string('difficulty', 'hard') + nbt_byte('locked', 1)
    data = nbt_int('GameType', 0) + nbt_compound('difficulty_settings', settings) + nbt_string('LevelName', 'world')
    return nbt_compound('', nbt_compound('Data', data))


def write_level(path, nbt=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, 'wb') as fh:
        fh.write(nbt if nbt is not None else sample_level_nbt())


def write_file(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


def creative_configs(root):
    write_file(os.path.join(root, 'bukkit.yml'), 'settings:\n  allow-end: true\n')
    write_file(os.path.join(root, 'plugins', 'BellcraftBuild', 'config.yml'), 'role: live\nplots:\n  world: plots\n')
    write_file(os.path.join(root, 'plugins', 'CMI', 'Settings', 'DataBaseInfo.yml'), 'storage:\n  method: sqlite\n')
    write_file(os.path.join(root, 'server.properties'),
               'gamemode=survival\nforce-gamemode=false\nallow-nether=false\n'
               'rcon.password=<<REDACTED>>\nrcon.port=25578\nmotd=Bellcraft build server\n')


class CreativeWorldTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='creative-world-')
        self.survival = os.path.join(self.tmp, 'survival')
        self.creative = os.path.join(self.tmp, 'creative')
        self.archive = os.path.join(self.tmp, 'archive')
        os.makedirs(self.survival)
        os.makedirs(self.creative)
        creative_configs(self.creative)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _source_world(self, name='world'):
        base = os.path.join(self.survival, name)
        write_level(os.path.join(base, 'level.dat'))
        write_file(os.path.join(base, 'region', 'r.0.0.mca'), 'TERRAIN')
        write_file(os.path.join(base, 'playerdata', 'survival.dat'), 'SURVIVAL-INV')
        write_file(os.path.join(base, 'stats', 'survival.json'), '{}')
        write_file(os.path.join(base, 'uid.dat'), 'same-uid')
        write_file(os.path.join(base, 'session.lock'), 'lock')
        return base

    def _run(self, **kwargs):
        params = dict(
            source=self.survival,
            creative_root=self.creative,
            survival_root=self.survival,
            archive_root=self.archive,
            replace=False,
            dry_run=False,
            allow_live=True,
            creative_active=False,
            survival_active=False,
        )
        params.update(kwargs)
        return cw.run_copy(**params)

    def test_patch_level_dat_keeps_other_tags(self):
        raw = sample_level_nbt()
        patched = cw.patch_level_dat_nbt(raw)
        self.assertEqual(len(patched), len(raw))
        self.assertEqual(cw.read_level_fields(patched), {'GameType': 1, 'Difficulty': 0})
        self.assertIn(b'world', patched)
        self.assertIn(b'WorldGenSettings', patched)

    def test_patch_level_dat_26_rewrites_difficulty_string(self):
        raw = sample_level_nbt_26()
        patched = cw.patch_level_dat_nbt(raw)
        self.assertNotEqual(len(patched), len(raw))
        self.assertEqual(cw.read_level_fields(patched), {'GameType': 1, 'difficulty': 'peaceful'})
        self.assertIn(b'world', patched)
        self.assertIn(b'locked', patched)
        self.assertNotIn(b'hard', patched)

    def test_properties_keep_secrets_and_rcon_port(self):
        text = open(os.path.join(self.creative, 'server.properties')).read()
        updated = cw.set_properties(text, cw.PROPERTY_UPDATES)
        self.assertIn('rcon.password=<<REDACTED>>', updated)
        self.assertIn('rcon.port=25578', updated)
        self.assertIn('gamemode=creative', updated)
        self.assertIn('force-gamemode=true', updated)
        self.assertIn('allow-nether=true', updated)
        self.assertNotIn('rcon.port=25575', updated)

    def test_copy_skips_playerdata_and_does_not_touch_survival(self):
        self._source_world()
        write_level(os.path.join(self.survival, 'world_nether', 'level.dat'))
        write_file(os.path.join(self.survival, 'world_nether', 'region', 'n.mca'), 'NETHER')
        before = open(os.path.join(self.survival, 'world', 'region', 'r.0.0.mca'), 'rb').read()
        src_stat = os.stat(os.path.join(self.survival, 'world', 'region', 'r.0.0.mca'))
        result = self._run()
        self.assertEqual(result['action'], 'copied')
        self.assertEqual(result['worlds'], ['world', 'world_nether'])
        dest_region = os.path.join(self.creative, 'world', 'region', 'r.0.0.mca')
        self.assertEqual(open(dest_region, 'rb').read(), before)
        self.assertFalse(os.path.samestat(src_stat, os.stat(dest_region)))
        self.assertFalse(os.path.exists(os.path.join(self.creative, 'world', 'playerdata')))
        self.assertFalse(os.path.exists(os.path.join(self.creative, 'world', 'stats')))
        self.assertFalse(os.path.exists(os.path.join(self.creative, 'world', 'uid.dat')))
        self.assertFalse(os.path.exists(os.path.join(self.creative, 'world', 'session.lock')))
        self.assertEqual(open(os.path.join(self.survival, 'world', 'playerdata', 'survival.dat')).read(), 'SURVIVAL-INV')
        self.assertEqual(open(os.path.join(self.survival, 'world', 'region', 'r.0.0.mca'), 'rb').read(), before)
        with gzip.open(os.path.join(self.creative, 'world', 'level.dat'), 'rb') as fh:
            fields = cw.read_level_fields(fh.read())
        self.assertEqual(fields, {'GameType': 1, 'Difficulty': 0})
        with gzip.open(os.path.join(self.survival, 'world', 'level.dat'), 'rb') as fh:
            self.assertEqual(cw.read_level_fields(fh.read())['GameType'], 0)
        props = open(os.path.join(self.creative, 'server.properties')).read()
        self.assertIn('force-gamemode=true', props)
        self.assertIn('rcon.password=<<REDACTED>>', props)
        self.assertIn('rcon.port=25578', props)

    def test_replace_keeps_creative_inventory_and_archives_old_terrain(self):
        self._source_world()
        write_level(os.path.join(self.creative, 'world', 'level.dat'))
        write_file(os.path.join(self.creative, 'world', 'region', 'old.mca'), 'PLOT')
        write_file(os.path.join(self.creative, 'world', 'playerdata', 'builder.dat'), 'CREATIVE-INV')
        self._run(replace=True)
        self.assertEqual(open(os.path.join(self.creative, 'world', 'playerdata', 'builder.dat')).read(), 'CREATIVE-INV')
        self.assertFalse(os.path.exists(os.path.join(self.creative, 'world', 'playerdata', 'survival.dat')))
        self.assertEqual(open(os.path.join(self.creative, 'world', 'region', 'r.0.0.mca')).read(), 'TERRAIN')
        archived = [n for n in os.listdir(self.archive)]
        self.assertEqual(len(archived), 1)
        self.assertEqual(open(os.path.join(self.archive, archived[0], 'world', 'region', 'old.mca')).read(), 'PLOT')

    def test_second_run_does_not_refresh(self):
        self._source_world()
        self._run()
        write_file(os.path.join(self.survival, 'world', 'region', 'r.0.0.mca'), 'CHANGED')
        result = self._run()
        self.assertEqual(result['action'], 'kept')
        self.assertEqual(open(os.path.join(self.creative, 'world', 'region', 'r.0.0.mca')).read(), 'TERRAIN')

    def test_symlink_aborts_and_leaves_creative_world(self):
        self._source_world()
        os.symlink('/etc/hostname', os.path.join(self.survival, 'world', 'region', 'linked.mca'))
        write_file(os.path.join(self.creative, 'world', 'kept.txt'), 'stay')
        with self.assertRaises(RuntimeError):
            self._run(replace=True)
        self.assertEqual(open(os.path.join(self.creative, 'world', 'kept.txt')).read(), 'stay')
        self.assertTrue(os.path.islink(os.path.join(self.survival, 'world', 'region', 'linked.mca')))
        self.assertFalse(os.path.exists(os.path.join(self.creative, 'world.partial')))

    def test_playerdata_symlink_rolls_back_to_old_world(self):
        self._source_world()
        write_level(os.path.join(self.creative, 'world', 'level.dat'))
        write_file(os.path.join(self.creative, 'world', 'sentinel.txt'), 'old-world')
        os.makedirs(os.path.join(self.creative, 'world', 'playerdata'))
        os.symlink('/etc/hostname', os.path.join(self.creative, 'world', 'playerdata', 'linked.dat'))
        with self.assertRaises(RuntimeError):
            self._run(replace=True)
        self.assertEqual(open(os.path.join(self.creative, 'world', 'sentinel.txt')).read(), 'old-world')
        self.assertTrue(os.path.islink(os.path.join(self.creative, 'world', 'playerdata', 'linked.dat')))

    def test_refuses_live_source_without_live_mode(self):
        self._source_world()
        with self.assertRaises(SystemExit):
            self._run(allow_live=False)

    def test_refuses_overlapping_trees_and_archive_inside_survival(self):
        self._source_world()
        with self.assertRaises(SystemExit):
            self._run(source=self.creative, allow_live=False, survival_root=os.path.join(self.tmp, 'other'))
        with self.assertRaises(SystemExit):
            self._run(archive_root=os.path.join(self.survival, 'archive'))

    def test_refuses_plot_generator_and_shared_database_and_survival_plugins(self):
        self._source_world()
        write_file(os.path.join(self.creative, 'bukkit.yml'), 'worlds:\n  world:\n    generator: BellcraftBuild\n')
        with self.assertRaises(SystemExit):
            self._run()
        self.assertFalse(os.path.exists(os.path.join(self.creative, 'world', 'level.dat')))
        creative_configs(self.creative)
        write_file(os.path.join(self.creative, 'plugins', 'BellcraftBuild', 'config.yml'), 'plots:\n  world: world\n')
        with self.assertRaises(SystemExit):
            self._run()
        creative_configs(self.creative)
        write_file(os.path.join(self.creative, 'plugins', 'CMI', 'Settings', 'DataBaseInfo.yml'), 'storage:\n  method: mysql\n')
        with self.assertRaises(SystemExit):
            self._run()
        creative_configs(self.creative)
        os.makedirs(os.path.join(self.creative, 'plugins', 'MMOCore'))
        with self.assertRaises(SystemExit):
            self._run()

    def test_refuses_to_delete_under_survival(self):
        with self.assertRaises(RuntimeError):
            cw.safe_rmtree(self.survival, self.survival)

    def test_backup_picker_skips_live_tree_and_prefers_newest(self):
        live = os.path.join(self.tmp, 'live', 'survival')
        old = os.path.join(self.tmp, 'backups', 'old', 'survival')
        new = os.path.join(self.tmp, 'backups', 'new', 'survival')
        write_level(os.path.join(live, 'world', 'level.dat'))
        write_level(os.path.join(old, 'world', 'level.dat'))
        write_level(os.path.join(new, 'world', 'level.dat'))
        os.utime(os.path.join(old, 'world', 'level.dat'), (1, 1))
        os.utime(os.path.join(new, 'world', 'level.dat'), (2, 2))
        found, _archives = cw.find_survival_backups(os.path.join(self.tmp, 'backups'), live)
        self.assertEqual(os.path.realpath(found[0]), os.path.realpath(new))
        found_wide, _archives = cw.find_survival_backups(self.tmp, live)
        self.assertTrue(all(os.path.realpath(p) != os.path.realpath(live) for p in found_wide))
        self.assertEqual(os.path.realpath(found_wide[0]), os.path.realpath(new))

    def test_worldguard_regions_are_archived_not_copied_from_survival(self):
        self._source_world()
        write_file(os.path.join(self.survival, 'plugins', 'WorldGuard', 'worlds', 'world', 'regions.yml'), 'TOWN')
        write_file(os.path.join(self.creative, 'plugins', 'WorldGuard', 'worlds', 'world', 'regions.yml'), 'PLOT')
        self._run()
        self.assertFalse(os.path.exists(os.path.join(self.creative, 'plugins', 'WorldGuard', 'worlds', 'world')))
        self.assertTrue(os.path.exists(os.path.join(self.survival, 'plugins', 'WorldGuard', 'worlds', 'world', 'regions.yml')))
        archived = os.listdir(self.archive)[0]
        self.assertEqual(
            open(os.path.join(self.archive, archived, 'WorldGuard', 'world', 'regions.yml')).read(),
            'PLOT',
        )

    def test_dry_run_writes_nothing(self):
        self._source_world()
        write_file(os.path.join(self.creative, 'world', 'level.dat'), 'existing')
        snapshot = []
        for dirpath, _dirs, files in os.walk(self.tmp):
            for name in files:
                snapshot.append(os.path.join(dirpath, name))
        before = {p: open(p, 'rb').read() for p in snapshot}
        result = self._run(dry_run=True)
        self.assertEqual(result['action'], 'dry-run')
        self.assertTrue(result['exists'])
        self.assertFalse(result['replace'])
        for path, data in before.items():
            self.assertEqual(open(path, 'rb').read(), data)

    def test_save_on_runs_when_copy_fails_and_not_when_save_off_fails(self):
        calls = []

        def rcon(server, command):
            calls.append(command)
            if command == 'save-all flush':
                raise RuntimeError('disk')
            return 'ok'

        with self.assertRaises(RuntimeError):
            cw.with_saves_paused(rcon, lambda: '', lambda: None, sleep=0)
        self.assertEqual(calls, ['save-off', 'save-all flush', 'save-on'])

        calls.clear()

        def rcon_off(_server, command):
            calls.append(command)
            return None

        with self.assertRaises(RuntimeError):
            cw.with_saves_paused(rcon_off, lambda: '', lambda: None, sleep=0)
        self.assertEqual(calls, ['save-off'])

    def test_live_copy_pauses_saves_and_always_resumes(self):
        self._source_world()
        calls = []
        log = {'text': ''}

        def rcon(_server, command):
            calls.append(command)
            if command == 'save-all flush':
                log['text'] += 'Saved the game\n'
                return ''
            return 'ok'

        self._run(allow_live=True, survival_active=True, rcon=rcon, read_log=lambda: log['text'])
        self.assertEqual(calls[0], 'save-off')
        self.assertIn('save-all flush', calls)
        self.assertEqual(calls[-1], 'save-on')
        self.assertTrue(os.path.isfile(os.path.join(self.creative, 'world', 'region', 'r.0.0.mca')))

    def _modern_source(self):
        """Paper 26.1 layout: one world folder, dimensions inside it, players/ instead of playerdata."""
        base = os.path.join(self.survival, 'world')
        write_level(os.path.join(base, 'level.dat'), sample_level_nbt_26())
        write_file(os.path.join(base, 'dimensions', 'minecraft', 'overworld', 'region', 'r.0.0.mca'), 'OVERWORLD')
        write_file(os.path.join(base, 'dimensions', 'minecraft', 'the_nether', 'region', 'n.mca'), 'NETHER')
        write_file(os.path.join(base, 'dimensions', 'minecraft', 'the_end', 'region', 'e.mca'), 'END')
        write_file(os.path.join(base, 'dimensions', 'minecraft', 'the_nether', 'paper-world.yml'), 'survival-nether-paper')
        write_file(os.path.join(base, 'dimensions', 'minecraft', 'overworld', 'data', 'minecraft', 'raids.dat'), 'RAID')
        write_file(os.path.join(base, 'data', 'minecraft', 'scoreboard.dat'), 'SCORES')
        write_file(os.path.join(base, 'data', 'minecraft', 'maps', '1.dat'), 'MAP')
        write_file(os.path.join(base, 'data', 'minecraft', 'world_border.dat'), 'BORDER')
        write_file(os.path.join(base, 'players', 'data', 'survival.dat'), 'SURVIVAL-INV')
        write_file(os.path.join(base, 'players', 'stats', 'survival.json'), '{"surv":1}')
        write_file(os.path.join(base, 'players', 'advancements', 'survival.json'), '{"adv":1}')
        write_file(os.path.join(base, 'playerdata', 'legacy.dat'), 'OLD-INV')
        return base

    def test_modern_layout_copies_dimensions_and_skips_players(self):
        self._modern_source()
        write_level(os.path.join(self.creative, 'world', 'level.dat'))
        write_file(os.path.join(self.creative, 'world', 'region', 'old.mca'), 'PLOT')
        write_file(os.path.join(self.creative, 'world', 'players', 'data', 'builder.dat'), 'CREATIVE-INV')
        write_file(os.path.join(self.creative, 'world', 'players', 'stats', 'builder.json'), '{"b":1}')
        write_file(os.path.join(self.creative, 'world', 'players', 'advancements', 'builder.json'), '{"a":1}')
        write_file(os.path.join(self.creative, 'world', 'playerdata', 'builder.dat'), 'CREATIVE-OLD')
        write_file(os.path.join(self.creative, 'world_nether', 'region', 'old-nether.mca'), 'OLD-NETHER')
        write_file(os.path.join(self.creative, 'world_the_end', 'region', 'old-end.mca'), 'OLD-END')
        write_file(os.path.join(self.creative, 'plugins', 'WorldGuard', 'worlds', 'world_nether', 'regions.yml'), 'PLOT-NETHER')
        result = self._run(replace=True)
        self.assertEqual(result['worlds'], ['world'])
        world = os.path.join(self.creative, 'world')
        self.assertEqual(open(os.path.join(world, 'dimensions', 'minecraft', 'overworld', 'region', 'r.0.0.mca')).read(), 'OVERWORLD')
        self.assertEqual(open(os.path.join(world, 'dimensions', 'minecraft', 'the_nether', 'region', 'n.mca')).read(), 'NETHER')
        self.assertEqual(open(os.path.join(world, 'dimensions', 'minecraft', 'the_end', 'region', 'e.mca')).read(), 'END')
        self.assertEqual(open(os.path.join(world, 'data', 'minecraft', 'maps', '1.dat')).read(), 'MAP')
        self.assertEqual(open(os.path.join(world, 'data', 'minecraft', 'world_border.dat')).read(), 'BORDER')
        self.assertFalse(os.path.exists(os.path.join(world, 'data', 'minecraft', 'scoreboard.dat')))
        self.assertFalse(os.path.exists(os.path.join(world, 'dimensions', 'minecraft', 'overworld', 'data', 'minecraft', 'raids.dat')))
        self.assertFalse(os.path.exists(os.path.join(world, 'dimensions', 'minecraft', 'the_nether', 'paper-world.yml')))
        self.assertFalse(os.path.exists(os.path.join(world, 'players', 'data', 'survival.dat')))
        self.assertFalse(os.path.exists(os.path.join(world, 'playerdata', 'legacy.dat')))
        self.assertEqual(open(os.path.join(world, 'players', 'data', 'builder.dat')).read(), 'CREATIVE-INV')
        self.assertEqual(open(os.path.join(world, 'players', 'stats', 'builder.json')).read(), '{"b":1}')
        self.assertEqual(open(os.path.join(world, 'players', 'advancements', 'builder.json')).read(), '{"a":1}')
        self.assertEqual(open(os.path.join(world, 'playerdata', 'builder.dat')).read(), 'CREATIVE-OLD')
        self.assertEqual(open(os.path.join(self.survival, 'world', 'players', 'data', 'survival.dat')).read(), 'SURVIVAL-INV')
        self.assertFalse(os.path.exists(os.path.join(self.creative, 'world_nether')))
        self.assertFalse(os.path.exists(os.path.join(self.creative, 'world_the_end')))
        self.assertFalse(os.path.exists(os.path.join(self.creative, 'plugins', 'WorldGuard', 'worlds', 'world_nether')))
        archived = os.listdir(self.archive)
        self.assertEqual(len(archived), 1)
        saved = os.path.join(self.archive, archived[0])
        self.assertEqual(open(os.path.join(saved, 'world_nether', 'region', 'old-nether.mca')).read(), 'OLD-NETHER')
        self.assertEqual(open(os.path.join(saved, 'world_the_end', 'region', 'old-end.mca')).read(), 'OLD-END')
        self.assertEqual(open(os.path.join(saved, 'WorldGuard', 'world_nether', 'regions.yml')).read(), 'PLOT-NETHER')
        with gzip.open(os.path.join(world, 'level.dat'), 'rb') as fh:
            self.assertEqual(cw.read_level_fields(fh.read()), {'GameType': 1, 'difficulty': 'peaceful'})
        with gzip.open(os.path.join(self.survival, 'world', 'level.dat'), 'rb') as fh:
            self.assertEqual(cw.read_level_fields(fh.read())['difficulty'], 'hard')

    def test_modern_layout_without_nether_folder_does_not_fail(self):
        self._modern_source()
        result = self._run()
        self.assertEqual(result['action'], 'copied')
        self.assertEqual(result['worlds'], ['world'])
        self.assertFalse(os.path.exists(os.path.join(self.creative, 'world_nether')))
        self.assertTrue(os.path.isfile(os.path.join(
            self.creative, 'world', 'dimensions', 'minecraft', 'the_nether', 'region', 'n.mca')))
        self.assertFalse(os.path.exists(os.path.join(self.creative, 'world', 'players')))

    def test_players_symlink_rolls_back_to_old_world(self):
        self._modern_source()
        write_level(os.path.join(self.creative, 'world', 'level.dat'))
        write_file(os.path.join(self.creative, 'world', 'sentinel.txt'), 'old-world')
        os.makedirs(os.path.join(self.creative, 'world', 'players', 'data'))
        os.symlink('/etc/hostname', os.path.join(self.creative, 'world', 'players', 'data', 'linked.dat'))
        with self.assertRaises(RuntimeError):
            self._run(replace=True)
        self.assertEqual(open(os.path.join(self.creative, 'world', 'sentinel.txt')).read(), 'old-world')
        self.assertTrue(os.path.islink(os.path.join(self.creative, 'world', 'players', 'data', 'linked.dat')))

    def _write_nightly(self, archive, with_symlink=False):
        tree = os.path.join(self.tmp, 'nightly-src')
        if os.path.isdir(tree):
            shutil.rmtree(tree)
        write_level(os.path.join(tree, 'survival', 'world', 'level.dat'), sample_level_nbt_26())
        write_file(os.path.join(tree, 'survival', 'world', 'dimensions', 'minecraft', 'the_nether', 'region', 'n.mca'), 'NETHER')
        write_file(os.path.join(tree, 'survival', 'world', 'players', 'data', 'survival.dat'), 'SURVIVAL-INV')
        write_file(os.path.join(tree, 'survival', 'plugins', 'Towny', 'data.yml'), 'TOWN')
        if with_symlink:
            region = os.path.join(tree, 'survival', 'world', 'region')
            os.makedirs(region, exist_ok=True)
            os.symlink('/etc/hostname', os.path.join(region, 'linked.mca'))
        subprocess.check_call(['tar', '--zstd', '-C', tree, '-cf', archive, 'survival'])

    def test_backup_archive_extracts_world_only(self):
        archive = os.path.join(self.tmp, 'survival_2026-10-02_05-15.tar.zst')
        self._write_nightly(archive)
        dest = cw.extract_backup(archive, parent=self.tmp)
        self.assertTrue(os.path.isfile(os.path.join(dest, 'world', 'level.dat')))
        self.assertEqual(
            open(os.path.join(dest, 'world', 'dimensions', 'minecraft', 'the_nether', 'region', 'n.mca')).read(),
            'NETHER',
        )
        self.assertFalse(os.path.exists(os.path.join(dest, 'world', 'players')))
        self.assertFalse(os.path.exists(os.path.join(dest, 'plugins')))
        self.assertTrue(dest.startswith(self.tmp))
        copied = self._run(source=dest, allow_live=False, survival_root=self.survival)
        self.assertEqual(copied['worlds'], ['world'])
        self.assertEqual(
            open(os.path.join(self.creative, 'world', 'dimensions', 'minecraft', 'the_nether', 'region', 'n.mca')).read(),
            'NETHER',
        )
        self.assertFalse(os.path.exists(os.path.join(self.creative, 'world', 'players')))
        bare_src = os.path.join(self.tmp, 'bare-src')
        write_level(os.path.join(bare_src, 'world', 'level.dat'))
        write_file(os.path.join(bare_src, 'world', 'dimensions', 'minecraft', 'the_end', 'region', 'e.mca'), 'END')
        write_file(os.path.join(bare_src, 'world', 'players', 'data', 'survival.dat'), 'SURVIVAL-INV')
        bare = os.path.join(self.tmp, 'survival_bare.tar.zst')
        subprocess.check_call(['tar', '--zstd', '-C', bare_src, '-cf', bare, 'world'])
        bare_dest = cw.extract_backup(bare, parent=self.tmp)
        self.assertTrue(os.path.isfile(os.path.join(bare_dest, 'world', 'level.dat')))
        self.assertEqual(
            open(os.path.join(bare_dest, 'world', 'dimensions', 'minecraft', 'the_end', 'region', 'e.mca')).read(),
            'END',
        )
        self.assertFalse(os.path.exists(os.path.join(bare_dest, 'world', 'players')))

    def test_main_dry_run_archive_does_not_extract(self):
        archive = os.path.join(self.tmp, 'survival_2026-10-02_05-15.tar.zst')
        self._write_nightly(archive)
        rc = cw.main([
            'copy', '--from', 'backup', '--dry-run', '--source', archive,
            '--creative-root', self.creative, '--survival-root', self.survival,
            '--archive-root', self.archive, '--backup-root', self.tmp,
        ])
        self.assertEqual(rc, 0)
        self.assertFalse(any(name.startswith('bellcraft-creative-world-') for name in os.listdir(self.tmp)))
        self.assertFalse(os.path.exists(os.path.join(self.creative, 'world', 'level.dat')))
        write_file(os.path.join(self.creative, 'world', 'level.dat'), 'existing')
        rc = cw.main([
            'copy', '--from', 'backup', '--source', archive,
            '--creative-root', self.creative, '--survival-root', self.survival,
            '--archive-root', self.archive, '--backup-root', self.tmp,
        ])
        self.assertEqual(rc, 0)
        self.assertEqual(open(os.path.join(self.creative, 'world', 'level.dat')).read(), 'existing')
        self.assertIn('gamemode=creative', open(os.path.join(self.creative, 'server.properties')).read())
        self.assertFalse(any(name.startswith('bellcraft-creative-world-') for name in os.listdir(self.tmp)))

    def test_backup_archive_refuses_symlink_and_small_disk(self):
        archive = os.path.join(self.tmp, 'survival_linked.tar.zst')
        self._write_nightly(archive, with_symlink=True)
        with self.assertRaises(SystemExit):
            cw.extract_backup(archive, parent=self.tmp)
        self.assertFalse(any(name.startswith('bellcraft-creative-world-') for name in os.listdir(self.tmp)))
        plain = os.path.join(self.tmp, 'survival_plain.tar.zst')
        self._write_nightly(plain)
        with self.assertRaises(SystemExit) as ctx:
            cw.extract_backup(plain, parent=self.tmp, disk_free=lambda _path: 1)
        self.assertIn('not enough disk', str(ctx.exception))

    def test_backup_picker_uses_newest_survival_archive_name(self):
        backups = os.path.join(self.tmp, 'backups')
        os.makedirs(backups)
        older = os.path.join(backups, 'survival_2026-10-01_05-15.tar.zst')
        newer = os.path.join(backups, 'survival_2026-10-02_05-15.tar.zst')
        other = os.path.join(backups, 'creative_2026-10-02_05-15.tar.zst')
        for path in (older, newer, other):
            open(path, 'wb').close()
        os.utime(older, (1, 1))
        os.utime(newer, (3, 3))
        os.utime(other, (4, 4))
        _found, archives = cw.find_survival_backups(backups, self.survival)
        nightly = [path for path in archives if os.path.basename(path).startswith('survival')]
        self.assertEqual(nightly[0], newer)
        self.assertIn(other, archives)
        self.assertGreater(os.path.getmtime(other), os.path.getmtime(newer))

    def test_perms_do_not_touch_worlds(self):
        calls = []

        def rcon(server, command):
            calls.append((server, command))
            return ''

        cw.apply_perms(rcon, 'survival')
        self.assertEqual([c[0] for c in calls], ['survival', 'survival'])
        self.assertIn('velocity.command.server.build', calls[0][1])
        self.assertFalse(any('gamemode' in c[1] for c in calls))


if __name__ == '__main__':
    unittest.main()
