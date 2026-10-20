# Reproduce the Enshrouded hammer-menu fix

## 1. Requirements and tested versions

The successful game test used:

| Component | Tested value |
|---|---|
| Mac | Mac mini, Apple M4, 24 GB unified memory |
| macOS | 26.6.2, build 25G83 |
| CrossOver | Preview 27.0.0.41073; app version 20261015 |
| Xcode / SDK | Xcode 26.3 / macOS SDK 26.2 |
| Runtime architecture | x86_64 under Rosetta |
| MoltenVK source | `5189f8de86ec365860f63bf1da736815cfaea5cd` |
| SPIRV-Cross | `aa217aeb6c9f0ace7a0ab233b28807edf45eb165` |
| Steam application | Enshrouded, `1203620` |

Other hardware, macOS releases and CrossOver versions need their own validation. Full Xcode is required; command line tools alone are insufficient. Python 3 and Git must be available in Terminal. Install Rosetta if prompted by macOS/CrossOver.

Use your existing Steam bottle and game installation. The instructions create an additional CrossOver application copy; they do not replace the installed CrossOver application. Close CrossOver's interface, Steam and Enshrouded before installing.

## 2. Build the source

Download or clone this repository, then open Terminal in its root. Use a local folder outside iCloud Drive/Desktop/Documents for build files. The script defaults to `~/Library/Caches/enshrouded-crossover-fix/`.

```bash
xcodebuild -version
xcrun --find clang
python3 --version
bash scripts/build.sh
```

The script creates a fresh build directory, checks out the exact MoltenVK commit, checks and applies both patches, fetches the dependencies pinned by that commit, and builds the macOS package for x86_64. It signs the output library locally and records patch hashes and the Xcode version. It refuses to overwrite an existing build directory.

For a predictable output location, choose a **new** path:

```bash
WORK="$HOME/Library/Caches/enshrouded-crossover-fix/reproduction-01" \
  bash scripts/build.sh
```

Allow time for dependency downloads and compilation. The final message prints the output directory. Set a convenience variable to that actual directory:

```bash
BUILD="$HOME/Library/Caches/enshrouded-crossover-fix/reproduction-01"
LIB="$BUILD/dist/libMoltenVK.dylib"
cat "$BUILD/dist/SHA256SUMS"
lipo -info "$LIB"
```

The hash of a rebuild can differ with toolchain, signing and build metadata. The original game-tested diagnostic library's SHA-256 was:

```text
67a3a411e4e9f98de119cda308662583efb2020d9575fe422c48521a55e84ab8
```

That library included the earlier, disabled diagnostic experiments. This repository contains the two active source patches only. A clean rebuild is not expected to be byte-identical to the diagnostic library. Native tests and game reproduction are the relevant checks.

## 3. Run the native regression checks

First check installer safeguards without touching CrossOver or Steam:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

The native GPU tests below also run without starting Steam. They render a tessellated triangle, check its green center pixel, exercise 16-bit/32-bit indexed and non-indexed draws, and test 1,048,575 vertices/indices. A control run disables the fix. A separate test extracts the real metadata-cache helpers from the patched source and checks padding, ownership, cleanup and fallback behavior.

```bash
python3 tests/run.py \
  --library "$LIB" \
  --headers "$BUILD/MoltenVK/External/Vulkan-Headers/include" \
  --source "$BUILD/MoltenVK" \
  --results "$BUILD/native-test-results"
```

The results directory must be new. All eight checks should pass. Tests request Metal API validation and execute from a temporary directory to avoid synced-folder signing issues. The fixtures include their GLSL source and embedded SPIR-V, so no shader compiler download is needed to run them.

## 4. Install into a separate CrossOver copy

Find the actual CrossOver application and Steam bottle paths. A bottle directory contains `cxbottle.conf` and `drive_c`. Paths with spaces must be quoted. The examples below are placeholders; replace them with your own paths.

```bash
CX_APP="/Applications/CrossOver Preview.app"
BOTTLE="/path/to/CrossOver/Steam"
python3 scripts/runtime.py install \
  --app "$CX_APP" --bottle "$BOTTLE" --library "$LIB" --dry-run
```

Review the printed paths. Then quit Enshrouded, Steam and CrossOver and install:

```bash
python3 scripts/runtime.py install \
  --app "$CX_APP" --bottle "$BOTTLE" --library "$LIB"
python3 scripts/runtime.py check
```

