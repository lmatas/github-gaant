# Planning Document Template for GitHub-Gaant

This is the optimized markdown template for planning documents that feed into the `/planning-to-gaant` workflow.

---

## Required Metadata (at the top of your document)

```markdown
# [Component/Project Name]: High-Level Activity Plan ([YEAR])

**Execution Period:** [Start Month] to [End Month] [YEAR]
**Reporting Checkpoints:** [e.g., Mid-year (Month 6), End-of-year (Month 12)]
```

---

## Activity Structure

### Activity (Parent Issue)

```markdown
## Activity [ID]: [Activity Title]

*Corresponds to: [Month(s) X-Y] ([descriptive period])*

**Objective:** [Single paragraph describing the activity's main goal]

- **Key Deliverables:**
    - [Deliverable 1]
    - [Deliverable 2]
    - [Deliverable 3]
- **Justification:** [Why this activity matters]

---
```

### Sub-activity (Child Issue)

```markdown
### **[ID]: [Sub-activity Title]**

**Comment:**
[Context explaining why this sub-activity exists and what problem it solves]

**Objectives:**
- [Objective 1]
- [Objective 2]
- [Objective 3]

**Actions:**
- [Specific action 1]
- [Specific action 2]
- [Specific action 3]

**Deliverables:**
- [Concrete deliverable 1]
- [Concrete deliverable 2]
- [Concrete deliverable 3]

---
```

---

## Naming Conventions

| Level | ID Format | Example |
|-------|-----------|---------|
| Activity | `X.N` | `A.0`, `A.1`, `B.1` |
| Sub-activity | `X.N.M` | `A.0.1`, `A.1.2`, `B.1.3` |

---

## Temporal Markers (REQUIRED)

Each Activity **MUST** have one of these temporal indicators:

1. **In the header:** `(Month X)` or `(Months X-Y)`
2. **In the Corresponds line:** `*Corresponds to: [Month(s)]*`
3. **Explicit dates:** `Start: YYYY-MM-DD, End: YYYY-MM-DD`

### Valid examples:
- `*Corresponds to: January (Setup)*`
- `*Corresponds to: February–March (Discovery phase)*`
- `*Corresponds to: Months 4-7 (Pilot implementation)*`
- `## Activity A.1: Setup (Month 1)`

---

## Complete Example

```markdown
# Component A: High-Level Activity Plan (2026)

**Execution Period:** January to December 2026
**Reporting Checkpoints:** Mid-year (July), End-of-year (December)

---

## Activity A.0: Team Formation and Planning

*Corresponds to: January (Setup)*

**Objective:** Establish the team, tools, and baseline plan for Year 1 execution.

- **Key Deliverables:**
    - Year-1 execution plan with scope boundaries
    - Project repositories and working conventions
    - Technical environment readiness checklist
- **Justification:** Prevents drift and enables coordinated execution.

---

### **A.0.1: Team Formation and Role Alignment**

**Comment:**
Ensures the project starts with clear role distribution and coordination mechanisms.

**Objectives:**
- Confirm core team and role distribution
- Clarify responsibilities across functions
- Establish coordination mechanisms

**Actions:**
- Map roles to activities and workstreams
- Define decision-making responsibilities
- Establish meeting cadence

**Deliverables:**
- Team and role matrix
- Responsibility map
- Meeting cadence plan

---

### **A.0.2: Planning Baseline and Scope Framing**

**Comment:**
Translates the framework into a concrete, time-bounded execution baseline.

**Objectives:**
- Freeze Year-1 scope and objectives
- Align milestones and reporting checkpoints
- Document out-of-scope items

**Actions:**
- Consolidate Year-1 plan
- Define control points
- Document assumptions

**Deliverables:**
- Year-1 execution plan
- Milestone map
- Scope boundary document

---

## Activity A.1: Discovery Phase

*Corresponds to: February–March (Discovery)*

**Objective:** Identify gaps, prioritize sources, and define strategies.

- **Key Deliverables:**
    - Gap analysis report
    - Prioritized source list
    - Strategy matrix
- **Justification:** Systematic discovery prevents ad-hoc decisions.

---

### **A.1.1: Gap Analysis**

**Comment:**
Establishes where expansion is needed and why.

**Objectives:**
- Identify coverage gaps
- Define prioritization criteria

**Actions:**
- Analyze current coverage
- Compile candidate lists
- Rank by priority tiers

**Deliverables:**
- Gap analysis report
- Prioritized list with selection criteria

---
```

---

## Validation Checklist

Before using this document with `/planning-to-gaant`, verify:

- [ ] Each Activity has a temporal marker (month or date range)
- [ ] Activity IDs follow `X.N` pattern
- [ ] Sub-activity IDs follow `X.N.M` pattern and match parent
- [ ] Each sub-activity has: Comment, Objectives, Actions, Deliverables
- [ ] Each Activity has: Objective, Key Deliverables, Justification
