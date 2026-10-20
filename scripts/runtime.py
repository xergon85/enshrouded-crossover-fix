#!/usr/bin/env python3
"""Install a separate CrossOver copy, check it, and launch Enshrouded."""
# SPDX-License-Identifier: Apache-2.0
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOME = Path.home() / 'Library/Application Support/Enshrouded-CrossOver-Fix'
DRIVER = Path('Contents/SharedSupport/CrossOver/lib/x86_64/libMoltenVK.dylib')
WINE = Path('Contents/SharedSupport/CrossOver/bin/wine')
STEAM = Path('drive_c/Program Files (x86)/Steam/steam.exe')
FLAGS = {
    'MVK_PERF_OPTIMIZE_PRECISE_MATH': '1',
    'MVK_DIAG_REFLECT_TESS_OUTPUT_STRIDES': '1',
    'MVK_DIAG_DISABLE_RESIDENCY_SET': '0',
    'MVK_CONFIG_LIVE_CHECK_ALL_RESOURCES': '0',
    'MVK_DIAG_PRESERVE_EXPLICIT_BARRIERS': '0',
    'MVK_DIAG_RECYCLE_RESOURCE_USE_NODES': '0',
    'MVK_DIAG_FLAT_RESOURCE_USE_MAP': '0',
    'MVK_DIAG_SKIP_REDUNDANT_LIVE_CHECKS': '0',
    'MVK_DIAG_TRACE_METAL_ALLOCATIONS': '0',
    'MVK_DIAG_LOG_MEMORY': '0',
    'MVK_DIAG_LOG_PRESENT_RATE': '0',
    'MVK_CONFIG_LOG_LEVEL': '1',
}


def run(args, **kw):
    return subprocess.run([str(x) for x in args], check=True, **kw)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def existing(path):
    p = Path(path).expanduser().resolve(strict=True)
    return p


def ensure_stopped():
    # Wine executable names may not appear in the short Darwin process name.
    p = subprocess.run(['/usr/bin/pgrep', '-if', '[s]team[.]exe|[e]nshrouded[.]exe'],
                       stdout=subprocess.DEVNULL)
    if p.returncode == 0:
        raise ValueError('Exit Enshrouded and Steam normally, then retry.')
    if p.returncode != 1:
        raise ValueError('Cannot inspect running Steam/game processes.')


def install(args):
    app, lib, bottle = existing(args.app), existing(args.library), existing(args.bottle)
    home = Path(args.home).expanduser().resolve()
    target = home / 'CrossOver-Enshrouded.app'
    config = home / 'installation.json'
    for item in [app / WINE, app / DRIVER, bottle / 'cxbottle.conf', bottle / STEAM]:
        if not item.is_file():
            raise ValueError(f'Missing required file: {item}')
    if home == app or app in home.parents or home == bottle or bottle in home.parents:
        raise ValueError('Runtime destination must be outside the source app and Steam bottle.')
    if home.exists() and (not home.is_dir() or any(home.iterdir())):
        raise ValueError('Runtime destination must be a new or empty directory. Choose a new --home.')
    run(['lipo', lib, '-verify_arch', 'x86_64'])
    # A stock driver cannot implement this private opt-in flag.
    if b'MVK_DIAG_REFLECT_TESS_OUTPUT_STRIDES' not in lib.read_bytes():
        raise ValueError('Driver does not contain the tessellation fix flag.')
    digest = sha(lib)
    print(f'Copy: {app}\nTo:   {target}\nBottle: {bottle}\nDriver SHA-256: {digest}', flush=True)
    if args.dry_run:
        print('Dry run complete. No files changed.')
        return
    ensure_stopped()
    home.mkdir(parents=True, exist_ok=True)
    # Never inherit Finder/FileProvider extended attributes into the new runtime.
    run(['/usr/bin/ditto', '--norsrc', '--noextattr', '--noqtn', app, target])
    shutil.copyfile(lib, target / DRIVER)
    run(['codesign', '--force', '--deep', '--preserve-metadata=entitlements', '--sign', '-', target])
    run(['codesign', '--verify', '--deep', '--strict', target])
    cfg = {'runtime': str(target), 'bottle': str(bottle), 'driver_sha256': sha(target / DRIVER),
           'source_driver_sha256': digest,
           'source_app': str(app), 'log': str(home / 'enshrouded-play.log')}
    config.write_text(json.dumps(cfg, indent=2) + '\n')
    print(f'Installed. Check with: python3 "{ROOT / "scripts/runtime.py"}" check --home "{home}"')


def load(args):
    config = Path(args.home).expanduser().resolve() / 'installation.json'
    cfg = json.loads(config.read_text())
    app, bottle = Path(cfg['runtime']), Path(cfg['bottle'])
    for item in [app / WINE, app / DRIVER, bottle / 'cxbottle.conf', bottle / STEAM]:
        if not item.is_file():
            raise ValueError(f'Missing required file: {item}')
    if sha(app / DRIVER) != cfg['driver_sha256']:
        raise ValueError('Driver changed since installation. Rebuild/reinstall in a new --home.')
    return cfg, app, bottle


def check_or_play(args):
    cfg, app, bottle = load(args)
    if args.command == 'check':
        ensure_stopped()
        run(['codesign', '--verify', '--deep', '--strict', app])
        run([app / WINE, '--bottle', bottle, '--no-update', '--wait-children',
             '--debugmsg=-all', 'cmd.exe', '/c', 'echo', 'Enshrouded-runtime-OK'])
        print('Driver hash, signature, bottle, Steam and Windows command verified.')
        return
    ensure_stopped()
    env = os.environ.copy()
    # Diagnostic/HUD settings inherited from an interactive shell can alter the run.
    for key in list(env):
        if key.startswith('MVK_DIAG_') or key in ('MTL_DEBUG_LAYER', 'MTL_HUD_ENABLED'):
            del env[key]
    env.update(FLAGS)
    log = Path(cfg['log'])
    print(f'Starting Enshrouded. Runtime log: {log}', flush=True)
    with log.open('w') as output:
        p = subprocess.run([str(app / WINE), '--bottle', str(bottle), '--no-update',
                            '--wait-children', '--debugmsg=-all',
                            r'C:\Program Files (x86)\Steam\steam.exe', '-applaunch', '1203620'],
                           env=env, stdout=output, stderr=subprocess.STDOUT)
    sys.exit(p.returncode)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    i = sub.add_parser('install', help='Create and sign a separate CrossOver app copy')
    i.add_argument('--app', required=True, help='Existing CrossOver .app')
    i.add_argument('--library', required=True, help='Patched x86_64 libMoltenVK.dylib')
    i.add_argument('--bottle', required=True, help='Full path of existing Steam bottle')
    i.add_argument('--dry-run', action='store_true')
    for item in [i, sub.add_parser('check'), sub.add_parser('play')]:
        item.add_argument('--home', default=str(DEFAULT_HOME), help='Isolated runtime directory')
    args = p.parse_args()
    if platform.system() != 'Darwin':
        p.error('Requires macOS.')
    try:
        install(args) if args.command == 'install' else check_or_play(args)
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as e:
        p.exit(1, f'Error: {e}\n')


if __name__ == '__main__':
    main()
