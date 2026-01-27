---
description: Extract activities and sub-activities from a planning markdown document and generate a gaant.yaml file
---

# Planning MD to Gaant YAML Workflow

This workflow extracts hierarchical activities from a planning markdown document and generates a `gaant.yaml` file ready for `gaant push`.

**Reference template:** Use `.agent/workflows/gaant_template.yaml` as the exact format example.

---

## Step 1: Configure the Project

**Ask the user for the following details:**

1. **Repository name** (format: `OWNER/REPO`, e.g., `my-org/my-repo`)
2. **GitHub Project number** (the number visible in the project URL)
3. **Project title** (descriptive name for the project)
4. **Year** for date calculations

**Edit `config.yaml` with the provided values:**

```yaml
repo: 'OWNER/REPO'
project_number: PROJECT_NUMBER
date_fields:
  start: Start date
  end: Target date
output_file: gaant.yaml
include_closed: false
```

---

## Step 2: Extract Activities and Generate YAML

Parse the planning markdown document and generate `gaant.yaml`:

### Input Pattern Recognition

- **Activities (Level 1):** `## Activity X.N:` or `#### **Activity X.N:`
- **Sub-activities:** `### **X.N.M:`
- **Dates:** `*Corresponds to: [Month(s) X-Y]*` or `(Months X-Y)` in title

### Output YAML Format (with issue: 0 for new issues)

```yaml
project:
  id: ''
  number: PROJECT_NUMBER
  title: 'PROJECT_TITLE'
  url: ''
  progress: 0

tasks:
- issue: 0
  title: 'Activity X.N: Title'
  start: 'YYYY-MM-DD'
  end: 'YYYY-MM-DD'
  progress: 0
  subtasks:
  - issue: 0
    title: 'X.N.1: Sub-activity Title'
    start: 'YYYY-MM-DD'
    end: 'YYYY-MM-DD'
    progress: 0
```

---

## Step 3: First Push - Create Issues

// turbo
Run `gaant push` to create all issues in GitHub:

```bash
source .venv/bin/activate && gaant push
```

This will:
- Create all issues with proper parent/child relationships
- Update `gaant.yaml` with the real issue numbers

---

## Step 4: Backup Existing Issues Directory

Before generating new markdown files, check if `issues/` directory exists:

// turbo
```bash
# If issues/ exists, rename it with timestamp backup
if [ -d "issues" ]; then
  mv issues issues_backup_$(date +%Y%m%d_%H%M%S)
fi
mkdir -p issues
```

---

## Step 5: Generate Issue Body Markdown Files

**After the push**, use the updated `gaant.yaml` (which now has real issue numbers) to generate markdown files in `issues/` directory.

### For Activities (parent issues):

```markdown
<!-- Issue #N: [Activity Title] -->

*Corresponds to: [time period]*
**Objective:** [objective from MD]

- **Key Deliverables:**
    - [deliverable 1]
    - [deliverable 2]
- **Justification:** [justification from MD]
```

### For Sub-activities:

```markdown
<!-- Issue #N: [Sub-activity Title] -->

**Comment:**
[comment/context from MD]

**Objectives:**
- [objective 1]
- [objective 2]

**Actions:**
- [action 1]
- [action 2]

**Deliverables:**
- [deliverable 1]
- [deliverable 2]
```

---

## Step 6: Second Push - Upload Bodies

// turbo
Run `gaant push` again to upload the markdown bodies:

```bash
source .venv/bin/activate && gaant push
```

---

## Date Mapping Reference

| Period | Start | End |
|--------|-------|-----|
| Month 1 / January | YYYY-01-01 | YYYY-01-31 |
| Months 2-3 / Feb-Mar | YYYY-02-01 | YYYY-03-31 |
| Months 2-4 / Feb-Apr | YYYY-02-01 | YYYY-04-30 |
| Months 4-7 / Apr-Jul | YYYY-04-01 | YYYY-07-31 |
| Months 8-10 / Aug-Oct | YYYY-08-01 | YYYY-10-31 |
| Months 8-11 / Aug-Nov | YYYY-08-01 | YYYY-11-30 |
| Months 11-12 / Nov-Dec | YYYY-11-01 | YYYY-12-31 |

---

## Quick Start Prompt

```
/planning-to-gaant @[planning_document.md]
```

Then provide when asked:
- Repository: `owner/repo-name`
- Project number: `N`
- Project title: `My Project Title`
- Year: `2026`
