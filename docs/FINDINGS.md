# Diagnosis, implementation and validation

## Failure and allocation evidence

Enshrouded could start using an updated, performance-patched MoltenVK, but opening the construction hammer's building/Blueprints menu with Tab triggered a crash or freeze. Lowering resolution and quality did not resolve it. The failing path reported `VK_ERROR_OUT_OF_DEVICE_MEMORY` and Metal's `kIOGPUCommandBufferCallbackErrorOutOfMemory` (code 8).

The decisive trace separated Vulkan allocations from MoltenVK's private Metal allocations:

| Observation | Value |
|---|---:|
| Live tracked Vulkan allocation bytes across menu opening | 6,137,983,748, unchanged |
| Metal allocated bytes before menu | 6,213,091,328 |
| Metal allocated bytes after menu | 27,771,879,424 |
| Newly created large temporary buffers | 40 × 536,870,912 bytes |
| Backing represented by those buffers | 20 GiB |

The dominant growth was internal tessellation scratch storage. This explains why reducing screen resolution did not remove the allocation spike. It does not establish that all crashes in this game have the same cause.

## Source-level cause

At the pinned MoltenVK revision, `MoltenVK/MoltenVK/Commands/MVKCmdDraw.mm` reserves `1024 * KIBI` vertices for indirect tessellation. Output allocations use the device's maximum Vulkan output-component limits, multiplied by four bytes per component. For relevant game pipelines, the legacy vertex record allowance was 496 bytes, then the temporary-buffer allocator rounded the backing size up to 512 MiB.

The shader's actual output record was much smaller. Metal pipeline reflection reported padded records of 64 or 96 bytes for vertex outputs and 128 bytes for tessellation-control outputs in the successful game run.

## Patch behavior

Patch 0002 requests `MTLPipelineOptionArgumentInfo | MTLPipelineOptionBufferTypeInfo` while compiling compute pipeline states. It caches each positive reflected buffer data size, rounded up to its reported alignment. Indirect indexed and non-indexed tessellation draws look up the applicable stage's output-buffer index and use that stride when allocating vertex, control-point and patch outputs.

The change preserves the existing vertex capacity, draw counts, tessellation factors, shader source and advertised Vulkan feature limits. If the flag is disabled, the pipeline is unknown, the argument is absent or its metadata cannot be used, allocation keeps the legacy stride.

The cache is protected by a mutex. It counts shared pipeline-state owners and removes entries after the last corresponding graphics/compute pipeline owner is destroyed. Newly compiled states replace previous argument metadata, including empty reflection, to prevent an old stride surviving pointer reuse. The cache retains no Metal objects or GPU resources. Factory helper pipeline metadata can remain until process exit; this is small CPU metadata, not the large scratch storage at issue.

Only two existing translation units change: `MVKPipeline.mm` and `MVKCmdDraw.mm`, plus a new utility header. No class-layout or serialized shader-cache format change is required. The opt-in environment variable retains its investigation name, `MVK_DIAG_REFLECT_TESS_OUTPUT_STRIDES=1`, so existing launchers continue to work.

Patch 0001 is an independent existing performance mod. It removes `[[clang::optnone]]` from selected precise-math helpers outside vertex shaders. It changes shader optimization behavior and is not a general Vulkan-conformance fix. Its author and source are credited in [PROVENANCE.md](PROVENANCE.md).

## Successful game reproduction

Tested on 2026-10-20 using the versions in the reproduction guide. The hammer/Blueprints menu opened, the user reported much better performance, and the game shut down normally without a logged MoltenVK error.

| Measurement | Earlier diagnostic/failing runs | Successful sizing-fix run |
|---|---:|---:|
| Large temporary backing attributed at menu opening | 20 GiB | 4.078125 GiB |
| Peak process footprint | approximately 27.4 GiB | 11.1681 GiB |
| Maximum Metal allocated bytes | approximately 27.77 billion | 10,592,010,240 |
| Nearby menu presentation completions/second | approximately 1 in the slow fallback | 24–28 with normal residency |

These are different diagnostic runs, not a controlled benchmark. Presentation numbers count successful/suboptimal `vkQueuePresentKHR` completions; they are **not independently measured displayed FPS**. Allocation tracing included resources of at least 1 MiB, so the backing total is not a count of every allocation. The new run's large pool backing comprised twenty-four 128 MiB buffers, sixteen 64 MiB buffers and twenty 4 MiB buffers.

Normal residency was restored in the successful run. Earlier experiments disabling residency and adding live resource checks/barrier preservation avoided some crashes but were slow; other variants produced missing/flickering geometry. Those experiments are omitted from this repository. Do not treat them as prerequisites for patch 0002.

## Reproduction-package validation

A fresh checkout of MoltenVK `5189f8de…` accepted both packaged patches. A complete x86_64 MoltenVK packaging build with Xcode succeeded on 2026-10-20. This verification reused the previously downloaded dependency trees and built dependency archives; the public script's network download step was not rerun. Dependency Git revisions were checked against `ExternalRevisions`.

The clean two-patch library passed all eight packaged checks with normal residency and Metal API validation:

- Basic indirect draw: non-indexed, 16-bit indices and 32-bit indices.
- Near-capacity draw: 1,048,575 vertices/indices in all three modes.
- Fix disabled: original sizing still renders the expected pixel.
- Extracted production cache helpers: alignment/padding, absent arguments/state, shared ownership, cleanup and missing-reflection replacement.

Every render test checked a green center pixel read back from the GPU. These fixtures exercise the allocation paths but do not exhaust possible shader interfaces or game content. The earlier diagnostic driver also passed the original native suite recorded in `evidence/original-native-results.json`.

The packaged scripts passed Python/shell syntax checks; the installer dry run accepted the real application/bottle paths, including spaces, and the clean driver's architecture/feature flag. An installer fixture test checks nonempty-directory rejection, path isolation, post-signing hash storage, reinstall refusal and changed-library detection while simulating copy/sign tools. The new portable installer was not used to replace the working runtime, and the clean two-patch build has not yet been game-tested. The installed diagnostic driver remains the game-validated build. Machine-readable summaries are in `evidence/`.

## Limits and next steps

Long sessions, large bases, additional shader layouts, multiplayer and other hardware remain untested. Metal's older reflection argument API is deprecated in recent SDKs; the current patch uses it for compatibility with the pinned source. Reflection adds pipeline creation work, and the cache/fallback behavior deserves upstream review before broader distribution.

For an upstream report, attach patch 0002, the allocation table, source/OS/driver versions, native test results and exact reproduction steps. Provide fresh logs only after reviewing them for private paths, Steam identifiers or server details. Keep the separate precise-math optimization explicit when comparing results.
