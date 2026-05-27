#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1
#
# kdevops plugin management script
#
# Manages installation, removal, and listing of kdevops plugins.
# Plugins can come from:
#   - Git repositories (with .kdevops/ directory)
#   - Local directories (with .kdevops/ directory)
#   - Compressed tarballs (.kdevops.tar.xz or .kdevops-VERSION.tar.xz)
#
# Usage:
#   kdevops-plugin.sh list                    - List installed plugins
#   kdevops-plugin.sh evaluate URL|PATH       - Show available versions
#   kdevops-plugin.sh add URL|PATH [VERSION]  - Install plugin
#   kdevops-plugin.sh remove NAME             - Uninstall plugin
#   kdevops-plugin.sh update NAME             - Update plugin to latest
#   kdevops-plugin.sh --has-plugins           - Check if any plugins installed (for Kconfig)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KDEVOPS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Plugin installation directory
PLUGINS_BASE_DIR="${HOME}/.config/kdevops"
PLUGINS_DIR="${PLUGINS_BASE_DIR}/plugins"
PLUGINS_REGISTRY="${PLUGINS_BASE_DIR}/plugins.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Ensure jq is available (needed for JSON handling)
check_dependencies() {
    if ! command -v jq &> /dev/null; then
        log_error "jq is required but not installed. Please install jq."
        exit 1
    fi
    if ! command -v git &> /dev/null; then
        log_error "git is required but not installed."
        exit 1
    fi
}

# Initialize the plugins directory and registry
init_plugins_dir() {
    mkdir -p "${PLUGINS_DIR}"
    if [ ! -f "${PLUGINS_REGISTRY}" ]; then
        echo '{"version": 1, "plugins": {}}' > "${PLUGINS_REGISTRY}"
    fi
}

# Read plugin manifest
read_manifest() {
    local plugin_dir="$1"
    local manifest="${plugin_dir}/plugin.yaml"

    if [ ! -f "${manifest}" ]; then
        log_error "No plugin.yaml found in ${plugin_dir}"
        return 1
    fi

    # Use python or yq if available, fall back to simple parsing
    if command -v python3 &> /dev/null; then
        python3 -c "
import yaml
import json
import sys
with open('${manifest}', 'r') as f:
    data = yaml.safe_load(f)
    print(json.dumps(data))
" 2>/dev/null || {
            # PyYAML not installed, try yq
            if command -v yq &> /dev/null; then
                yq -o json "${manifest}"
            else
                log_error "Need python3 with PyYAML or yq to parse plugin.yaml"
                return 1
            fi
        }
    elif command -v yq &> /dev/null; then
        yq -o json "${manifest}"
    else
        log_error "Need python3 with PyYAML or yq to parse plugin.yaml"
        return 1
    fi
}

# Get plugin name from manifest
get_plugin_name() {
    local manifest_json="$1"
    echo "${manifest_json}" | jq -r '.metadata.name // empty'
}

# Get plugin version from manifest
get_plugin_version() {
    local manifest_json="$1"
    echo "${manifest_json}" | jq -r '.metadata.version // "0.0.0"'
}

