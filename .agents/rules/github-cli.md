# GitHub CLI Rule

Use this rule before any GitHub issue, PR, review, branch cleanup, or `gh` workflow in this repository.

## Local Auth First

Do not silently use global GitHub CLI auth. Detect repo-local auth in this order:

```bash
if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI is not installed."
  echo "Install gh, then run the local auth setup script below."
  exit 1
fi

if [ -f "$PWD/.gh/hosts.yml" ]; then
  export GH_CONFIG_DIR="$PWD/.gh"
elif [ -f "$PWD/tmp/gh/hosts.yml" ]; then
  export GH_CONFIG_DIR="$PWD/tmp/gh"
else
  echo "No repo-local gh auth found in .gh/ or tmp/gh/."
  exit 1
fi
```

Then verify:

```bash
gh auth status
```

## Setup Script

If `gh` exists but repo-local auth is missing, give the user this setup script:

```bash
mkdir -p tmp/gh
export GH_CONFIG_DIR="$PWD/tmp/gh"
gh auth login --hostname github.com --git-protocol https --web
gh auth status
```

If `gh` is not installed, ask the user to install GitHub CLI first. Common options:

```bash
# macOS
brew install gh

# Debian/Ubuntu, if GitHub CLI apt repository is already configured
sudo apt install gh
```

## Constraints

- Never print tokens from `hosts.yml`.
- Never commit `.gh/` or `tmp/gh/`.
- Prefer `.agents/lib/github/setup.md` for shared PR/issue workflow variables.
- Stop if auth cannot be verified.