The installer:

- Copies CrossOver to `~/Library/Application Support/Enshrouded-CrossOver-Fix/CrossOver-Enshrouded.app` using `ditto` without resource forks, extended attributes or quarantine inheritance.
- Replaces only the copy's `Contents/SharedSupport/CrossOver/lib/x86_64/libMoltenVK.dylib`.
- Signs that copy ad hoc, preserving existing entitlements, and verifies its signature.
- Saves the runtime location, bottle path, driver hash and log path in `installation.json` beside the copy.

The check verifies the installed driver's post-signing hash, application signature, bottle/Steam paths and a Windows `cmd.exe` echo command. It does not launch the game. Exit Steam/the game before running it. The installer requires a new or empty destination, so unrelated files cannot be mixed into the runtime directory. For a second build, choose a new directory with `--home`; pass that same option to `check` and `play`.

If macOS requests permission for Terminal to manage applications, follow the system prompt. Do not disable SIP or Gatekeeper. If installation fails partway through, the original application is still available; inspect the error and use a new destination for the next attempt.

## 5. Launch and verify the game

Exit Steam fully first. Starting a new launcher while an existing Steam process is running can reuse that process's runtime.

```bash
python3 scripts/runtime.py play
```

You can also double-click `Play-Enshrouded.command` in the repository. For a custom installation:

```bash
bash Play-Enshrouded.command --home "/path/to/your/runtime-directory"
```

The launcher sets the exact active flags used for the successful configuration:

```text
MVK_PERF_OPTIMIZE_PRECISE_MATH=1
MVK_DIAG_REFLECT_TESS_OUTPUT_STRIDES=1
MVK_DIAG_DISABLE_RESIDENCY_SET=0
MVK_CONFIG_LIVE_CHECK_ALL_RESOURCES=0
```

It also disables the earlier barrier/live-check/resource-map experiments, allocation tracing, memory logging and presentation counters. Normal residency remains enabled. These private `MVK_DIAG_*` names belong to the investigation build; the clean two-patch library only implements the reflected-stride flag and ignores the unrelated switches. The math optimization comes from patch 0001 and intentionally changes precise-math helper optimization outside vertex shaders.

The launcher removes inherited diagnostic/HUD settings, starts Steam through the isolated Wine executable, and launches app `1203620`. Its log is `enshrouded-play.log` inside the runtime directory.

Check the following in game:

1. Load a world and check geometry and general responsiveness.
2. Equip the construction hammer and press Tab to open the building/Blueprints menu.
3. Keep the menu open for at least 30 seconds, then close and reopen it several times.
4. Check memory pressure in Activity Monitor and look for crashes, freezes, missing geometry or flicker.
5. Exit the game normally. Inspect the runtime log for `Tessellation output stride:` and errors such as `VK_ERROR_OUT_OF_DEVICE_MEMORY`.

On the successful test, reflected output records were 64/96/128 bytes rather than the 496-byte legacy allowance. Not every shader has those same values. A short successful run establishes the original reproduction; longer play, other worlds and other Macs still require testing.

## 6. Troubleshooting and rollback

| Symptom | Check |
|---|---|
| No compatible graphics card | Confirm the game was started through the new runtime and the pinned driver was installed. |
| Black screen during first launch | Inspect the log and CPU activity; shader compilation can take time. Keep Metal HUD disabled. |
| No stride messages after opening the hammer menu | Check the library hash and that the launcher supplies the reflected-stride flag. |
| Very slow menu / memory surge | Confirm normal residency is enabled and the old live-check/fallback experiments are disabled. |
| Flickering or missing geometry | Stop the test, retain the log, and check for inherited renderer overrides or a different driver build. |
| Xcode hangs before compiling | Use a local cache/tmp build folder outside FileProvider/iCloud. Retain the build log. |
| macOS kills a native test executable | Rebuild/run it in a local temporary directory and check its code signature. |

To return to the installed CrossOver, exit the game and Steam and start Steam through that original application. The separate copy does not alter the original app; it shares the selected Steam bottle. Save data is not rolled back by switching runtimes.

To remove the fix, quit the game/Steam, then remove **only the dedicated runtime directory created in step 4** and this source repository if no longer needed. Keep your bottle and saves. After a CrossOver update, create a new copy and retest; the isolated runtime does not update automatically.
