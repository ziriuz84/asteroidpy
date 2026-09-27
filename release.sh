#!/bin/bash

# release.sh - Automates the asteroidpy release workflow
# Usage: ./release.sh 1.1.3
# Options: ./release.sh --help

set -e

# The release branch. Single source of truth: the help text, validate_repo and
# push_changes all read this, so they can no longer drift apart.
#
# Why this must be enforced rather than merely suggested: the release commit
# (version bump + CHANGELOG) is created on whatever branch is checked out, but
# the push below targets RELEASE_BRANCH. Releasing from any other branch
# therefore leaves the release commit unpushed while still publishing the tag,
# so PyPI would receive a release whose version bump never reached the release
# branch.
RELEASE_BRANCH="main"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Banner
print_banner() {
    cat << "EOF"

  ╔═══════════════════════════════════════╗
  ║   AsteroidPy Release Manager 🚀      ║
  ╚═══════════════════════════════════════╝

EOF
}

# Help
show_help() {
    cat << EOF
Usage: ./release.sh [VERSION] [OPTIONS]

Examples:
  ./release.sh 1.1.3               # Release version 1.1.3
  ./release.sh --patch             # Auto-increment patch (1.1.2 → 1.1.3)
  ./release.sh --minor             # Auto-increment minor (1.1.0 → 1.2.0)
  ./release.sh --major             # Auto-increment major (1.0.0 → 2.0.0)
  ./release.sh --dry-run 1.1.3     # Preview changes without committing

Options:
  --help           Show this help message
  --dry-run        Show what would be done without making changes
  --no-tag         Create release but don't push the tag
  --push-only      Only push an existing tag (for recovery)
  --github-release Only create the GitHub release for the current CHANGELOG entry

Files modified:
  - asteroidpy/version.py (__version__; pyproject.toml reads it via setuptools dynamic)
  - asteroidpy/locales/*/LC_MESSAGES/base.mo (recompiled from .po when msgfmt is available)
  - CHANGELOG.md (new section prepended): built from commits after the tag for the version in version.py prior to bump (vX.Y.Z..HEAD); feat/fix/docs map to Added/Fixed/etc.; merges, chore: release*, __version__ bumps ignored.

Requirements:
  - git, sed, grep, awk, cat, head, date, tr  (checked up front; missing = abort)
  - msgfmt (gettext; optional — if absent the script only warns, but PyPI wheels
    may ship stale .mo catalogs)
  - gh (GitHub CLI, only for --github-release) — https://cli.github.com,
    plus a completed 'gh auth login'
  - Current branch: $RELEASE_BRANCH (enforced; see the note in release.sh)
  - Clean working tree (no uncommitted changes to tracked files)

preflight_base() runs before the banner and before argument parsing, so a
missing tool is always reported as such rather than as a later, unrelated
failure. See preflight_base() and preflight_github().

EOF
}

# Validate semantic version format
validate_version() {
    local version=$1
    if [[ ! $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        error "Invalid version format: $version (use X.Y.Z format)"
    fi
}

# Read current version from version.py
get_current_version() {
    grep -E '^__version__[[:space:]]*=' asteroidpy/version.py | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1
}

# Increment version (major/minor/patch)
increment_version() {
    local current=$1
    local type=$2
    
    IFS='.' read -r major minor patch <<< "$current"
    
    case $type in
        patch)
            patch=$((patch + 1))
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        *)
            error "Unknown increment type: $type"
            ;;
    esac
    
    echo "$major.$minor.$patch"
}

# Assert a required executable is present.
#
# Blocking on purpose: every tool below is used to compute or validate the
# release, so a missing one either aborts the script or, worse, lets it get
# partway through — after the release commit already exists locally. Missing
# tools are accumulated instead of aborting on the first, so a bare environment
# is reported in full rather than fixed one run at a time.
MISSING_TOOLS=()

require_tool() {
    local tool=$1
    local hint=$2
    if ! command -v "$tool" >/dev/null 2>&1; then
        MISSING_TOOLS+=("$tool — $hint")
    fi
}

# Non-blocking: its absence degrades the result but does not invalidate it.
require_tool_optional() {
    local tool=$1
    local consequence=$2
    if ! command -v "$tool" >/dev/null 2>&1; then
        warning "'$tool' not found: $consequence"
    fi
}

# Abort with an explicit, complete explanation if anything required is missing.
assert_no_missing_tools() {
    if [ "${#MISSING_TOOLS[@]}" -gt 0 ]; then
        local list=""
        local entry
        for entry in "${MISSING_TOOLS[@]}"; do
            list="$list
  - $entry"
        done
        error "Aborting before making any change: required tool(s) missing from PATH:$list"
    fi
}

# Tools every mode needs. Called as the first statement of main(), before the
# banner and before argument parsing — parsing already calls get_current_version(),
# which shells out to grep, and print_banner() to cat, so a missing tool has to
# be reported here rather than as an unrelated failure further down.
preflight_base() {
    MISSING_TOOLS=()

    require_tool git "install git; this script also must run inside a git repository"
    require_tool sed "install GNU sed (e.g. 'apt-get install sed')"
    require_tool grep "install grep (e.g. 'apt-get install grep')"
    require_tool awk "install gawk/mawk (e.g. 'apt-get install gawk')"

    # Plain coreutils, used by print_banner(), the changelog builder and the
    # conventional-commit classifier. Missing on a stripped-down container, and
    # previously only noticed as a bare "cat: command not found" mid-run.
    local coreutils_hint="install coreutils (e.g. 'apt-get install coreutils')"
    require_tool cat "$coreutils_hint"
    require_tool head "$coreutils_hint"
    require_tool date "$coreutils_hint"
    require_tool tr "$coreutils_hint"

    assert_no_missing_tools

    # Optional: the release stays valid, only the compiled catalogs can go stale.
    require_tool_optional msgfmt "locale catalogs will NOT be recompiled, so the built wheel may ship stale .mo files. Install gettext (e.g. 'apt-get install gettext')."
}

# Extra tools for --github-release, checked once the mode is known but still
# before any state is read or written.
preflight_github() {
    MISSING_TOOLS=()

    require_tool gh "install the GitHub CLI: https://cli.github.com"

    assert_no_missing_tools

    # Presence is not enough: an unauthenticated gh only fails once the release
    # notes have been assembled, which is a confusing way to find out.
    if ! gh auth status >/dev/null 2>&1; then
        error "The GitHub CLI is installed but not authenticated.
Run: gh auth login
(required to check for and create the release)"
    fi
}

# Validate the current branch is the release branch.
# The optional reason is appended to the error, because the consequences of
# running from the wrong branch differ per mode and a generic message would be
# misleading in at least one of them.
validate_branch() {
    local current_branch
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    if [ "$current_branch" != "$RELEASE_BRANCH" ]; then
        local reason=${1:-"This script creates the release commit on the current branch yet pushes to
'$RELEASE_BRANCH'. Running it here would publish the tag while leaving the
version bump and CHANGELOG entry unpushed."}
        error "Releases must be cut from '$RELEASE_BRANCH', but HEAD is on '$current_branch'.
$reason

Run:  git checkout $RELEASE_BRANCH
Then:  git status --short   # must be empty"
    fi
}

# Validate repo is ready for release.
# The optional argument is a mode-specific explanation for the branch rule,
# forwarded to validate_branch().
validate_repo() {
    info "Validating repository state..."
    
    # Ensure we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        error "Not a git repository"
    fi
    
    # Hard requirement: release from the release branch.
    #
    # This is deliberately fatal rather than a y/N prompt. The release commit is
    # created on whatever branch is checked out, but push_changes() targets
    # RELEASE_BRANCH, so continuing from another branch would publish the tag
    # while silently dropping the version bump and CHANGELOG entry from the
    # remote. That state is not recoverable by re-running this script.
    validate_branch "${1:-}"
    
    # Check working tree.
    #
    # `git status --porcelain` rather than `git diff-index --quiet HEAD --`:
    # diff-index reads the index stat cache and can report a dirty tree that
    # git status considers clean, blocking a legitimate release. Untracked
    # files are excluded on purpose — release.sh stages an explicit path list,
    # so scratch files do not affect the release, but tracked edits do.
    if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
        error "Working directory has uncommitted changes. Please commit first.
Run: git status --short"
    fi
    
    # Check remote
    if ! git remote | grep -q 'origin'; then
        error "No 'origin' remote configured"
    fi
    
    success "Repository validation passed"
}

# Read the top released version from the CHANGELOG heading.
# Matches both shapes update_changelog() emits:
#   ## [1.2.3](https://.../releases/tag/v1.2.3) (2026-05-27)
#   ## [1.2.3] (2026-05-27)
changelog_version() {
    sed -n 's/^## \[\([^]]*\)\].*/\1/p' CHANGELOG.md | head -1
}

