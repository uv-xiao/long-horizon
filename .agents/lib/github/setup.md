# Setup

Initialize GitHub workflow state.

## Authenticate

Use repository-local GitHub CLI config before running any `gh` command:

```bash
if ! command -v gh >/dev/null 2>&1; then
  cat <<'EOF'
GitHub CLI is not installed.

Install it first, then initialize repo-local auth:

  mkdir -p tmp/gh
  export GH_CONFIG_DIR="$PWD/tmp/gh"
  gh auth login --hostname github.com --git-protocol https --web
  gh auth status
EOF
  exit 1
fi

if [ -f "$PWD/.gh/hosts.yml" ]; then
  export GH_CONFIG_DIR="$PWD/.gh"
elif [ -f "$PWD/tmp/gh/hosts.yml" ]; then
  export GH_CONFIG_DIR="$PWD/tmp/gh"
else
  cat <<'EOF'
No repo-local GitHub CLI auth was found.

Create local auth before using GitHub skills:

  mkdir -p tmp/gh
  export GH_CONFIG_DIR="$PWD/tmp/gh"
  gh auth login --hostname github.com --git-protocol https --web
  gh auth status

Alternative: place an existing gh config in .gh/ or tmp/gh/.
EOF
  exit 1
fi
```

Then run:

```bash
gh auth status
```

If authentication fails, tell the user to refresh repo-local auth with the script above and stop.

## Detect Canonical Repository

Prefer the current GitHub CLI context:

```bash
PR_REPO_OWNER=$(gh repo view --json owner -q '.owner.login')
PR_REPO_NAME=$(gh repo view --json name -q '.name')
DEFAULT_BRANCH=$(gh repo view --json defaultBranchRef -q '.defaultBranchRef.name')
```

If repository detection fails, stop and ask the user for the target `owner/name` instead of guessing.

## Detect Role And Remotes

```bash
ORIGIN_URL=$(git remote get-url origin 2>/dev/null || echo "")
REPO_OWNER=$(echo "$ORIGIN_URL" | sed -n 's#.*[:/]\([^/]*\)/\([^/]*\)\.git.*#\1#p')
REPO_NAME=$(echo "$ORIGIN_URL" | sed -n 's#.*[:/]\([^/]*\)/\([^/]*\)\.git.*#\2#p')

if [ "$REPO_OWNER" = "$PR_REPO_OWNER" ] && [ "$REPO_NAME" = "$PR_REPO_NAME" ]; then
  ROLE="owner"
  BASE_REMOTE="origin"
  PR_HEAD_PREFIX=""
else
  ROLE="fork"
  BASE_REMOTE="upstream"
  PR_HEAD_PREFIX="$REPO_OWNER:"
  if ! git remote | grep -q '^upstream$'; then
    git remote add upstream "git@github.com:$PR_REPO_OWNER/$PR_REPO_NAME.git"
  fi
fi

git fetch "$BASE_REMOTE" "$DEFAULT_BRANCH"
git fetch origin

BASE_REF="$BASE_REMOTE/$DEFAULT_BRANCH"
PUSH_REMOTE="origin"
BRANCH_NAME=$(git branch --show-current 2>/dev/null || echo "")
UNCOMMITTED=$(git status --porcelain)
COMMITS_AHEAD=$(git rev-list HEAD --not "$BASE_REF" --count 2>/dev/null || echo "0")
```

Never assume local `main` is fresh. Use `BASE_REF`.
