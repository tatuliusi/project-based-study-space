# Architecture — Autonomous Data Analyst

## Core pattern: Code execution loop with HITL checkpointing

The agent generates code, runs it, reads the output, and decides what to do next. It loops until it has answered the user's question. Human-in-the-loop (HITL) checkpoints let the user approve the analysis plan before the agent starts executing code.

## Implementation entry point

The analysis loop and checkpoint routing are implemented in `src/graph.py`.

## State

```python
class AnalysisState(TypedDict):
    question: str
    dataframe_info: str          # Schema, dtypes, sample rows — not the full df
    analysis_plan: list[str]     # Approved list of analysis steps
    code_history: list[CodeRun]  # All code executed and their outputs
    charts: list[ChartResult]    # Generated chart paths and descriptions
    iteration: int
    report: AnalysisReport | None
```

```python
class CodeRun(BaseModel):
    code: str
    stdout: str
    stderr: str
    success: bool
```

## Nodes

### `load_data`
Reads the CSV/database. Extracts schema info, dtypes, shape, and a sample (first 5 rows). Stores this description — never the full dataframe — in state. Prevents the LLM from being fed huge context.

### `plan_analysis`
LLM node. Given the question and data schema, produces a numbered list of analysis steps. **HITL checkpoint here** — graph pauses and waits for user approval before proceeding.

### `generate_code`
LLM node. Takes the current step from the plan, the data schema, and prior code outputs. Generates Python code (pandas + matplotlib) to execute that step.

### `execute_code`
Runs the generated code in a restricted subprocess with a timeout. Captures stdout, stderr, and any saved chart files. Routes to `fix_code` on error, `interpret_results` on success.

### `fix_code`
LLM node. Receives the failed code + stderr. Produces a corrected version. Capped at 2 fix attempts before moving to the next analysis step.

### `interpret_results`
LLM node. Reads the code output and decides: is this step done? Is there more to analyze? Routes to `plan_analysis` if more steps remain, or to `generate_report` when all steps are complete.

### `generate_report`
LLM node with structured output. Produces a final `AnalysisReport`:

```python
class AnalysisReport(BaseModel):
    question: str
    answer: str
    key_findings: list[str]
    charts: list[ChartSummary]
    caveats: list[str]
```

## Graph

```
START
  │
  ▼
load_data
  │
  ▼
plan_analysis ◄──────────────────────────────────────────┐
  │                                                       │
  [HITL checkpoint — user approves plan]                  │
  │                                                       │
  ▼                                                       │
generate_code                                             │
  │                                                       │
  ▼                                                       │
execute_code                                              │
  │                                                       │
  ├── [error, attempts < 2] ──► fix_code ──► execute_code │
  │                                                       │
  └── [success] ──► interpret_results                     │
                        │                                 │
                        ├── [more steps] ─────────────────┘
                        │
                        └── [done] ──► generate_report ──► END
```

## The hard problem: safe code execution

LLM-generated code can do anything — delete files, make network calls, infinite loops. The sandbox must:
1. Restrict imports (whitelist: pandas, numpy, matplotlib, datetime, math)
2. Enforce a timeout (30 seconds max)
3. Redirect file writes to a temp directory
4. Never run as root

This project uses subprocess isolation with resource limits. A production version would use a container or WebAssembly sandbox.

## Why HITL matters here

Before the agent starts running code against real data, the user should see and approve the analysis plan. LangGraph's checkpointing lets you persist state to disk, pause the graph, and resume it after the user responds — even across process restarts. This is what makes LangGraph suited for production use cases that span minutes or hours.
