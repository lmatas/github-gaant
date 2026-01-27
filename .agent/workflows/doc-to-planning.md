---
description: Transform any planning document or text into the standardized markdown format for /planning-to-gaant
---

# Document to Planning MD Workflow

This workflow transforms unstructured or semi-structured planning documents into the standardized markdown format required by `/planning-to-gaant`.

**Reference template:** `.agent/workflows/planning_template.md`

---

## Step 1: Receive and Analyze the Source Document

Read the user's source document and identify:

1. **Project/Component name**
2. **Execution year**
3. **Activities** (major work packages, phases, or objectives)
4. **Sub-activities** (tasks, work items, or deliverables under each activity)
5. **Temporal information** (dates, months, phases, durations)

---

## Step 2: Validate Essential Data

**CRITICAL:** Before transforming, check for these REQUIRED elements:

### Must Have:
- [ ] Clear activity/task hierarchy (what belongs under what)
- [ ] Temporal markers (at least one of):
  - Explicit dates or months
  - Phase names with implied timing (e.g., "Q1", "First quarter")
  - Sequential ordering with durations
  - Milestone dates

### Warn the User if Missing:

If temporal information is missing or unclear, **STOP and notify the user:**

```
⚠️ **Missing Temporal Information**

The document does not contain sufficient date/time information to generate a Gantt chart.

Please add one of the following to your document:
1. Month ranges for each activity (e.g., "February-March")
2. Explicit dates (e.g., "Start: 2026-02-01")
3. Phase durations (e.g., "Duration: 6 weeks")
4. Quarter references (e.g., "Q1 2026")

Activities missing temporal data:
- [List activities without dates]
```

---

## Step 3: Transform to Standardized Format

Convert the source document using this structure:

### Document Header

```markdown
# [Component/Project Name]: High-Level Activity Plan ([YEAR])

**Execution Period:** [Start] to [End] [YEAR]
**Reporting Checkpoints:** [checkpoints if mentioned]

---
```

### For Each Activity

```markdown
## Activity [X.N]: [Activity Title]

*Corresponds to: [Month(s) or period]*

**Objective:** [Synthesized or extracted objective]

- **Key Deliverables:**
    - [Deliverable 1]
    - [Deliverable 2]
- **Justification:** [Why this matters]

---
```

### For Each Sub-activity

```markdown
### **[X.N.M]: [Sub-activity Title]**

**Comment:**
[Context - synthesize from source or write based on activity purpose]

**Objectives:**
- [Objective 1]
- [Objective 2]

**Actions:**
- [Action 1]
- [Action 2]

**Deliverables:**
- [Deliverable 1]
- [Deliverable 2]

---
```

---

## Step 4: Assign IDs and Temporal Mapping

### ID Assignment Rules

| Source Structure | Assigned ID |
|------------------|-------------|
| First major section | A.0 (or B.0, C.0, etc.) |
| Second major section | A.1 |
| First task under A.0 | A.0.1 |
| Second task under A.0 | A.0.2 |

### Temporal Inference Rules

| Source Indicator | Mapped Period |
|------------------|---------------|
| "Q1" or "First quarter" | January-March |
| "Q2" or "Second quarter" | April-June |
| "H1" or "First half" | January-June |
| "Week 1-4" or "First month" | Month 1 |
| "Phase 1" (if 4 phases) | ~3 months |
| Sequential without dates | Distribute evenly across year |

---

## Step 5: Generate Output and Validate

1. **Write the transformed markdown** to a new file (e.g., `planning_[year].md`)
2. **Run validation checklist:**
   - [ ] All Activities have IDs (X.N format)
   - [ ] All Sub-activities have IDs (X.N.M format)  
   - [ ] All Activities have temporal markers
   - [ ] All Sub-activities have: Comment, Objectives, Actions, Deliverables
   - [ ] All Activities have: Objective, Key Deliverables, Justification

3. **Report any gaps** to the user for manual completion

---

## Quick Start Prompt

```
/doc-to-planning @[source_document.md]
```

Or paste the planning text directly after invoking the workflow.

---

## Transformation Prompt for AI Agent

When transforming a document, use this internal reasoning:

```
I will analyze this planning document to extract:

1. STRUCTURE: Identify the hierarchy (what are main activities vs sub-tasks)
2. CONTENT: Extract objectives, actions, and deliverables for each item
3. TIMING: Find all temporal references and map them to months
4. GAPS: Identify missing information that needs user input

For each activity I find:
- Assign an ID following X.N pattern
- Extract or synthesize the objective
- List concrete deliverables
- Add justification based on context

For each sub-activity:
- Assign ID following X.N.M pattern (matching parent)
- Write a Comment explaining context
- List specific Objectives, Actions, and Deliverables

If temporal information is missing, I will STOP and ask the user to provide:
- Execution year
- Month ranges for activities
- Or any other timing indicators
```

---

## Example Transformation

### Source (unstructured):

```
Project Setup Phase:
- Form the team
- Set up tools and repos
- Create baseline plan

Discovery Phase (Feb-Mar):  
- Analyze coverage gaps
- Prioritize sources
- Define harvesting strategies
```

### Output (structured):

```markdown
# Project: High-Level Activity Plan (2026)

**Execution Period:** January to December 2026

---

## Activity A.0: Project Setup Phase

*Corresponds to: January (Setup)*

**Objective:** Establish team, tools, and baseline plan for project execution.

- **Key Deliverables:**
    - Formed team with clear roles
    - Initialized tools and repositories
    - Baseline execution plan
- **Justification:** Foundation for coordinated execution.

---

### **A.0.1: Team Formation**

**Comment:**
Ensures the project starts with clear responsibilities.

**Objectives:**
- Form core project team
- Define roles and responsibilities

**Actions:**
- Identify team members
- Assign roles

**Deliverables:**
- Team roster with roles

---

### **A.0.2: Tools and Repository Setup**

**Comment:**
Establishes shared infrastructure for collaboration.

**Objectives:**
- Set up project tools
- Initialize repositories

**Actions:**
- Configure project management tools
- Create code repositories

**Deliverables:**
- Initialized repositories
- Configured tools

---

## Activity A.1: Discovery Phase

*Corresponds to: February–March (Discovery)*

**Objective:** Analyze gaps, prioritize sources, and define strategies.

- **Key Deliverables:**
    - Coverage gap analysis
    - Prioritized source list
    - Harvesting strategies
- **Justification:** Systematic discovery prevents ad-hoc decisions.

---
```
