#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIN=5189f8de86ec365860f63bf1da736815cfaea5cd
WORK="${WORK:-$HOME/Library/Caches/enshrouded-crossover-fix/build-$(date +%Y%m%d-%H%M%S)-$$}"
REPO="${MOLTENVK_REPO:-https://github.com/KhronosGroup/MoltenVK.git}"
if [[ -e "$WORK" ]]; then
  printf 'Refusing to overwrite an existing build directory: %s\n' "$WORK" >&2
  exit 1
fi
command -v python3 >/dev/null
xcrun --find clang >/dev/null
mkdir -p "$WORK"
git clone --no-checkout "$REPO" "$WORK/MoltenVK"
SRC="$WORK/MoltenVK"
if ! git -C "$SRC" cat-file -e "$PIN^{commit}"; then
  git -C "$SRC" fetch origin "$PIN"
fi
git -C "$SRC" checkout --detach "$PIN"
[[ "$(git -C "$SRC" rev-parse HEAD)" == "$PIN" ]]
git -C "$SRC" apply --check "$ROOT/patches/0001-optimize-precise-math-helpers.patch" "$ROOT/patches/0002-size-indirect-tessellation-output.patch"
git -C "$SRC" apply "$ROOT/patches/0001-optimize-precise-math-helpers.patch" "$ROOT/patches/0002-size-indirect-tessellation-output.patch"
if [[ "${PREPARE_ONLY:-0}" == 1 ]]; then
  printf 'Pinned source prepared and both patches applied: %s\n' "$SRC"
  exit 0
fi
cd "$SRC"
./fetchDependencies --macos
xcodebuild build -project MoltenVKPackaging.xcodeproj \
  -scheme 'MoltenVK Package (macOS only)' -destination 'generic/platform=macOS' \
  -derivedDataPath "$WORK/DerivedData" -jobs "${JOBS:-4}" \
  ARCHS=x86_64 ONLY_ACTIVE_ARCH=YES CODE_SIGNING_ALLOWED=NO \
  2>&1 | tee "$WORK/build.log"
LIB="$SRC/Package/Release/MoltenVK/dynamic/dylib/macOS/libMoltenVK.dylib"
[[ -f "$LIB" ]]
mkdir "$WORK/dist"
cp "$LIB" "$WORK/dist/libMoltenVK.dylib"
codesign --force --sign - "$WORK/dist/libMoltenVK.dylib"
lipo "$WORK/dist/libMoltenVK.dylib" -verify_arch x86_64
(cd "$WORK/dist" && shasum -a 256 libMoltenVK.dylib > SHA256SUMS)
cp "$SRC/LICENSE" "$WORK/dist/MoltenVK-LICENSE"
cp -R "$SRC/ExternalRevisions" "$WORK/dist/ExternalRevisions"
python3 - "$ROOT" "$WORK" "$PIN" <<'PY'
import hashlib,json,subprocess,sys
from pathlib import Path
root,work,pin=Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3]
manifest={'moltenvk_commit':pin,'architecture':'x86_64',
 'xcode':subprocess.check_output(['xcodebuild','-version'],text=True).strip(),
 'patches':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'patches').glob('*.patch'))}}
(work/'dist/build.json').write_text(json.dumps(manifest,indent=2)+'\n')
PY
printf '\nBuild saved in %s/dist\n' "$WORK"
