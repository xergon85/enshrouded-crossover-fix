"""Installer safety checks; use temporary fixtures, never the real runtime."""
# SPDX-License-Identifier: Apache-2.0
import argparse
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'runtime', Path(__file__).resolve().parents[1] / 'scripts/runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class InstallerTests(unittest.TestCase):
    def test_isolation_destination_and_post_sign_hash(self):
        with tempfile.TemporaryDirectory(prefix='enshrouded-installer-') as temporary:
            base = Path(temporary).resolve()
            app, bottle, lib = base / 'Original app.app', base / 'Steam bottle', base / 'driver.dylib'
            for file in [app / runtime.WINE, app / runtime.DRIVER,
                         bottle / 'cxbottle.conf', bottle / runtime.STEAM]:
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(b'original')
            lib.write_bytes(b'MVK_DIAG_REFLECT_TESS_OUTPUT_STRIDES fixture')
            unrelated = base / 'Existing directory'
            unrelated.mkdir()
            (unrelated / 'keep.txt').write_text('preserve')
            args = argparse.Namespace(app=str(app), bottle=str(bottle), library=str(lib),
                                      home=str(unrelated), dry_run=False)
            calls = []

            def simulated_tool(argv, **kwargs):
                argv = [str(x) for x in argv]
                calls.append(argv)
                if argv[0] == '/usr/bin/ditto':
                    runtime.shutil.copytree(argv[-2], argv[-1])
                if argv[0] == 'codesign' and '--force' in argv:
                    file = Path(argv[-1]) / runtime.DRIVER
                    file.write_bytes(file.read_bytes() + b' signed')

            with patch.object(runtime, 'run', side_effect=simulated_tool), \
                    patch.object(runtime, 'ensure_stopped'):
                with self.assertRaisesRegex(ValueError, 'new or empty'):
                    runtime.install(args)
                self.assertFalse(calls)
                self.assertEqual((unrelated / 'keep.txt').read_text(), 'preserve')
                args.home = str(base / 'New runtime')
                runtime.install(args)
                cfg, installed, _ = runtime.load(args)
                self.assertNotEqual(cfg['driver_sha256'], cfg['source_driver_sha256'])
                self.assertEqual(cfg['driver_sha256'], runtime.sha(installed / runtime.DRIVER))
                ditto = next(c for c in calls if c[0] == '/usr/bin/ditto')
                self.assertEqual(ditto[-2:], [str(app), str(installed)])
                self.assertEqual((app / runtime.DRIVER).read_bytes(), b'original')
                with self.assertRaisesRegex(ValueError, 'new or empty'):
                    runtime.install(args)
                (installed / runtime.DRIVER).write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, 'Driver changed'):
                    runtime.load(args)


if __name__ == '__main__':
    unittest.main()
