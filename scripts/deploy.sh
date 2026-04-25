#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_DIR="$ROOT_DIR/docs"
SITE_DIR="$DOCS_DIR/_site"
DEPLOY_REMOTE="${DEPLOY_REMOTE:-origin}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-gh-pages}"

build_site() {
  cd "$DOCS_DIR"
  bundle config set path vendor/bundle
  bundle install --jobs 4 --retry 3
  bundle exec jekyll build
}

deploy_site() {
  local worktree_dir
  worktree_dir="$(mktemp -d)"

  cleanup() {
    git -C "$ROOT_DIR" worktree remove "$worktree_dir" --force >/dev/null 2>&1 || true
    rm -rf "$worktree_dir"
  }
  trap cleanup EXIT

  if git -C "$ROOT_DIR" ls-remote --exit-code --heads "$DEPLOY_REMOTE" "$DEPLOY_BRANCH" >/dev/null 2>&1; then
    git -C "$ROOT_DIR" fetch "$DEPLOY_REMOTE" "$DEPLOY_BRANCH"
    git -C "$ROOT_DIR" worktree add "$worktree_dir" "$DEPLOY_REMOTE/$DEPLOY_BRANCH"
  else
    git -C "$ROOT_DIR" worktree add --detach "$worktree_dir"
    git -C "$worktree_dir" checkout --orphan "$DEPLOY_BRANCH"
    git -C "$worktree_dir" rm -rf . >/dev/null 2>&1 || true
  fi

  rsync -a --delete "$SITE_DIR/" "$worktree_dir/"
  touch "$worktree_dir/.nojekyll"

  if [[ -f "$DOCS_DIR/CNAME" ]]; then
    cp "$DOCS_DIR/CNAME" "$worktree_dir/CNAME"
  fi

  git -C "$worktree_dir" add -A

  if git -C "$worktree_dir" diff --cached --quiet; then
    echo "No changes to deploy."
    return
  fi

  git -C "$worktree_dir" commit -m "Deploy site $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  git -C "$worktree_dir" push "$DEPLOY_REMOTE" "HEAD:$DEPLOY_BRANCH" --force

  echo "Deployment complete: $DEPLOY_REMOTE/$DEPLOY_BRANCH"
}

usage() {
  cat <<'EOF'
Usage:
  scripts/deploy.sh build   # Build Jekyll site into docs/_site
  scripts/deploy.sh deploy  # Build and push docs/_site to gh-pages

Environment variables:
  DEPLOY_REMOTE (default: origin)
  DEPLOY_BRANCH (default: gh-pages)
EOF
}

main() {
  local command="${1:-build}"

  case "$command" in
    build)
      build_site
      echo "Build complete: $SITE_DIR"
      ;;
    deploy)
      build_site
      deploy_site
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