# Check if source is a git URL
is_git_url() {
    local source="$1"
    if [[ "${source}" =~ ^https?:// ]] || [[ "${source}" =~ ^git@ ]] || [[ "${source}" =~ ^ssh:// ]]; then
        return 0
    fi
    return 1
}

# Check if source is a tarball
is_tarball() {
    local source="$1"
    if [[ "${source}" =~ \.tar\.(xz|gz|bz2)$ ]] || [[ "${source}" =~ \.tgz$ ]]; then
        return 0
    fi
    return 1
}

# Extract version from tarball name (e.g., .kdevops-1.0.0.tar.xz -> 1.0.0)
extract_tarball_version() {
    local tarball="$1"
    local basename
    basename=$(basename "${tarball}")
    if [[ "${basename}" =~ \.kdevops-([0-9]+\.[0-9]+\.[0-9]+[^.]*)\. ]]; then
        echo "${BASH_REMATCH[1]}"
    else
        echo ""
    fi
}

# List available versions from a git repository
list_git_versions() {
    local git_url="$1"
    local tmpdir
    tmpdir=$(mktemp -d)
    trap "rm -rf ${tmpdir}" EXIT

    log_info "Fetching version information from ${git_url}..."

    # Clone with minimal depth to get tags
    if ! git clone --bare --filter=blob:none "${git_url}" "${tmpdir}/repo.git" 2>/dev/null; then
        log_error "Failed to access repository: ${git_url}"
        return 1
    fi

    echo "Available versions (git tags):"
    git --git-dir="${tmpdir}/repo.git" tag -l 'v*' | sort -V | while read -r tag; do
        echo "  ${tag}"
    done

    echo ""
    echo "Branches:"
    git --git-dir="${tmpdir}/repo.git" branch -r | grep -v HEAD | sed 's/origin\//  /'

    rm -rf "${tmpdir}"
    trap - EXIT
}

# List available versions from a directory (look for .kdevops-*.tar.xz files)
list_dir_versions() {
    local dir="$1"

    if [ ! -d "${dir}" ]; then
        log_error "Directory does not exist: ${dir}"
        return 1
    fi

    echo "Available versions:"

    # Check for versioned tarballs
    local found_versions=false
    for tarball in "${dir}"/.kdevops-*.tar.xz "${dir}"/.kdevops-*.tar.gz; do
        if [ -f "${tarball}" ]; then
            local version
            version=$(extract_tarball_version "${tarball}")
            if [ -n "${version}" ]; then
                echo "  ${version} ($(basename "${tarball}"))"
                found_versions=true
            fi
        fi
    done

    # Check for .kdevops directory (latest)
    if [ -d "${dir}/.kdevops" ]; then
        if [ -f "${dir}/.kdevops/plugin.yaml" ]; then
            local manifest_json
            manifest_json=$(read_manifest "${dir}/.kdevops")
            local version
            version=$(get_plugin_version "${manifest_json}")
            echo "  ${version} (from .kdevops/ directory - latest)"
            found_versions=true
        fi
    fi

    # Check for unversioned tarball
    if [ -f "${dir}/.kdevops.tar.xz" ]; then
        echo "  latest (.kdevops.tar.xz)"
        found_versions=true
    fi

    if [ "${found_versions}" = "false" ]; then
        log_warn "No plugin versions found in ${dir}"
        log_info "Expected: .kdevops/ directory, .kdevops.tar.xz, or .kdevops-VERSION.tar.xz"
    fi
}

# Check if URL is a GitHub URL
is_github_url() {
    local url="$1"
    [[ "${url}" =~ ^https://github\.com/ ]]
}

# Extract owner/repo from GitHub URL
parse_github_url() {
    local url="$1"
    url="${url%.git}"
    echo "${url}" | sed 's|https://github.com/||'
}

# Extract plugin from GitHub using curl (faster than git clone)
extract_from_github() {
    local git_url="$1"
    local version="${2:-}"
    local dest_dir="$3"

    local owner_repo
    owner_repo=$(parse_github_url "${git_url}")

    local tmpdir
    tmpdir=$(mktemp -d)
    trap "rm -rf ${tmpdir}" EXIT

    local ref="${version:-main}"
    local tarball_url

    if [ -n "${version}" ]; then
        tarball_url="https://github.com/${owner_repo}/archive/refs/tags/${ref}.tar.gz"
    else
        tarball_url="https://github.com/${owner_repo}/archive/refs/heads/${ref}.tar.gz"
    fi

    log_info "Downloading from GitHub: ${owner_repo} (${ref})..."

    if ! curl -sfL "${tarball_url}" -o "${tmpdir}/archive.tar.gz" 2>/dev/null; then
        # Try with 'v' prefix if version doesn't start with 'v'
        if [ -n "${version}" ] && [[ ! "${ref}" =~ ^v ]]; then
            ref="v${version}"
            tarball_url="https://github.com/${owner_repo}/archive/refs/tags/${ref}.tar.gz"
            log_info "Trying version '${ref}'..."
            if ! curl -sfL "${tarball_url}" -o "${tmpdir}/archive.tar.gz" 2>/dev/null; then
                log_error "Version '${version}' not found"
                log_info "Use 'make kdevops-plugin-evaluate ${git_url}' to see available versions"
                rm -rf "${tmpdir}"
                trap - EXIT
                return 1
            fi
        else
            log_error "Failed to download from: ${tarball_url}"
            rm -rf "${tmpdir}"
            trap - EXIT
            return 1
        fi
    fi

    tar -xzf "${tmpdir}/archive.tar.gz" -C "${tmpdir}"

    local extracted_dir
    extracted_dir=$(find "${tmpdir}" -maxdepth 1 -type d -name "${owner_repo##*/}-*" | head -1)

    if [ -z "${extracted_dir}" ] || [ ! -d "${extracted_dir}/.kdevops" ]; then
        log_error "No .kdevops directory found in repository"
        rm -rf "${tmpdir}"
        trap - EXIT
        return 1
    fi

    cp -r "${extracted_dir}/.kdevops/." "${dest_dir}/"
    rm -rf "${tmpdir}"
    trap - EXIT
}

# Extract plugin from git repository (fallback for non-GitHub)
extract_from_git() {
    local git_url="$1"
    local version="${2:-}"
    local dest_dir="$3"

    # Use faster GitHub-specific method if applicable
    if is_github_url "${git_url}"; then
        extract_from_github "${git_url}" "${version}" "${dest_dir}"
        return $?
    fi

    local tmpdir
    tmpdir=$(mktemp -d)
    trap "rm -rf ${tmpdir}" EXIT

    log_info "Cloning repository..."

    local git_ref="${version:-}"

    if [ -n "${git_ref}" ]; then
        if ! git clone --depth 1 --branch "${git_ref}" "${git_url}" "${tmpdir}/repo" 2>/dev/null; then
            if [[ ! "${git_ref}" =~ ^v ]]; then
                log_info "Trying 'v${git_ref}'..."
                git clone --depth 1 --branch "v${git_ref}" "${git_url}" "${tmpdir}/repo" 2>/dev/null || {
                    log_error "Version '${git_ref}' not found"
                    rm -rf "${tmpdir}"
                    trap - EXIT
                    return 1
                }
            else
                log_error "Version '${git_ref}' not found"
                rm -rf "${tmpdir}"
                trap - EXIT
                return 1
            fi
        fi
    else
        git clone --depth 1 "${git_url}" "${tmpdir}/repo" 2>/dev/null || {
            log_error "Failed to clone repository"
            rm -rf "${tmpdir}"
            trap - EXIT
            return 1
        }
    fi

    if [ ! -d "${tmpdir}/repo/.kdevops" ]; then
        log_error "No .kdevops directory found in repository"
        rm -rf "${tmpdir}"
        trap - EXIT
        return 1
    fi

    cp -r "${tmpdir}/repo/.kdevops/." "${dest_dir}/"
    rm -rf "${tmpdir}"
    trap - EXIT
}

# Extract plugin from tarball
extract_from_tarball() {
    local tarball="$1"
    local dest_dir="$2"

    log_info "Extracting tarball..."

    local tmpdir
    tmpdir=$(mktemp -d)
    trap "rm -rf ${tmpdir}" EXIT

    # Determine compression type and extract
    case "${tarball}" in
        *.tar.xz)
            tar -xJf "${tarball}" -C "${tmpdir}"
            ;;
        *.tar.gz|*.tgz)
            tar -xzf "${tarball}" -C "${tmpdir}"
            ;;
        *.tar.bz2)
            tar -xjf "${tarball}" -C "${tmpdir}"
            ;;
        *)
            log_error "Unsupported archive format: ${tarball}"
            return 1
            ;;
    esac

    # Find the .kdevops directory or assume root is plugin content
    if [ -d "${tmpdir}/.kdevops" ]; then
        cp -r "${tmpdir}/.kdevops/." "${dest_dir}/"
    elif [ -f "${tmpdir}/plugin.yaml" ]; then
        cp -r "${tmpdir}/." "${dest_dir}/"
    else
        # Look for .kdevops in subdirectory
        local found=false
        for subdir in "${tmpdir}"/*; do
            if [ -d "${subdir}/.kdevops" ]; then
                cp -r "${subdir}/.kdevops/." "${dest_dir}/"
                found=true
                break
            fi
        done
        if [ "${found}" = "false" ]; then
            log_error "Could not find plugin content in tarball"
            rm -rf "${tmpdir}"
            trap - EXIT
            return 1
        fi
    fi

    rm -rf "${tmpdir}"
    trap - EXIT
}

# Extract plugin from local directory
extract_from_dir() {
    local source_dir="$1"
    local version="${2:-}"
    local dest_dir="$3"

    # Check for versioned tarball first
    if [ -n "${version}" ]; then
        for tarball in "${source_dir}/.kdevops-${version}.tar.xz" \
                       "${source_dir}/.kdevops-${version}.tar.gz"; do
            if [ -f "${tarball}" ]; then
                extract_from_tarball "${tarball}" "${dest_dir}"
                return $?
            fi
        done
        log_warn "Version ${version} tarball not found, using .kdevops directory"
    fi

    # Check for .kdevops directory
    if [ -d "${source_dir}/.kdevops" ]; then
        cp -r "${source_dir}/.kdevops/." "${dest_dir}/"
        return 0
    fi

    # Check for unversioned tarball
    for tarball in "${source_dir}/.kdevops.tar.xz" "${source_dir}/.kdevops.tar.gz"; do
        if [ -f "${tarball}" ]; then
            extract_from_tarball "${tarball}" "${dest_dir}"
            return $?
        fi
    done

    log_error "No .kdevops directory or tarball found in ${source_dir}"
    return 1
}

# Add plugin to registry
register_plugin() {
    local name="$1"
    local version="$2"
    local source="$3"
    local ref="${4:-}"

    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    local tmpfile
    tmpfile=$(mktemp)

    jq --arg name "${name}" \
       --arg version "${version}" \
       --arg source "${source}" \
       --arg ref "${ref}" \
       --arg timestamp "${timestamp}" \
       --arg path "${PLUGINS_DIR}/${name}" \
       '.plugins[$name] = {
           "version": $version,
           "installed": $timestamp,
           "source": $source,
           "ref": $ref,
           "path": $path
       }' "${PLUGINS_REGISTRY}" > "${tmpfile}"

    mv "${tmpfile}" "${PLUGINS_REGISTRY}"
}

# Remove plugin from registry
unregister_plugin() {
    local name="$1"

    local tmpfile
    tmpfile=$(mktemp)

    jq --arg name "${name}" 'del(.plugins[$name])' "${PLUGINS_REGISTRY}" > "${tmpfile}"
    mv "${tmpfile}" "${PLUGINS_REGISTRY}"
}

# Generate the combined Kconfig for all plugins
generate_plugins_kconfig() {
    local kconfig_file="${PLUGINS_BASE_DIR}/Kconfig.plugins"

    cat > "${kconfig_file}" << 'EOF'
# SPDX-License-Identifier: copyleft-next-0.3.1
# Auto-generated by kdevops-plugin.sh - DO NOT EDIT
#
# This file sources all installed kdevops plugins

EOF

    local plugin_count=0
    for plugin_dir in "${PLUGINS_DIR}"/*; do
        if [ -d "${plugin_dir}" ] && [ -f "${plugin_dir}/Kconfig" ]; then
            local plugin_name
            plugin_name=$(basename "${plugin_dir}")
            echo "# Plugin: ${plugin_name}" >> "${kconfig_file}"
            echo "source \"${plugin_dir}/Kconfig\"" >> "${kconfig_file}"
            echo "" >> "${kconfig_file}"
            ((plugin_count++)) || true
        fi
    done

    if [ ${plugin_count} -eq 0 ]; then
        echo "# No plugins installed" >> "${kconfig_file}"
    fi

    log_info "Generated ${kconfig_file} with ${plugin_count} plugin(s)"
}

# Generate the combined Makefile for all plugins
generate_plugins_makefile() {
    local makefile="${PLUGINS_BASE_DIR}/Makefile.plugins"

    cat > "${makefile}" << 'EOF'
# SPDX-License-Identifier: copyleft-next-0.3.1
# Auto-generated by kdevops-plugin.sh - DO NOT EDIT
#
# This file includes all installed kdevops plugins

EOF

    local plugin_count=0
    for plugin_dir in "${PLUGINS_DIR}"/*; do
        if [ -d "${plugin_dir}" ] && [ -f "${plugin_dir}/Makefile" ]; then
            local plugin_name
            plugin_name=$(basename "${plugin_dir}")
            echo "# Plugin: ${plugin_name}" >> "${makefile}"
            echo "include ${plugin_dir}/Makefile" >> "${makefile}"
            echo "" >> "${makefile}"
            ((plugin_count++)) || true
        fi
    done

    if [ ${plugin_count} -eq 0 ]; then
        echo "# No plugins installed" >> "${makefile}"
    fi
}

# Regenerate the user Kconfig to source plugins
update_user_kconfig() {
    local user_kconfig="${PLUGINS_BASE_DIR}/Kconfig"

    # Check if Kconfig.plugins exists
    if [ ! -f "${PLUGINS_BASE_DIR}/Kconfig.plugins" ]; then
        generate_plugins_kconfig
    fi

    # Create or update user Kconfig to source plugins
    if [ ! -f "${user_kconfig}" ]; then
        cat > "${user_kconfig}" << EOF
# SPDX-License-Identifier: copyleft-next-0.3.1
# User kdevops configuration
#
# This file is auto-managed for plugin support.
# You can add your own configurations below the plugin source line.

# Source installed plugins
source "${PLUGINS_BASE_DIR}/Kconfig.plugins"
EOF
    else
        # Check if plugins are already sourced
        if ! grep -q "Kconfig.plugins" "${user_kconfig}"; then
            # Prepend plugin source
            local tmpfile
            tmpfile=$(mktemp)
            echo "# Source installed plugins" > "${tmpfile}"
            echo "source \"${PLUGINS_BASE_DIR}/Kconfig.plugins\"" >> "${tmpfile}"
            echo "" >> "${tmpfile}"
            cat "${user_kconfig}" >> "${tmpfile}"
            mv "${tmpfile}" "${user_kconfig}"
        fi
    fi
}

# Update user Makefile to include plugins
update_user_makefile() {
    local user_makefile="${PLUGINS_BASE_DIR}/Makefile"

    # Check if Makefile.plugins exists
    if [ ! -f "${PLUGINS_BASE_DIR}/Makefile.plugins" ]; then
        generate_plugins_makefile
    fi

    # Create or update user Makefile
    if [ ! -f "${user_makefile}" ]; then
        cat > "${user_makefile}" << EOF
# SPDX-License-Identifier: copyleft-next-0.3.1
# User kdevops Makefile
#
# This file is auto-managed for plugin support.
# You can add your own targets below the plugin include line.

# Include installed plugins
include ${PLUGINS_BASE_DIR}/Makefile.plugins
EOF
    else
        # Check if plugins are already included
        if ! grep -q "Makefile.plugins" "${user_makefile}"; then
            # Prepend plugin include
            local tmpfile
            tmpfile=$(mktemp)
            echo "# Include installed plugins" > "${tmpfile}"
            echo "include ${PLUGINS_BASE_DIR}/Makefile.plugins" >> "${tmpfile}"
            echo "" >> "${tmpfile}"
            cat "${user_makefile}" >> "${tmpfile}"
            mv "${tmpfile}" "${user_makefile}"
        fi
    fi
}

# Command: list installed plugins
cmd_list() {
    init_plugins_dir

    local plugin_count
    plugin_count=$(jq '.plugins | length' "${PLUGINS_REGISTRY}")

    if [ "${plugin_count}" -eq 0 ]; then
        echo "No plugins installed."
        echo ""
        echo "To install a plugin:"
        echo "  make kdevops-plugin-add URL [VERSION]"
        echo ""
        echo "Example:"
        echo "  make kdevops-plugin-add https://github.com/mcgrof/knlp"
        return 0
    fi

    echo "Installed plugins:"
    echo ""
    printf "%-20s %-12s %-40s\n" "NAME" "VERSION" "SOURCE"
    printf "%-20s %-12s %-40s\n" "----" "-------" "------"

    jq -r '.plugins | to_entries[] | "\(.key)\t\(.value.version)\t\(.value.source)"' "${PLUGINS_REGISTRY}" | \
    while IFS=$'\t' read -r name version source; do
        printf "%-20s %-12s %-40s\n" "${name}" "${version}" "${source}"
    done
}

# Command: evaluate available versions
cmd_evaluate() {
    local source="$1"

    if [ -z "${source}" ]; then
        log_error "Usage: kdevops-plugin.sh evaluate URL|PATH"
        exit 1
    fi

    if is_git_url "${source}"; then
        list_git_versions "${source}"
    elif [ -d "${source}" ]; then
        list_dir_versions "${source}"
    elif is_tarball "${source}"; then
        local version
        version=$(extract_tarball_version "${source}")
        if [ -n "${version}" ]; then
            echo "Tarball version: ${version}"
        else
            echo "Tarball: latest (unversioned)"
        fi
    else
        log_error "Source must be a git URL, directory, or tarball: ${source}"
        exit 1
    fi
}

# Command: add/install plugin
cmd_add() {
    local source="$1"
    local version="${2:-}"

    if [ -z "${source}" ]; then
        log_error "Usage: kdevops-plugin.sh add URL|PATH [VERSION]"
        exit 1
    fi

    check_dependencies
    init_plugins_dir

    # Create temporary extraction directory
    local tmpdir
    tmpdir=$(mktemp -d)
    trap "rm -rf ${tmpdir}" EXIT

    log_info "Installing plugin from: ${source}"
    if [ -n "${version}" ]; then
        log_info "Requested version: ${version}"
    fi

    # Extract plugin based on source type
    if is_git_url "${source}"; then
        extract_from_git "${source}" "${version}" "${tmpdir}"
    elif is_tarball "${source}"; then
        extract_from_tarball "${source}" "${tmpdir}"
    elif [ -d "${source}" ]; then
        extract_from_dir "${source}" "${version}" "${tmpdir}"
    else
        log_error "Source must be a git URL, directory, or tarball: ${source}"
        exit 1
    fi

    # Read and validate manifest
    if [ ! -f "${tmpdir}/plugin.yaml" ]; then
        log_error "No plugin.yaml found - invalid plugin"
        exit 1
    fi

    local manifest_json
    manifest_json=$(read_manifest "${tmpdir}")
    local plugin_name
    plugin_name=$(get_plugin_name "${manifest_json}")
    local plugin_version
    plugin_version=$(get_plugin_version "${manifest_json}")

    if [ -z "${plugin_name}" ]; then
        log_error "Plugin manifest missing 'metadata.name'"
        exit 1
    fi

    log_info "Plugin: ${plugin_name} version ${plugin_version}"

    # Check if already installed
    local existing_version
    existing_version=$(jq -r --arg name "${plugin_name}" '.plugins[$name].version // empty' "${PLUGINS_REGISTRY}")
    if [ -n "${existing_version}" ]; then
        log_warn "Plugin ${plugin_name} is already installed (version ${existing_version})"
        read -p "Replace with version ${plugin_version}? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Installation cancelled"
            exit 0
        fi
        # Remove old installation
        rm -rf "${PLUGINS_DIR}/${plugin_name}"
    fi

    # Install plugin
    local install_dir="${PLUGINS_DIR}/${plugin_name}"
    mkdir -p "${install_dir}"
    cp -r "${tmpdir}/." "${install_dir}/"

    # Register plugin
    register_plugin "${plugin_name}" "${plugin_version}" "${source}" "${version}"

    # Regenerate Kconfig and Makefile
    generate_plugins_kconfig
    generate_plugins_makefile
    update_user_kconfig
    update_user_makefile

    rm -rf "${tmpdir}"
    trap - EXIT

    log_success "Plugin ${plugin_name} (${plugin_version}) installed successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Run 'make menuconfig' to enable the plugin"
    echo "  2. Look for the plugin under 'User-private workflows'"
    echo ""
    echo "To use with a defconfig, add the plugin's config fragment:"
    echo "  make defconfig-<base>+${plugin_name}"
}

# Command: remove/uninstall plugin
cmd_remove() {
    local plugin_name="$1"

    if [ -z "${plugin_name}" ]; then
        log_error "Usage: kdevops-plugin.sh remove PLUGIN_NAME"
        exit 1
    fi

    init_plugins_dir

    # Check if plugin exists
    local existing_version
    existing_version=$(jq -r --arg name "${plugin_name}" '.plugins[$name].version // empty' "${PLUGINS_REGISTRY}")
    if [ -z "${existing_version}" ]; then
        log_error "Plugin '${plugin_name}' is not installed"
        exit 1
    fi

    log_info "Removing plugin: ${plugin_name} (${existing_version})"

    # Remove plugin directory
    rm -rf "${PLUGINS_DIR}/${plugin_name}"

    # Unregister plugin
    unregister_plugin "${plugin_name}"

    # Regenerate Kconfig and Makefile
    generate_plugins_kconfig
    generate_plugins_makefile

    log_success "Plugin ${plugin_name} removed successfully!"
    echo ""
    echo "Note: You may need to reconfigure kdevops:"
    echo "  make menuconfig"
}

# Command: update plugin
cmd_update() {
    local plugin_name="$1"

    if [ -z "${plugin_name}" ]; then
        log_error "Usage: kdevops-plugin.sh update PLUGIN_NAME"
        exit 1
    fi

    init_plugins_dir

    # Check if plugin exists
    local plugin_info
    plugin_info=$(jq -r --arg name "${plugin_name}" '.plugins[$name] // empty' "${PLUGINS_REGISTRY}")
    if [ -z "${plugin_info}" ] || [ "${plugin_info}" = "null" ]; then
        log_error "Plugin '${plugin_name}' is not installed"
        exit 1
    fi

    local source
    source=$(echo "${plugin_info}" | jq -r '.source')
    local current_version
    current_version=$(echo "${plugin_info}" | jq -r '.version')

    log_info "Updating ${plugin_name} (current: ${current_version})"
    log_info "Source: ${source}"

    # Remove old and reinstall
    rm -rf "${PLUGINS_DIR}/${plugin_name}"

    # Reinstall from source (will get latest)
    cmd_add "${source}"
}

# Command: check if plugins installed (for Kconfig)
cmd_has_plugins() {
    if [ ! -f "${PLUGINS_REGISTRY}" ]; then
        echo "n"
        return
    fi

    local plugin_count
    plugin_count=$(jq '.plugins | length' "${PLUGINS_REGISTRY}" 2>/dev/null || echo "0")

    if [ "${plugin_count}" -gt 0 ]; then
        echo "y"
    else
        echo "n"
    fi
}

# Main command dispatcher
main() {
    local cmd="${1:-}"
    shift || true

    case "${cmd}" in
        list)
            cmd_list
            ;;
        evaluate)
            cmd_evaluate "$@"
            ;;
        add)
            cmd_add "$@"
            ;;
        remove)
            cmd_remove "$@"
            ;;
        update)
            cmd_update "$@"
            ;;
        --has-plugins)
            cmd_has_plugins
            ;;
        --help|-h|"")
            echo "kdevops plugin manager"
            echo ""
            echo "Usage: kdevops-plugin.sh COMMAND [OPTIONS]"
            echo ""
            echo "Commands:"
            echo "  list                    List installed plugins"
            echo "  evaluate URL|PATH       Show available versions from source"
            echo "  add URL|PATH [VERSION]  Install a plugin"
            echo "  remove NAME             Uninstall a plugin"
            echo "  update NAME             Update a plugin to latest"
            echo ""
            echo "Examples:"
            echo "  kdevops-plugin.sh add https://github.com/mcgrof/knlp"
            echo "  kdevops-plugin.sh add https://github.com/mcgrof/knlp v1.0.0"
            echo "  kdevops-plugin.sh add /path/to/project"
            echo "  kdevops-plugin.sh evaluate https://github.com/mcgrof/knlp"
            echo "  kdevops-plugin.sh list"
            echo "  kdevops-plugin.sh remove knlp"
            ;;
        *)
            log_error "Unknown command: ${cmd}"
            echo "Run 'kdevops-plugin.sh --help' for usage"
            exit 1
            ;;
    esac
}

main "$@"
