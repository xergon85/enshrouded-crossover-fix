# Source provenance and redistribution

## MoltenVK baseline

- Repository: [KhronosGroup/MoltenVK](https://github.com/KhronosGroup/MoltenVK).
- Pinned source: [5189f8de86ec365860f63bf1da736815cfaea5cd](https://github.com/KhronosGroup/MoltenVK/tree/5189f8de86ec365860f63bf1da736815cfaea5cd).
- Dependencies: the pinned source's `ExternalRevisions/` files; SPIRV-Cross is `aa217aeb6c9f0ace7a0ab233b28807edf45eb165`.
- License: Apache License 2.0 for MoltenVK; preserve individual dependency licenses if distributing compiled libraries.

## Existing performance optimization

- Author: Nuno Cunha.
- Repository: [djnunocunhadev/enshrouded-mac-perfmod](https://github.com/djnunocunhadev/enshrouded-mac-perfmod).
- Inspected commit: [ad485d3a841508d1d76138fb742204fa67ccdafe](https://github.com/djnunocunhadev/enshrouded-mac-perfmod/tree/ad485d3a841508d1d76138fb742204fa67ccdafe).
- `patches/0001-optimize-precise-math-helpers.patch` is copied unchanged from that source.
- Its Apache 2.0 LICENSE and attribution NOTICE are retained; additional modifications are identified in NOTICE.

The original investigation started from a user reference to [icetear/x4-crossover-moltenvk-fix](https://github.com/icetear/x4-crossover-moltenvk-fix). The source actually present on the test machine was the Enshrouded performance-mod checkout above. The reproduction here pins that inspected source ancestry rather than assuming the two repositories are interchangeable.

## Additional work

Patch 0002, runtime/build scripts, diagnostic fixtures and documentation capture the subsequent hammer-menu investigation. Patch 0002 contains the same active tessellation-sizing changes used in the successful game test, extracted from the diagnostic build. Previous diagnostic changes are omitted. The clean source package has its own native validation; the original diagnostic library hash identifies the separately game-validated artifact.

This repository distributes source patches, test fixtures and documentation only. CrossOver must be obtained separately from CodeWeavers; Steam and Enshrouded must already be installed by the user. The installer copies the user's own local application into a separate runtime directory. Do not upload that runtime copy or game/bottle files with this repository.

Before distributing a compiled MoltenVK build, include its complete dependency license/notice material and source/build provenance. The repository's source-only ZIP deliberately contains no compiled driver or proprietary runtime.
