---
name: git-workflow
description: Multi-platform Git workflow for GitHub and GitLab. Use when you need to review code changes, generate conventional commit messages, push to remote, and create or update Pull Requests (GitHub) or Merge Requests (GitLab). Triggers on tasks involving git commit, git push, PR creation, MR creation, code review, or workflow automation.
license: MIT
metadata:
  author: make-fe-great-again
  version: "1.0.0"
---

> 来源声明：[make-fe-great-again / gitlab-skill-workflow](https://github.com/make-fe-great-again/gitlab-skill-workflow)，原文标注 MIT。上游目前无法核实，保留原声明作私人归档；详见 [PROVENANCE.json](PROVENANCE.json)。

## Post-Installation Setup (Required for GitLab)

After installing this skill, run the setup script to install dependencies and authenticate:

```bash
bash scripts/setup.sh
```

> **Note**: Without this setup, GitLab MRs will only have a title (no description). The setup script will install `glab` CLI and guide you through authentication for full MR template support.

## What I do

- **Review Changes**: Analyze code changes for quality, potential bugs, and improvements
- **Generate Commit Messages**: Create conventional commit messages following best practices
- **Push to Remote**: Push changes to remote repository
- **Create/Update PRs/MRs**: Create or update GitHub Pull Requests or GitLab Merge Requests
- **Custom Templates**: Support platform-specific custom PR/MR description templates

## When to use me

Use when you need to:
- Complete a full git workflow from changes to PR/MR
- Ensure consistent commit message format
- Automate PR/MR creation with proper descriptions
- Apply code review best practices
- Work seamlessly with both GitHub and GitLab repositories

## How I work

### 1. Dependency Check

First, I'll check if required tools are installed:
- `git` - Required for all operations
- `gh` - Required for GitHub repositories (no push options alternative)
- `glab` - Optional for GitLab (can use `git push -o` instead)

**Platform differences:**
| Platform | CLI Tool | Required? | Alternative |
|----------|----------|-----------|-------------|
| GitHub | `gh` | Yes | None |
| GitLab | `glab` | Recommended | `git push -o` (limited) |

**Important GitLab limitation:**
`git push -o` does NOT support multi-line descriptions due to Git's restriction:
> fatal: push options must not have new line characters

This means MR templates with checklists, sections, etc. **cannot** be used with `git push -o`. To use full MR templates, install and authenticate `glab` CLI via `bash scripts/setup.sh`.

If you need to install dependencies, run:
```bash
bash scripts/setup.sh
```

This will:
- Check installed dependencies
- Offer interactive installation options
- Guide you through platform authentication

### 2. Platform Detection

I automatically detect your platform by:
1. Checking the active git remote host for `github.com`, `gitlab.com`, or a self-hosted GitLab host
2. Matching the remote host against `GITLAB_URL` when you use a private GitLab domain such as `git.example.com`
3. Checking for `.github/` or `.gitlab/` directories
4. Using the active remote as primary if both platforms are present

### 3. Review Changes

Run `git status` and `git diff` to:
- Analyze changed files and their types
- Identify potential code quality issues
- Check for missing lint/typecheck commands
- Generate a review report

### 4. Generate Commit Message

Analyze changes to create a conventional commit message:
- Format: `<type>(<scope>): <description>`
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- Identify scope based on changed files
- Generate concise, clear description

Example:
```
feat(auth): add JWT token validation
fix(api): handle null response in user endpoint
docs(readme): update installation instructions
```

### 5. Commit and Push

1. Ask for confirmation of commit message
2. Run `git commit` with the generated message
3. Run `git push` to remote repository
4. Handle upstream setup if needed

### 6. Create/Update PR or MR

**For GitHub:**
```bash
# Check for existing PR
gh pr list --head $CURRENT_BRANCH

# Create new PR
gh pr create --title "$TITLE" --body "$BODY" --base $BASE

# Update existing PR
gh pr edit $PR_NUMBER --body "$BODY"
```

**For GitLab:**

First, check if glab is authenticated:
```bash
glab auth status --hostname <your-gitlab-host>
```

**If glab is authenticated (recommended):**
```bash
# Check for existing MR
glab mr list --source-branch $CURRENT_BRANCH

# Create new MR with full template support
glab mr create --title "$TITLE" --description "$BODY" --target-branch $BASE

# Update existing MR
glab mr edit $MR_NUMBER --description "$BODY"
```

**If glab is NOT authenticated (fallback):**
```bash
# Create MR with push options (title only, no multi-line description)
git push -o merge_request.create \
         -o merge_request.target=$BASE \
         -o "merge_request.title=$TITLE" \
         origin $CURRENT_BRANCH

# Note: Description will be empty. User can edit in GitLab web UI.
# Available push options:
# -o merge_request.create              - Create MR
# -o merge_request.target=<branch>     - Set target branch
# -o merge_request.title="<title>"     - Set MR title
# -o merge_request.draft               - Mark as draft
# -o merge_request.merge_when_pipeline_succeeds - Auto-merge on CI pass
# -o merge_request.remove_source_branch - Delete branch after merge
```

### 7. Custom Templates

Support for platform-specific templates:

**GitHub** - Loads from:
1. `.github/pull_request_template.md` (recommended)
2. `.github/pr-template.md`

**GitLab** - Loads from:
1. `.gitlab/merge_request_templates/default.md` (recommended)
2. `.gitlab/mr-template.md`

> **Note for GitLab users:**
> - Full template support requires `glab` CLI (install via `bash scripts/setup.sh`)
> - With `git push -o`, only the title will be set; template content will be skipped

**Template Variables:**
- `${title}` - PR/MR title
- `${description}` - Commit message description
- `${changed_files}` - List of changed files
- `${review_notes}` - Code review observations
- `${platform}` - Platform name (GitHub/GitLab)
- `${branch}` - Current branch name
- `${base_branch}` - Target base branch

## Prerequisites

1. **Git** - Version control system (required)
   ```bash
   # Check installation
   git --version

   # Install if needed
   # Ubuntu/Debian: sudo apt install git
   # macOS: brew install git
   ```

2. **GitHub CLI (gh)** - For GitHub repositories
   ```bash
   # Check installation
   gh --version

   # Install
   curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
   sudo apt update && sudo apt install -y gh

   # Authenticate
   gh auth login
   ```

3. **GitLab CLI (glab)** - Recommended for GitLab repositories (for full MR template support)

   Official repository: https://gitlab.com/gitlab-org/cli

   ```bash
   # Check installation
   glab --version

   # Install (macOS)
   brew install glab

   # Install (Linux - Snap, recommended)
   sudo snap install glab

   # Install (Linux - Homebrew)
   brew install glab

   # Install (Windows)
   winget install glab.glab

   # Authenticate (gitlab.com)
   glab auth login

   # Authenticate (self-hosted, e.g., jihulab.com)
   glab auth login --hostname jihulab.com
   ```

   > **Note**: Without `glab`, MR descriptions will be empty (git push -o doesn't support multi-line content). Run `bash scripts/setup.sh` for guided installation and authentication.

## Quick Start

### Install the Skill

```bash
# Method 1: Clone and install
git clone https://github.com/make-fe-great-again/gitlab-skill-workflow.git
cd gitlab-skill-workflow
bash install.sh

# Method 2: Online installation
curl -fsSL https://raw.githubusercontent.com/make-fe-great-again/gitlab-skill-workflow/main/install.sh | bash
```

### Setup Dependencies

```bash
# Run interactive setup
bash scripts/setup.sh

# Follow the prompts to:
# 1. Check installed tools
# 2. Install missing dependencies
# 3. Authenticate with your platform
```

### Use the Skill

```bash
# In OpenCode conversation
skill({ name: "git-workflow" })
```

## Examples

### Example 1: Simple Feature

```
User: I just implemented user authentication
Agent: [Loads git-workflow skill]
     1. Review changes...
     2. Generate commit message: feat(auth): add JWT token validation
     3. Commit and push...
     4. Create PR with custom template...
```

### Example 2: Bug Fix

```
User: Fixed the null pointer exception in user service
Agent: [Loads git-workflow skill]
     1. Review changes...
     2. Generate commit message: fix(user-service): handle null response in user endpoint
     3. Commit and push...
     4. Update existing PR with new changes...
```

### Example 3: Documentation Update

```
User: Updated the README with installation instructions
Agent: [Loads git-workflow skill]
     1. Review changes...
     2. Generate commit message: docs(readme): update installation instructions
     3. Commit and push...
     4. Create PR with description from template...
```

## Platform-Specific Notes

### GitHub
- Uses `gh` CLI for all operations
- Supports GitHub Actions workflows
- PR templates should be in `.github/pull_request_template.md`
- Authentication: `gh auth login`

### GitLab

Two methods available for creating MRs:

**Method 1: `glab` CLI (recommended)**
- Full MR template support (multi-line descriptions, checklists, etc.)
- Can manage MRs, view status, add comments, assign reviewers
- Requires API authentication via Personal Access Token
- Run `bash scripts/setup.sh` for guided installation and authentication

**Method 2: `git push -o` (fallback)**
- Uses existing SSH/HTTPS authentication
- No extra tools needed
- **Limitation**: Does NOT support multi-line descriptions
- MR will be created with title only; description must be added manually in GitLab web UI

MR templates should be in `.gitlab/merge_request_templates/default.md`

### Supported GitLab Instances

| Instance Type | Hostname Example | Auth Command |
|--------------|------------------|--------------|
| GitLab.com | gitlab.com | `glab auth login` |
| JiHu GitLab | jihulab.com | `glab auth login --hostname jihulab.com` |
| Self-hosted | gitlab-ee.example.com | `glab auth login --hostname gitlab-ee.example.com` |
| Private company GitLab | git.example.com | `glab auth login --hostname git.example.com` |

Token creation URL (auto-selects required scopes):
```
https://<hostname>/-/user_settings/personal_access_tokens?scopes=api,write_repository
```

If your private GitLab host does not contain the word `gitlab`, export:

```bash
export GITLAB_URL="https://git.example.com"
```

This helps the setup flow treat the remote host as GitLab instead of `unknown`.

## Troubleshooting

**Issue: gh/glab command not found**
- Run `bash scripts/setup.sh` to install missing dependencies
- For GitLab, you can use `git push -o` instead of `glab`

**Issue: Authentication failed**
- Ensure you're logged in: `gh auth status` or `glab auth status`
- Re-authenticate if needed

**Issue: PR/MR creation failed**
- Check if branch is pushed to remote
- Verify base branch exists
- Ensure you have proper permissions

**Issue: Templates not loading**
- Verify template files exist in correct locations
- Check file permissions
- Ensure templates are markdown format

## Best Practices

1. **Commit Messages**: Follow conventional commits format
2. **Branch Names**: Use descriptive names (e.g., `feature/user-auth`, `fix/api-bug`)
3. **PR/MR Descriptions**: Use clear, detailed descriptions
4. **Code Review**: Always review changes before committing
5. **Testing**: Ensure tests pass before pushing

## Customization

### Modify Commit Message Format

The skill generates conventional commits by default. To customize:
1. Edit the skill instructions
2. Add your preferred format rules
3. Test with a small change first

### Custom PR/MR Templates

Create custom templates in your project:

**GitHub** - `.github/pull_request_template.md`:
```markdown
## Changes
${description}

## Files Changed
${changed_files}

## Review Notes
${review_notes}

## Checklist
- [ ] Tests pass
- [ ] Linting passes
- [ ] Documentation updated
```

**GitLab** - `.gitlab/merge_request_templates/default.md`:
```markdown
## Description
${description}

## Related Issues
${review_notes}

## Checklist
- [ ] Tests pass
- [ ] Pipeline passed
- [ ] Code review approved
```

## Integration

### With CI/CD

This skill integrates seamlessly with:
- GitHub Actions (GitHub)
- GitLab CI/CD (GitLab)
- Jenkins
- Any CI/CD system that supports git hooks

### With Git Hooks

Add pre-commit hooks to enforce quality:
```bash
# .git/hooks/pre-commit
#!/bin/bash
npm run lint
npm test
```

## Support

For issues, questions, or contributions:
- GitHub: https://github.com/make-fe-great-again/gitlab-skill-workflow
- Documentation: https://github.com/make-fe-great-again/gitlab-skill-workflow

## License

MIT License - See LICENSE file for details
