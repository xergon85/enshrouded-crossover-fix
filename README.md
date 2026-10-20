# Enshrouded: CrossOver hammer-menu memory fix

A source patch and reproducible setup for Enshrouded on Apple Silicon Macs using CrossOver. It addresses excessive Metal memory allocation when opening the hammer's building/Blueprints menu with **Tab**.

The successful trial reduced large temporary buffer backing from **20 GiB to about 4.08 GiB**, restored responsive play, and completed without the hammer-menu crash. This is a community workaround tested on one Mac; see [validation and limits](docs/FINDINGS.md).

## Replicate the fix

Follow the [step-by-step reproduction guide](docs/REPRODUCING.md). It covers requirements, pinned sources, building, installing into a separate CrossOver copy, launching, verification and rollback.

The essential steps are:

1. Build the pinned MoltenVK revision with both patches in `patches/`.
2. Create a separate CrossOver runtime with `scripts/runtime.py install`.
3. Exit Steam, then launch with `Play-Enshrouded.command`.
4. Keep `MVK_DIAG_REFLECT_TESS_OUTPUT_STRIDES=1` and normal residency enabled. The supplied launcher sets these for you.

Full Xcode, Python 3, an existing CrossOver installation and a Steam bottle containing Enshrouded are required. The build targets **x86_64**, matching the CrossOver Wine process on the tested Apple Silicon system.

## What changes

MoltenVK reserves space for 1,048,576 vertices in indirect tessellation draws. The affected code sizes output records using maximum Vulkan component limits. Opening this game's menu caused forty 512 MiB temporary buffers to be allocated.

The new patch sizes those records from the compiled Metal pipeline's reflected, padded output stride. It retains the vertex capacity and falls back to the original size when reflection is unavailable. Both indexed and non-indexed paths are covered. Details and measurements are in [FINDINGS.md](docs/FINDINGS.md).

This repository also includes Nuno Cunha's existing precise-math performance patch, unchanged, because it was part of the tested setup. It is a separate optimization with different behavior; see [provenance](docs/PROVENANCE.md).

## Repository contents

| Path | Purpose |
|---|---|
| `patches/0001-*` | Existing non-vertex precise-math optimization |
| `patches/0002-*` | New reflected-stride tessellation allocation fix |
| `scripts/build.sh` | Pinned, fresh-directory source build |
| `scripts/runtime.py` | Separate-runtime install, check and launch |
| `tests/run.py` | GPU output, capacity and metadata-cache checks |
| `evidence/` | Sanitized results and tested version identifiers |
| `docs/` | Reproduction guide, findings and source attribution |

No CrossOver, Steam, game files, driver binaries, saves or personal crash logs are included. Existing game/bottle files are used by the separate runtime; back up saves as you normally would before testing runtime changes.

Apache License 2.0. Preserve [LICENSE](LICENSE) and [NOTICE](NOTICE) when redistributing. Unofficial; not affiliated with Khronos, CodeWeavers or Keen Games.
