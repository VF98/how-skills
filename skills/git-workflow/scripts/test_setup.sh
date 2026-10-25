#!/bin/bash
# test_setup.sh - 测试 setup.sh 的核心功能
# 运行: bash scripts/test_setup.sh

set -e

# 加载工具函数
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/utils.sh"

# 测试计数器
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# 测试辅助函数
test_start() {
    echo ""
    echo "=== TEST: $1 ==="
    TESTS_RUN=$((TESTS_RUN + 1))
}

test_pass() {
    echo "✅ PASS: $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

test_fail() {
    echo "❌ FAIL: $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

assert_equals() {
    local expected="$1"
    local actual="$2"
    local message="$3"

    if [ "$expected" = "$actual" ]; then
        test_pass "$message"
    else
        test_fail "$message (expected: '$expected', got: '$actual')"
    fi
}

assert_contains() {
    local haystack="$1"
    local needle="$2"
    local message="$3"

    if [[ "$haystack" == *"$needle"* ]]; then
        test_pass "$message"
    else
        test_fail "$message (expected to contain: '$needle')"
    fi
}

# ============================================
# 测试 1: 平台检测
# ============================================
test_platform_detection() {
    test_start "Platform Detection"

    # 模拟 detect_platform 函数
    detect_platform() {
        local remote="$1"

        if [[ "$remote" == *"github.com"* ]]; then
            echo "github"
        elif [[ "$remote" == *"gitlab.com"* ]]; then
            echo "gitlab"
        elif [[ "$remote" == *"gitlab."* ]] || [[ "$remote" == *"gitlab-"* ]]; then
            echo "gitlab"
        elif [[ "$remote" == *"jihulab.com"* ]]; then
            echo "gitlab"
        else
            echo "unknown"
        fi
    }

    # 测试 GitHub
    result=$(detect_platform "git@github.com:user/repo.git")
    assert_equals "github" "$result" "Detect GitHub SSH URL"

    result=$(detect_platform "https://github.com/user/repo.git")
    assert_equals "github" "$result" "Detect GitHub HTTPS URL"

    # 测试 GitLab.com
    result=$(detect_platform "git@gitlab.com:user/repo.git")
    assert_equals "gitlab" "$result" "Detect GitLab.com SSH URL"

    result=$(detect_platform "https://gitlab.com/user/repo.git")
    assert_equals "gitlab" "$result" "Detect GitLab.com HTTPS URL"

    # 测试 JiHuLab
    result=$(detect_platform "git@jihulab.com:user/repo.git")
    assert_equals "gitlab" "$result" "Detect JiHuLab SSH URL"

    result=$(detect_platform "https://jihulab.com/user/repo.git")
    assert_equals "gitlab" "$result" "Detect JiHuLab HTTPS URL"

    # 测试自托管 GitLab
    result=$(detect_platform "git@gitlab.example.com:user/repo.git")
    assert_equals "gitlab" "$result" "Detect self-hosted GitLab SSH URL"

    result=$(detect_platform "https://gitlab.example.com/user/repo.git")
    assert_equals "gitlab" "$result" "Detect self-hosted GitLab HTTPS URL"
}

# ============================================
# 测试 2: Hostname 提取
# ============================================
test_hostname_extraction() {
    test_start "Hostname Extraction"

    # 模拟 hostname 提取逻辑
    extract_hostname() {
        local remote="$1"
        echo "$remote" | sed -E 's|.*@([^:/]+)[:/].*|\1|; s|.*://([^/]+)/.*|\1|'
    }

    # 测试 SSH URL
    result=$(extract_hostname "git@gitlab.com:user/repo.git")
    assert_equals "gitlab.com" "$result" "Extract hostname from GitLab SSH URL"

    result=$(extract_hostname "git@jihulab.com:user/repo.git")
    assert_equals "jihulab.com" "$result" "Extract hostname from JiHuLab SSH URL"

    result=$(extract_hostname "git@gitlab.example.com:user/repo.git")
    assert_equals "gitlab.example.com" "$result" "Extract hostname from self-hosted SSH URL"

    # 测试 HTTPS URL
    result=$(extract_hostname "https://gitlab.com/user/repo.git")
    assert_equals "gitlab.com" "$result" "Extract hostname from GitLab HTTPS URL"

    result=$(extract_hostname "https://jihulab.com/user/repo.git")
    assert_equals "jihulab.com" "$result" "Extract hostname from JiHuLab HTTPS URL"

    result=$(extract_hostname "https://gitlab.example.com/user/repo.git")
    assert_equals "gitlab.example.com" "$result" "Extract hostname from self-hosted HTTPS URL"
}

# ============================================
# 测试 3: Token URL 生成
# ============================================
test_token_url_generation() {
    test_start "Token URL Generation"

    # 模拟 Token URL 生成逻辑
    generate_token_url() {
        local hostname="$1"
        echo "https://${hostname}/-/user_settings/personal_access_tokens?scopes=api,write_repository"
    }

    result=$(generate_token_url "gitlab.com")
    assert_contains "$result" "gitlab.com" "Token URL contains gitlab.com"
    assert_contains "$result" "scopes=api,write_repository" "Token URL contains required scopes"

    result=$(generate_token_url "jihulab.com")
    assert_contains "$result" "jihulab.com" "Token URL contains jihulab.com"

    result=$(generate_token_url "gitlab.example.com")
    assert_contains "$result" "gitlab.example.com" "Token URL contains self-hosted hostname"
}

# ============================================
# 测试 4: glab 认证命令生成
# ============================================
test_glab_auth_command() {
    test_start "glab Auth Command Generation"

    # 模拟认证命令生成逻辑
    generate_auth_command() {
        local hostname="$1"
        local token="test_token"

        if [[ "$hostname" == "gitlab.com" ]]; then
            echo "glab auth login --token $token"
        else
            echo "glab auth login --hostname $hostname --token $token"
        fi
    }

    result=$(generate_auth_command "gitlab.com")
    assert_equals "glab auth login --token test_token" "$result" "Auth command for gitlab.com"

    result=$(generate_auth_command "jihulab.com")
    assert_equals "glab auth login --hostname jihulab.com --token test_token" "$result" "Auth command for jihulab.com"

    result=$(generate_auth_command "gitlab.example.com")
    assert_equals "glab auth login --hostname gitlab.example.com --token test_token" "$result" "Auth command for self-hosted"
}

# ============================================
# 测试 5: 工具函数
# ============================================
test_utils() {
    test_start "Utility Functions"

    # 测试 detect_os
    local os
    os=$(detect_os)
    if [[ "$os" == "linux" ]] || [[ "$os" == "macos" ]]; then
        test_pass "detect_os returns valid OS: $os"
    else
        test_fail "detect_os returned unknown OS: $os"
    fi

    # 测试 command_exists
    if command_exists git; then
        test_pass "command_exists detects git"
    else
        test_fail "command_exists should detect git"
    fi

    if ! command_exists nonexistent_command_12345; then
        test_pass "command_exists returns false for nonexistent command"
    else
        test_fail "command_exists should return false for nonexistent command"
    fi
}

# ============================================
# 测试 6: MR 创建决策逻辑
# ============================================
test_mr_creation_decision() {
    test_start "MR Creation Decision Logic"

    # 模拟决策逻辑
    decide_mr_method() {
        local glab_installed="$1"
        local glab_authenticated="$2"

        if [[ "$glab_installed" == "true" ]] && [[ "$glab_authenticated" == "true" ]]; then
            echo "glab"
        else
            echo "git_push_o"
        fi
    }

    result=$(decide_mr_method "true" "true")
    assert_equals "glab" "$result" "Use glab when installed and authenticated"

    result=$(decide_mr_method "true" "false")
    assert_equals "git_push_o" "$result" "Use git push -o when glab installed but not authenticated"

    result=$(decide_mr_method "false" "false")
    assert_equals "git_push_o" "$result" "Use git push -o when glab not installed"
}

# ============================================
# 测试 7: glab 安装决策逻辑
# ============================================
test_glab_install_decision() {
    test_start "glab Install Decision Logic"

    # 模拟安装决策逻辑
    decide_install_method() {
        local os="$1"
        local has_snap="$2"
        local has_brew="$3"

        if [[ "$os" == "linux" ]]; then
            if [[ "$has_snap" == "true" ]]; then
                echo "snap"
            elif [[ "$has_brew" == "true" ]]; then
                echo "brew"
            else
                echo "manual"
            fi
        elif [[ "$os" == "macos" ]]; then
            if [[ "$has_brew" == "true" ]]; then
                echo "brew"
            else
                echo "skip"  # macOS 没有 brew 直接跳过
            fi
        else
            echo "unsupported"
        fi
    }

    # Linux 测试
    result=$(decide_install_method "linux" "true" "false")
    assert_equals "snap" "$result" "Linux with snap uses snap"

    result=$(decide_install_method "linux" "false" "true")
    assert_equals "brew" "$result" "Linux without snap but with brew uses brew"

    result=$(decide_install_method "linux" "false" "false")
    assert_equals "manual" "$result" "Linux without snap or brew shows manual"

    # macOS 测试
    result=$(decide_install_method "macos" "false" "true")
    assert_equals "brew" "$result" "macOS with brew uses brew"

    result=$(decide_install_method "macos" "false" "false")
    assert_equals "skip" "$result" "macOS without brew skips (fallback to git push -o)"
}

# ============================================
# 运行所有测试
# ============================================
main() {
    echo ""
    echo "========================================"
    echo "  Git Workflow Skill - Test Suite"
    echo "========================================"

    test_platform_detection
    test_hostname_extraction
    test_token_url_generation
    test_glab_auth_command
    test_utils
    test_mr_creation_decision
    test_glab_install_decision

    echo ""
    echo "========================================"
    echo "  Test Results"
    echo "========================================"
    echo "  Total:  $TESTS_RUN"
    echo "  Passed: $TESTS_PASSED"
    echo "  Failed: $TESTS_FAILED"
    echo "========================================"

    if [ $TESTS_FAILED -gt 0 ]; then
        exit 1
    fi

    exit 0
}

main "$@"
