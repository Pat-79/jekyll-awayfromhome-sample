# jekyll-awayfromhome-sample
This is a demo website, build using the awayfromhome Jekyll theme. All content of this sample website is fictive. This website repo only serves as a demo for the theme.

## CI/CD

This repository includes a GitHub Actions workflow at `.github/workflows/ci-cd.yml`.

- On pull requests to `main`, it runs a Jekyll build for CI validation.
- On pushes to `main`, it builds and deploys to GitHub Pages.
- You can also run it manually with `workflow_dispatch`.
- CI uses `./scripts/deploy.sh build` so local and pipeline builds follow the same path.

### Requirements for GitHub Pages deploy

1. In GitHub repo settings, go to **Pages** and set the source to **GitHub Actions**.
2. Ensure Actions permissions allow Pages deployment (the workflow requests `pages: write` and `id-token: write`).

## Local Build and Deploy Script

Use `scripts/deploy.sh` for local build/deploy automation.

```bash
# Build site into docs/_site
./scripts/deploy.sh build

# Build and deploy docs/_site to gh-pages
./scripts/deploy.sh deploy
```

Environment variables:

- `DEPLOY_REMOTE` (default: `origin`)
- `DEPLOY_BRANCH` (default: `gh-pages`)
