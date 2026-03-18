#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
version="${1:-0.1.0}"

cd "$repo_root"

mkdir -p dist
rm -f "dist/hca-cli-${version}.tar.gz"
rm -f packaging/arch/*.pkg.tar.zst packaging/arch/*.pkg.tar.zst.sig packaging/arch/hca-cli-"${version}".tar.gz || true

tar \
  --exclude-vcs \
  --exclude='packaging/arch/*.pkg.tar.zst' \
  --exclude='packaging/arch/src' \
  --exclude='packaging/arch/pkg' \
  --exclude='__pycache__' \
  --exclude='.pytest_cache' \
  --transform "s,^,hca-cli-${version}/," \
  -czf "dist/hca-cli-${version}.tar.gz" \
  .

cp "dist/hca-cli-${version}.tar.gz" packaging/arch/

(
  cd packaging/arch
  makepkg --nodeps -f
)

cp packaging/arch/*.pkg.tar.zst dist/
cp packaging/arch/PKGBUILD dist/
cp packaging/arch/.SRCINFO dist/

(
  cd dist
  sha256sum * > SHA256SUMS
)

echo "Release assets created in $repo_root/dist"
