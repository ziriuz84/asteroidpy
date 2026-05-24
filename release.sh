#!/bin/bash

# release.sh - Automatizza il processo di rilascio di asteroidpy
# Uso: ./release.sh 1.1.3
# Opzioni: ./release.sh --help

set -e

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzioni helper
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
  --push-only      Only push existing tag (for recovery)

Files modified:
  - asteroidpy/version.py (__version__)
  - setup.py (version, if present)
  - CHANGELOG.md (new entry)

Requirements:
  - git
  - grep/sed
  - Current branch: main (or development)

EOF
}

# Valida versione
validate_version() {
    local version=$1
    if [[ ! $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        error "Invalid version format: $version (use X.Y.Z format)"
    fi
}

# Estrai versione corrente
get_current_version() {
    grep -E '^__version__[[:space:]]*=' asteroidpy/version.py | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1
}

# Incrementa versione
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

# Valida repository state
validate_repo() {
    info "Validating repository state..."
    
    # Check se siamo in un git repo
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        error "Not a git repository"
    fi
    
    # Check branch corrente
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    if [ "$current_branch" != "main" ] && [ "$current_branch" != "master" ]; then
        warning "Current branch is '$current_branch' (expected 'main' or 'master')"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            error "Aborted by user"
        fi
    fi
    
    # Check working tree
    if ! git diff-index --quiet HEAD --; then
        error "Working directory has uncommitted changes. Please commit first."
    fi
    
    # Check remote
    if ! git remote | grep -q 'origin'; then
        error "No 'origin' remote configured"
    fi
    
    success "Repository validation passed"
}

# Aggiorna versione nei file
update_version() {
    local new_version=$1
    local dry_run=$2
    
    info "Updating version to $new_version..."
    
    # asteroidpy/version.py (canonical; pyproject.build reads this via setuptools dynamic)
    if [ "$dry_run" = "true" ]; then
        sed -E -e 's/^__version__[[:space:]]*=.*/__version__ = "'"$new_version"'"/' asteroidpy/version.py | head -3
    else
        sed -i -E 's/^__version__[[:space:]]*=.*/__version__ = "'"$new_version"'"/' asteroidpy/version.py
    fi
    
    # setup.py
    if grep -q 'version=' setup.py; then
        if [ "$dry_run" = "true" ]; then
            sed -e "s/version=.*/version='$new_version',/" setup.py | head -5
        else
            sed -i "s/version=.*/version='$new_version',/" setup.py
        fi
    fi
    
    success "Version updated to $new_version"
}

# Aggiorna CHANGELOG
update_changelog() {
    local new_version=$1
    local dry_run=$2
    local date=$(date +%Y-%m-%d)
    
    info "Updating CHANGELOG.md..."
    
    local changelog_entry="## [$new_version] - $date

### Added
- 

### Changed
- 

### Fixed
- 

---

"
    
    if [ "$dry_run" = "true" ]; then
        echo "CHANGELOG.md would be updated with:"
        echo "$changelog_entry"
    else
        # Inserisci all'inizio del file (dopo il primo heading)
        sed -i "/^# Release History/a \\
$changelog_entry" CHANGELOG.md || {
            # Se non trova il pattern, inserisci all'inizio
            temp=$(mktemp)
            echo "$changelog_entry" > "$temp"
            cat CHANGELOG.md >> "$temp"
            mv "$temp" CHANGELOG.md
        }
    fi
    
    success "CHANGELOG.md updated"
}

# Crea commit
create_commit() {
    local version=$1
    local dry_run=$2
    
    info "Creating release commit..."
    
    if [ "$dry_run" = "true" ]; then
        echo "Would run:"
        echo "  git add asteroidpy/version.py setup.py CHANGELOG.md"
        echo "  git commit -m 'chore: release v$version'"
    else
        git add asteroidpy/version.py setup.py CHANGELOG.md
        git commit -m "chore: release v$version"
        success "Commit created"
    fi
}

# Crea tag
create_tag() {
    local version=$1
    local dry_run=$2
    
    info "Creating git tag..."
    
    if [ "$dry_run" = "true" ]; then
        echo "Would run:"
        echo "  git tag -a v$version -m 'Release version $version'"
        echo "  git push origin main v$version"
    else
        # Crea tag annotato
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
        echo "  git push origin main"
        if [ "$no_tag" != "true" ]; then
            echo "  git push origin v$version"
        fi
    else
        git push origin main
        if [ "$no_tag" != "true" ]; then
            git push origin "v$version"
        fi
        success "Changes pushed to origin"
    fi
}

# Main
main() {
    print_banner
    
    local new_version=""
    local dry_run=false
    local no_tag=false
    local push_only=false
    
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
    
    # Recupero versione attuale se non specificata
    if [ -z "$new_version" ]; then
        current=$(get_current_version)
        error "No version specified. Current version: $current\nRun with --help for usage"
    fi
    
    # Valida versione
    validate_version "$new_version"
    
    # Info
    current_version=$(get_current_version)
    info "Current version: $current_version"
    info "New version: $new_version"
    
    if [ "$dry_run" = "true" ]; then
        warning "DRY RUN MODE - no changes will be made"
    fi
    
    # Se push_only, salta la validazione e aggiornamento
    if [ "$push_only" = "true" ]; then
        info "Push-only mode: skipping validation and updates"
        push_changes "$new_version" "$dry_run" "$no_tag"
        success "Tag pushed"
        return 0
    fi
    
    # Validazione
    validate_repo
    
    # Aggiornamenti
    update_version "$new_version" "$dry_run"
    update_changelog "$new_version" "$dry_run"
    create_commit "$new_version" "$dry_run"

    # Coerenza con Jenkins: il tag deve puntare al commit che contiene __version__
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
        echo "  1. Jenkins will automatically detect the tag and run the pipeline"
        echo "  2. Package will be built and published to PyPI"
        echo "  3. Monitor the build at: https://jenkins.example.com/job/asteroidpy-publish/"
        echo ""
        info "Release process initiated! 🚀"
    fi
}

# Esegui
main "$@"
