#!/usr/bin/env python3
"""Render indirect tessellation probes using an explicitly selected MoltenVK."""
# SPDX-License-Identifier: Apache-2.0
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent


def run(command, **kw):
    return subprocess.run([str(x) for x in command], check=kw.pop('check', True), **kw)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--library', type=Path, required=True)
    p.add_argument('--headers', type=Path, required=True, help='Vulkan-Headers/include directory')
    p.add_argument('--source', type=Path, required=True, help='Patched MoltenVK checkout')
    p.add_argument('--results', type=Path, required=True, help='New directory for test logs/results')
    args = p.parse_args()
    args.results.mkdir(parents=True, exist_ok=False)
    args.results = args.results.resolve()
    env = os.environ.copy()
    # Start from the final, normal-residency configuration.
    for key in list(env):
        if key.startswith('MVK_') or key.startswith('MTL_'):
            del env[key]
    env.update(MVK_DIAG_REFLECT_TESS_OUTPUT_STRIDES='1', MTL_DEBUG_LAYER='1')
    results = []
    # Avoid FileProvider/signature issues with executable files in synced folders.
    with tempfile.TemporaryDirectory(prefix='enshrouded-tess-') as temporary:
        work = Path(temporary)
        library = work / 'libMoltenVK.dylib'
        shutil.copyfile(args.library.resolve(strict=True), library)
        run(['codesign', '--force', '--sign', '-', library])
        for source in ['tess-probe', 'tess-capacity-probe']:
            binary = work / source
            run(['xcrun', 'clang', '-arch', 'x86_64', '-O2', '-I', args.headers.resolve(),
                 HERE / 'fixtures' / (source + '.c'), library,
                 '-Wl,-rpath,' + str(work), '-o', binary])
            run(['codesign', '--force', '--sign', '-', binary])
            for mode in ['', 'indexed', 'indexed32']:
                name = source + '-' + (mode or 'nonindexed')
                r = run([binary] + ([mode] if mode else []), env=env,
                        capture_output=True, text=True, timeout=120, check=False)
                log = r.stdout + r.stderr
                (args.results / (name + '.log')).write_text(log)
                r.check_returncode()
                if 'PASS: indirect tessellation rendered expected green center pixel' not in log:
                    raise RuntimeError(f'Missing rendered-pixel success: {name}')
                if 'Tessellation output stride:' not in log:
                    raise RuntimeError(f'Fix was not exercised: {name}')
                results.append({'name': name, 'passed': True, 'normal_residency': True})
                print(name, 'PASS', flush=True)
        env['MVK_DIAG_REFLECT_TESS_OUTPUT_STRIDES'] = '0'
        r = run([work / 'tess-probe'], env=env, capture_output=True, text=True, timeout=120)
        if 'PASS: indirect tessellation rendered expected green center pixel' not in r.stdout:
            raise RuntimeError('Control did not render correctly')
        if 'Tessellation output stride:' in r.stderr:
            raise RuntimeError('Control unexpectedly enabled reflected sizing')
        (args.results / 'control.log').write_text(r.stdout + r.stderr)
        results.append({'name': 'control-disabled', 'passed': True, 'normal_residency': True})
        # Extract actual production helpers instead of maintaining a second implementation.
        production = (args.source / 'MoltenVK/MoltenVK/GPUObjects/MVKPipeline.mm').read_text()
        start = production.index('// Optional tessellation scratch sizing')
        end = production.index('#pragma mark - MVKPipelineLayout', start)
        harness = (HERE / 'fixtures/cache-harness.mm').read_text()
        at = harness.index('int main()')
        extracted = work / 'cache.mm'
        extracted.write_text(harness[:at] + production[start:end] + harness[at:])
        binary = work / 'cache-test'
        run(['xcrun', 'clang++', '-arch', 'x86_64', '-std=c++17', '-fno-objc-arc',
             extracted, '-framework', 'Metal', '-framework', 'Foundation', '-o', binary])
        run(['codesign', '--force', '--sign', '-', binary])
        env['MVK_DIAG_REFLECT_TESS_OUTPUT_STRIDES'] = '1'
        r = run([binary], env=env, capture_output=True, text=True, timeout=60)
        if 'PASS: production cache' not in r.stdout:
            raise RuntimeError('Cache helper probe did not pass')
        (args.results / 'cache.log').write_text(r.stdout + r.stderr)
        results.append({'name': 'production-cache-helpers', 'passed': True})
    (args.results / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    print('All 8 checks passed. Results:', args.results)


if __name__ == '__main__':
    main()
