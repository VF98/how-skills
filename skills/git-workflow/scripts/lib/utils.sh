#!/bin/bash
# utils.sh - 工具函数库
# 提供日志输出、用户交互、进度显示等通用功能

# 颜色定义
readonly COLOR_RED='\033[0;31m'
readonly COLOR_GREEN='\033[0;32m'
readonly COLOR_YELLOW='\033[1;33m'
readonly COLOR_BLUE='\033[0;34m'
readonly COLOR_CYAN='\033[0;36m'
readonly COLOR_RESET='\033[0m'

# 日志函数
log_info() {
    echo -e "${COLOR_CYAN}ℹ${COLOR_RESET} $*"
}

log_success() {
    echo -e "${COLOR_GREEN}✓${COLOR_RESET} $*"
}

log_warning() {
    echo -e "${COLOR_YELLOW}⚠${COLOR_RESET} $*"
}

log_error() {
    echo -e "${COLOR_RED}✗${COLOR_RESET} $*" >&2
}

log_step() {
    echo -e "${COLOR_BLUE}▸${COLOR_RESET} $*"
}

# Spinner 进度显示
spinner_pid=""

start_spinner() {
    local message="$1"
    local delay=0.1
    local spinstr='|/-\'

    {
        while true; do
            for i in $(seq 0 3); do
                echo -ne "\r${COLOR_CYAN}${spinstr:$i:1}${COLOR_RESET} $message"
                sleep $delay
            done
        done
    } &
    spinner_pid=$!
}

stop_spinner() {
    if [ -n "$spinner_pid" ]; then
        kill "$spinner_pid" 2>/dev/null
        spinner_pid=""
        echo -ne "\r\033[K"  # 清除当前行
    fi
}

# 检测是否为交互式终端
is_interactive() {
    [ -t 0 ]
}

# 是/否询问函数
# 返回 0 (yes) 或 1 (no)
ask_yes_no() {
    local prompt="$1"
    local default="${2:-n}"

    # 非交互式环境直接返回默认值
    if ! is_interactive; then
        if [ "$default" = "y" ]; then
            return 0
        else
            return 1
        fi
    fi

    local default_str
    if [ "$default" = "y" ]; then
        default_str="[Y/n]"
    else
        default_str="[y/N]"
    fi

    while true; do
        read -t 30 -p "$prompt $default_str: " response || {
            # 超时或无输入，使用默认值
            echo ""
            if [ "$default" = "y" ]; then
                return 0
            else
                return 1
            fi
        }
        response="${response:-$default}"

        case "$response" in
            [Yy]|[Yy][Ee][Ss])
                return 0
                ;;
            [Nn]|[Nn][Oo])
                return 1
                ;;
            *)
                log_error "Please answer yes or no"
                ;;
        esac
    done
}

# 多选询问函数
# 参数: prompt option1 option2 ...
# 返回选择的数字
ask_choice() {
    local prompt="$1"
    shift
    local options=("$@")

    echo ""
    log_info "$prompt"
    echo ""

    for i in "${!options[@]}"; do
        echo "[$((i + 1))] ${options[$i]}"
    done
    echo ""

    # 非交互式环境返回默认选项 1
    if ! is_interactive; then
        log_warning "Non-interactive mode, selecting option 1: ${options[0]}"
        return 1
    fi

    local choice
    local max_attempts=3
    local attempts=0

    while [ $attempts -lt $max_attempts ]; do
        read -t 30 -p "Enter your choice [1-${#options[@]}]: " choice || {
            # 超时，使用默认选项 1
            echo ""
            log_warning "Timeout, selecting option 1: ${options[0]}"
            return 1
        }

        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#options[@]}" ]; then
            return "$choice"
        else
            attempts=$((attempts + 1))
            if [ $attempts -lt $max_attempts ]; then
                log_error "Invalid choice. Please enter a number between 1 and ${#options[@]}"
            else
                # 超过最大尝试次数，使用默认选项 1
                log_warning "Too many attempts, selecting option 1: ${options[0]}"
                return 1
            fi
        fi
    done
}

# 检测命令是否存在
command_exists() {
    command -v "$1" &>/dev/null
}

# 获取命令版本
get_version() {
    local cmd="$1"
    if command_exists "$cmd"; then
        "$cmd" --version 2>&1 | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1
    else
        echo "not found"
    fi
}

# 检测操作系统
detect_os() {
    case "$(uname -s)" in
        Linux*)
            echo "linux"
            ;;
        Darwin*)
            echo "macos"
            ;;
        CYGWIN*|MINGW*|MSYS*)
            echo "windows"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

# 检测包管理器
detect_package_manager() {
    if command_exists apt; then
        echo "apt"
    elif command_exists brew; then
        echo "brew"
    elif command_exists yum; then
        echo "yum"
    elif command_exists dnf; then
        echo "dnf"
    else
        echo "unknown"
    fi
}

# 检测系统架构
detect_arch() {
    case "$(uname -m)" in
        x86_64|amd64)
            echo "amd64"
            ;;
        aarch64|arm64)
            echo "arm64"
            ;;
        i386|i686)
            echo "386"
            ;;
        armv6l)
            echo "armv6"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

# 从 remote -v 行中提取 URL
extract_remote_url() {
    local remote="$1"

    if [ -z "$remote" ]; then
        echo ""
        return
    fi

    if [[ "$remote" == *" (push)" ]] || [[ "$remote" == *" (fetch)" ]]; then
        echo "$remote" | awk '{print $2}'
    else
        echo "$remote"
    fi
}

# 从 URL 中提取 host
extract_url_host() {
    local value="$1"

    if [ -z "$value" ]; then
        echo ""
        return
    fi

    if [[ "$value" =~ ^git@([^:]+): ]]; then
        echo "${BASH_REMATCH[1]}"
    elif [[ "$value" =~ ^[a-zA-Z]+://([^/]+) ]]; then
        echo "${BASH_REMATCH[1]}"
    elif [[ "$value" =~ ^([^/]+)/ ]]; then
        echo "${BASH_REMATCH[1]}"
    else
        echo ""
    fi
}

# 从 git remote 信息中提取 host
extract_remote_host() {
    extract_url_host "$(extract_remote_url "$1")"
}

# 从 GITLAB_URL 中提取 host
get_env_gitlab_host() {
    extract_url_host "${GITLAB_URL:-}"
}

# 格式化状态显示
format_status() {
    local name="$1"
    local installed="$2"
    local version="$3"

    if [ "$installed" = "true" ]; then
        printf "  %-20s  ${COLOR_GREEN}%-12s${COLOR_RESET}  %s\n" "$name" "Installed" "$version"
    else
        printf "  %-20s  ${COLOR_RED}%-12s${COLOR_RESET}  %s\n" "$name" "Not found" ""
    fi
}

# 显示分割线
separator() {
    local width=60
    local char="${1:-─}"
    printf "$(printf '%*s' "$width" | tr ' ' "$char")\n"
}

# 检查是否在 git 仓库中
is_git_repo() {
    [ -d ".git" ] || git rev-parse --git-dir &>/dev/null
}

# 检测活跃的 git remote
get_active_remote() {
    git remote -v 2>/dev/null | grep "(push)" | head -1
}