# Create the GitHub release for the top CHANGELOG entry.
#
# The notes are parsed from the *working tree* while the release is attached to
# a *tag*. Those two only agree if the checkout is the one that produced the
# tag, which is why this is refused off $RELEASE_BRANCH. Without that, a stale
# feature branch would silently publish release notes that exist in no commit
# and in no tag.
github_release() {
    local version=$1
    local dry_run=$2

    if [ ! -f CHANGELOG.md ]; then
        error "CHANGELOG.md not found"
    fi

    if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        error "Invalid version in CHANGELOG.md: '$version'"
    fi

    # The notes come from the checked-out tree: refuse to publish them if the
    # tree carries uncommitted edits, or if version.py disagrees, so the notes
    # always describe the commit the tag points at.
    if [ -f asteroidpy/version.py ]; then
        local py_version
        py_version=$(get_current_version)
        if [ -n "$py_version" ] && [ "$py_version" != "$version" ]; then
            error "CHANGELOG version ($version) does not match asteroidpy/version.py ($py_version)"
        fi
    fi

    local notes
    notes=$(awk -v v="$version" '
      $0 ~ "^## \\[" v "\\]" { in_section=1; next }
      in_section && /^## \[/ { exit }
      in_section && /^---$/ { next }
      in_section {
        sub(/---$/, "", $0)
        if ($0 != "") print
      }
    ' CHANGELOG.md)

    if [ -z "${notes//[[:space:]]/}" ]; then
        error "Release notes for v$version are empty in CHANGELOG.md"
    fi

    local tag="v$version"
    if ! git rev-parse "$tag^{commit}" >/dev/null 2>&1; then
        error "Git tag $tag not found locally. Fetch tags (git fetch --tags) or create it before running this."
    fi

    # New invariant: the tag must actually be part of the release branch.
    # This is precisely the invariant a release cut from the wrong branch
    # violated, and it is the only place it can still be caught.
    if ! git merge-base --is-ancestor "$tag^{commit}" "$RELEASE_BRANCH"; then
        error "Tag $tag is not reachable from '$RELEASE_BRANCH'.
The release commit must be merged into the release branch before the GitHub
release is created, otherwise the notes would describe a commit that main
does not contain."
    fi

    if gh release view "$tag" >/dev/null 2>&1; then
        error "GitHub release $tag already exists"
    fi

    if [ "$dry_run" = "true" ]; then
        info "Would run:"
        echo "  gh release create $tag --title 'AsteroidPy $version' --notes <CHANGELOG entry>"
        return 0
    fi

    gh release create "$tag" --title "AsteroidPy $version" --notes "$notes"
    success "GitHub release created: $tag"
}

# Bump version in tracked files
update_version() {
    local new_version=$1
    local dry_run=$2
    
    info "Updating version to $new_version..."
    
    # asteroidpy/version.py (canonical; pyproject.toml reads this via setuptools dynamic)
    if [ "$dry_run" = "true" ]; then
        sed -E -e 's/^__version__[[:space:]]*=.*/__version__ = "'"$new_version"'"/' asteroidpy/version.py | head -3
    else
        sed -i -E 's/^__version__[[:space:]]*=.*/__version__ = "'"$new_version"'"/' asteroidpy/version.py
    fi
    
    success "Version updated to $new_version"
}

# Compile gettext catalogs shipped inside the wheel (asteroidpy/locales/)
compile_locale_catalogs() {
    local dry_run=$1
    local msgfmt_missing_warned=false
    local compiled=0

    info "Compiling locale catalogs under asteroidpy/locales/..."

    shopt -s nullglob
    local po_files=(asteroidpy/locales/*/LC_MESSAGES/base.po)
    shopt -u nullglob

    if [ ${#po_files[@]} -eq 0 ]; then
        warning "No base.po files found under asteroidpy/locales/"
        return 0
    fi

    for po in "${po_files[@]}"; do
        local mo="${po%.po}.mo"
        if ! command -v msgfmt >/dev/null 2>&1; then
            if [ "$msgfmt_missing_warned" = "false" ]; then
                warning "msgfmt not found; install gettext to refresh .mo files before release"
                msgfmt_missing_warned=true
            fi
            if [ ! -f "$mo" ]; then
                error "Missing $mo and msgfmt is unavailable; compile catalogs or install gettext"
            fi
            continue
        fi

        if [ "$dry_run" = "true" ]; then
            echo "Would run: msgfmt -o $mo $po"
        else
            msgfmt -o "$mo" "$po"
        fi
        compiled=$((compiled + 1))
    done

    if [ "$compiled" -gt 0 ]; then
        success "Compiled $compiled locale catalog(s)"
    fi
}

# GitHub https base URL from origin (https://github.com/owner/repo), or empty
get_github_https_base() {
    local remote
    remote=$(git remote get-url origin 2>/dev/null || echo "")
    if [[ "$remote" =~ github\.com[:/]([^/]+)/([^/.]+)(\.git)?$ ]]; then
        echo "https://github.com/${BASH_REMATCH[1]}/${BASH_REMATCH[2]%.git}"
    else
        echo ""
    fi
}

# Maps conventional commit subjects to changelog sections (added/changed/fixed/...)
classify_commit_subject() {
    local s="$1"
    if [[ "$s" != *:* ]]; then
        local lc
        lc=$(printf '%s\n' "$s" | tr '[:upper:]' '[:lower:]')
        if [[ "$lc" == bump* ]] && [[ "$s" =~ __version__ ]]; then
            echo "skip"
        else
            echo "changed"
        fi
        return
    fi

    local prefix="${s%%:*}"
    local body="${s#*:}"
    local body_trim="${body#"${body%%[![:space:]]*}"}"
    local body_lower
    body_lower=$(printf '%s\n' "$body_trim" | tr '[:upper:]' '[:lower:]')

    case "$prefix" in
        Merge*)
            echo "skip"
            return
            ;;
    esac

    local raw_type="${prefix%%(*}"
    local type="$raw_type"
    type="${type%\!}"

    case "$type" in
        feat | Feat | feature | Feature) echo added ;;
        fix | Fix) echo fixed ;;
        docs | Docs) echo documentation ;;
        test | tests | Test | Tests) echo tests ;;
        chore | Chore)
            if [[ "$body_lower" == release* ]] || { [[ "$body_lower" == bump* ]] && [[ "$s" =~ __version__ ]]; }; then
                echo skip
            else
                echo chores
            fi
            ;;
        style | Style | refactor | Refactor | perf | Perf | ci | CI | build | Build | revert | Revert) echo changed ;;
        *) echo changed ;;
    esac
}

# Build markdown changelog body from git (v<previous_version>..HEAD unless fallback)
build_changelog_notes() {
    local previous_version=$1
    local github_base=$2
    local log_range=""
    local tmpdir
    tmpdir=$(mktemp -d)

    if git rev-parse "v${previous_version}^{commit}" >/dev/null 2>&1; then
        log_range="v${previous_version}..HEAD"
    elif last=$(git describe --tags --abbrev=0 --match 'v*' 2>/dev/null); then
        warning "Tag v${previous_version} not found; using revision range ${last}..HEAD"
        log_range="${last}..HEAD"
    else
        warning "No v* tag found; falling back to the last 30 commits"
        log_range="-n 30"
    fi

    : >"$tmpdir/added"
    : >"$tmpdir/changed"
    : >"$tmpdir/fixed"
    : >"$tmpdir/documentation"
    : >"$tmpdir/tests"
    : >"$tmpdir/chores"

    local -a log_cmd
    if [[ "$log_range" == "-n 30" ]]; then
        log_cmd=(git log -n 30 --no-merges --pretty=format:'%H|%s')
    else
        log_cmd=(git log "$log_range" --no-merges --pretty=format:'%H|%s')
    fi

    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        local hash="${line%%|*}"
        local subject="${line#*|}"
        local section
        section=$(classify_commit_subject "$subject")
        [[ "$section" == "skip" ]] && continue
        local short
        short=$(git rev-parse --short "$hash" 2>/dev/null || echo "${hash:0:7}")
        local link_suffix=""
        if [[ -n "$github_base" ]]; then
            link_suffix=" ([${short}](${github_base}/commit/${hash}))"
        fi
        echo "- ${subject}${link_suffix}" >>"$tmpdir/$section"
    done < <("${log_cmd[@]}")

    append_section() {
        local title=$1
        local file=$2
        if [[ -s "$file" ]]; then
            printf '%s\n\n%s\n\n' "### $title" "$(cat "$file")" >>"$tmpdir/outbuf"
        fi
    }

    : >"$tmpdir/outbuf"
    append_section "Added" "$tmpdir/added"
    append_section "Changed" "$tmpdir/changed"
    append_section "Fixed" "$tmpdir/fixed"
    append_section "Documentation" "$tmpdir/documentation"
    append_section "Tests" "$tmpdir/tests"
    append_section "Chores" "$tmpdir/chores"

    if [[ ! -s "$tmpdir/outbuf" ]]; then
        echo "### Changed"
        echo ""
        echo "- No commits left after filtering (merge/release/__version__ bump only). Check tags or edit this entry manually."
        echo ""
        rm -rf "$tmpdir"
    else
        cat "$tmpdir/outbuf"
        rm -rf "$tmpdir"
    fi
}

# Prepend generated release section to CHANGELOG.md
update_changelog() {
    local previous_version=$1
    local new_version=$2
    local dry_run=$3
    local date
    date=$(date +%Y-%m-%d)

    info "Updating CHANGELOG.md..."

    local github_base
    github_base=$(get_github_https_base)
    local heading
    if [[ -n "$github_base" ]]; then
        heading="## [$new_version](${github_base}/releases/tag/v${new_version}) (${date})"
    else
        heading="## [$new_version] (${date})"
    fi

    local body
    body=$(build_changelog_notes "$previous_version" "$github_base")
    body="${body%"${body##*[![:space:]]}"}"$'\n'

    local changelog_entry="${heading}"$'\n\n'"${body}"$'---'$'\n\n'

    if [ "$dry_run" = "true" ]; then
        echo "CHANGELOG.md would be updated with:"
        echo "$changelog_entry"
    else
        temp=$(mktemp)
        {
            echo "$changelog_entry"
            cat CHANGELOG.md
        } >"$temp"
        mv "$temp" CHANGELOG.md
    fi

    success "CHANGELOG.md updated"
}

# Stage and commit version + changelog
create_commit() {
    local version=$1
    local dry_run=$2
    
    info "Creating release commit..."
    
    if [ "$dry_run" = "true" ]; then
        echo "Would run:"
        echo "  git add asteroidpy/version.py asteroidpy/locales CHANGELOG.md"
        echo "  git commit -m 'chore: release v$version'"
    else
        git add asteroidpy/version.py asteroidpy/locales CHANGELOG.md
        git commit -m "chore: release v$version"
        success "Commit created"
    fi
}

# Create annotated git tag
create_tag() {
    local version=$1
    local dry_run=$2
    
    info "Creating git tag..."
    
    if [ "$dry_run" = "true" ]; then
        echo "Would run:"
        echo "  git tag -a v$version -m 'Release version $version'"
        echo "  (pushing is handled by push_changes)"
    else
        # Annotated tag points at release commit (__version__)
        git tag -a "v$version" -m "Release version $version"
        success "Tag created: v$version"
    fi
}

# Push
push_changes() {
    local version=$1
    local dry_run=$2
    local no_tag=$3
    
    info "Pushing changes to origin..."
    
    if [ "$dry_run" = "true" ]; then
        echo "Would run:"
        echo "  git push origin $RELEASE_BRANCH"
        if [ "$no_tag" != "true" ]; then
            echo "  git push origin v$version"
        fi
    else
        git push origin "$RELEASE_BRANCH"
        if [ "$no_tag" != "true" ]; then
            git push origin "v$version"
        fi
        success "Changes pushed to origin"
    fi
}

# Main
main() {
    # First statement on purpose: argument parsing itself calls
    # get_current_version(), which shells out to grep, and --github-release calls
    # git. Verifying the tools before any of that guarantees a missing
    # dependency is reported as such, instead of as a confusing failure later.
    preflight_base

    print_banner
    
    local new_version=""
    local dry_run=false
    local no_tag=false
    local push_only=false
    local github_only=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                show_help
                exit 0
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --no-tag)
                no_tag=true
                shift
                ;;
            --push-only)
                push_only=true
                shift
                ;;
            --github-release)
                github_only=true
                shift
                ;;
            --patch|--minor|--major)
                current_version=$(get_current_version)
                increment_type=${1#--}
                new_version=$(increment_version "$current_version" "$increment_type")
                shift
                ;;
            *)
                new_version=$1
                shift
                ;;
        esac
    done
    
    # GitHub-release-only mode: the version is whatever the CHANGELOG says, so
    # it is derived instead of required. Handled before the "no version
    # specified" check, which would otherwise reject the bare flag.
    if [ "$github_only" = "true" ]; then
        preflight_github
        validate_repo "The release notes are parsed from the working tree while the release is
attached to a tag, so the two only agree if this checkout is the one that
produced the tag. Publishing from here would ship notes that exist in no
commit and in no tag."
        info "GitHub release mode: skipping version bump, changelog, commit and tag"
        if [ "$dry_run" = "true" ]; then
            warning "DRY RUN MODE - no changes will be made"
        fi
        local changelog_ver
        changelog_ver=$(changelog_version)
        if [ -z "$changelog_ver" ]; then
            error "Could not parse a release version from CHANGELOG.md"
        fi
        info "CHANGELOG version: $changelog_ver"
        github_release "$changelog_ver" "$dry_run"
        return 0
    fi
    
    # Require explicit version (--patch|--minor|--major handled above)
    if [ -z "$new_version" ]; then
        current=$(get_current_version)
        error "No version specified. Current version: $current\nRun with --help for usage"
    fi
    
    # Semantic version sanity check
    validate_version "$new_version"
    
    # Info
    current_version=$(get_current_version)
    info "Current version: $current_version"
    info "New version: $new_version"
    
    if [ "$dry_run" = "true" ]; then
        warning "DRY RUN MODE - no changes will be made"
    fi
    
    # Push-only: skip changelog/version steps, but still refuse to push from a
    # branch other than RELEASE_BRANCH — the recovery path is exactly where a
    # stray `git push origin main` would do real damage.
    if [ "$push_only" = "true" ]; then
        info "Push-only mode: skipping version bump, changelog and tag creation"
        if ! git rev-parse --git-dir > /dev/null 2>&1; then
            error "Not a git repository"
        fi
        validate_branch
        push_changes "$new_version" "$dry_run" "$no_tag"
        success "Tag pushed"
        return 0
    fi
    
    # Prerequisites
    validate_repo

    local previous_version
    previous_version=$(get_current_version)

    # Version file, locale catalogs, changelog, commit
    update_version "$new_version" "$dry_run"
    compile_locale_catalogs "$dry_run"
    update_changelog "$previous_version" "$new_version" "$dry_run"
    create_commit "$new_version" "$dry_run"

    # Tag must attach to the commit that touches __version__ (CI expects this)
    if [ "$dry_run" != "true" ]; then
        if ! git show --pretty="" --name-only HEAD | grep -qx 'asteroidpy/version.py'; then
            error "Release commit missing asteroidpy/version.py — refusing to tag (fix release.sh)"
        fi
        committed_ver=$(
            git show "HEAD:asteroidpy/version.py" | grep -E '^__version__' |
                grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1
        )
        if [ "$committed_ver" != "$new_version" ]; then
            error "Committed __version__ ($committed_ver) != release target ($new_version)"
        fi
    fi

    create_tag "$new_version" "$dry_run"
    push_changes "$new_version" "$dry_run" "$no_tag"
    
    # Summary
    echo ""
    if [ "$dry_run" = "true" ]; then
        warning "DRY RUN completed. No changes were made."
        info "Run again without --dry-run to make changes"
    else
        success "Release v$new_version created successfully!"
        echo ""
        echo "Next steps:"
        echo "  1. Jenkins will detect the tag and run tests, build, and PyPI publish"
        echo "  2. After Jenkins succeeds, run ./ghrelease.sh to create the GitHub release"
        echo ""
        info "Release process initiated! 🚀"
    fi
}

# Entry point
main "$@"
