import textwrap
from pathlib import Path

import pandas as pd
from langchain_openai import ChatOpenAI
from langgraph.types import interrupt

from src.sandbox import run_code
from src.schemas import (
    AnalysisPlan,
    AnalysisReport,
    ChartResult,
    CodeRun,
    GeneratedCode,
    StepVerdict,
)
from src.state import AnalysisState

_MAX_FIX_ATTEMPTS = 2
_CHARTS_DIR = "charts"

_llm_mini = ChatOpenAI(model="gpt-4o-mini", temperature=0)
_llm = ChatOpenAI(model="gpt-4o", temperature=0)


def load_data(state: AnalysisState) -> dict:
    df = pd.read_csv(state["file_path"])
    info_lines = [
        f"File: {state['file_path']}",
        f"Shape: {df.shape[0]} rows × {df.shape[1]} columns",
        f"Columns and dtypes:\n{df.dtypes.to_string()}",
        f"\nSample (first 5 rows):\n{df.head(5).to_string(index=False)}",
        f"\nDescriptive stats:\n{df.describe(include='all').to_string()}",
    ]
    return {
        "dataframe_info": "\n".join(info_lines),
        "code_history": [],
        "charts": [],
        "iteration": 0,
        "current_step_index": 0,
        "fix_attempts": 0,
        "analysis_plan": [],
        "report": None,
    }


def plan_analysis(state: AnalysisState) -> dict:
    llm = _llm.with_structured_output(AnalysisPlan)
    result: AnalysisPlan = llm.invoke([
        {"role": "system", "content": textwrap.dedent("""\
            You are a data analyst. Given a dataset description and a user question, produce
            a numbered list of 3-6 concrete analysis steps. Each step should be one self-contained
            Python script that prints findings and optionally saves a chart via save_chart("name.png").
            Steps must use only pandas, numpy, and matplotlib.
        """)},
        {"role": "user", "content": (
            f"Dataset info:\n{state['dataframe_info']}\n\n"
            f"Question: {state['question']}"
        )},
    ])

    approved = interrupt({
        "message": "Analysis plan ready. Approve or provide an edited list of steps.",
        "steps": result.steps,
    })

    final_steps = approved if isinstance(approved, list) else result.steps
    return {"analysis_plan": final_steps, "current_step_index": 0, "fix_attempts": 0}


def generate_code(state: AnalysisState) -> dict:
    step_idx = state["current_step_index"]
    step = state["analysis_plan"][step_idx]

    prior_output = ""
    if state["code_history"]:
        last = state["code_history"][-1]
        prior_output = f"\nPrevious step output (for context):\n{last.stdout[:1000]}"

    llm = _llm_mini.with_structured_output(GeneratedCode)
    result: GeneratedCode = llm.invoke([
        {"role": "system", "content": textwrap.dedent("""\
            Write a complete, self-contained Python data analysis script.
            Rules:
            - Load data with: df = pd.read_csv(DATA_FILE)
            - Use pre-imported: pd, np, plt, math, statistics, json, re, Counter, defaultdict
            - Save charts with: save_chart("filename.png")
            - Print ALL key findings with print()
            - Do NOT write any import statements — they are already present
            - The script must be runnable as-is with no undefined variables
        """)},
        {"role": "user", "content": (
            f"Dataset info:\n{state['dataframe_info']}"
            f"{prior_output}\n\n"
            f"Task (step {step_idx + 1}): {step}"
        )},
    ])

    new_run = CodeRun(step=step, code=result.code, stdout="", stderr="", success=False, attempt=1)
    return {"code_history": state["code_history"] + [new_run]}


def execute_code(state: AnalysisState) -> dict:
    pending = state["code_history"][-1]
    chart_dir = str(Path(state["file_path"]).parent / _CHARTS_DIR)

    stdout, stderr, success = run_code(pending.code, state["file_path"], chart_dir)

    charts = list(state.get("charts", []))
    for line in stdout.splitlines():
        if line.startswith("CHART_SAVED:"):
            path = line[len("CHART_SAVED:"):]
            charts.append(ChartResult(path=path, description=pending.step))

    updated = CodeRun(
        step=pending.step,
        code=pending.code,
        stdout=stdout,
        stderr=stderr,
        success=success,
        attempt=pending.attempt,
    )
    return {"code_history": state["code_history"][:-1] + [updated], "charts": charts}


def fix_code(state: AnalysisState) -> dict:
    failed = state["code_history"][-1]
    attempt_num = state["fix_attempts"] + 1

    llm = _llm_mini.with_structured_output(GeneratedCode)
    result: GeneratedCode = llm.invoke([
        {"role": "system", "content": textwrap.dedent("""\
            Fix the Python code shown below. The error is in stderr.
            Pre-imported: pd, np, plt, math, statistics, json, re, Counter, defaultdict, groupby
            Available: DATA_FILE (str path), CHART_DIR (str path), save_chart(name)
            Do NOT add any import statements. Return the complete corrected script.
        """)},
        {"role": "user", "content": (
            f"FAILED CODE:\n```python\n{failed.code}\n```\n\n"
            f"STDERR:\n{failed.stderr}\n\n"
            f"Fix it to complete: {failed.step}"
        )},
    ])

    fixed = CodeRun(
        step=failed.step,
        code=result.code,
        stdout="",
        stderr="",
        success=False,
        attempt=attempt_num + 1,
    )
    return {"code_history": state["code_history"][:-1] + [fixed], "fix_attempts": attempt_num}


def interpret_results(state: AnalysisState) -> dict:
    last = state["code_history"][-1]
    step_idx = state["current_step_index"]
    total = len(state["analysis_plan"])

    llm = _llm_mini.with_structured_output(StepVerdict)
    result: StepVerdict = llm.invoke([
        {"role": "system", "content": (
            f"You are evaluating a data analysis step. "
            f"Current step: {step_idx + 1} of {total}. "
            "Set analysis_complete=true only when ALL steps have been covered and the user's question is answered."
        )},
        {"role": "user", "content": (
            f"Completed step: {last.step}\n"
            f"Output:\n{last.stdout[:2000]}\n"
            f"Errors (if any):\n{last.stderr[:500]}\n"
            f"Remaining steps: {state['analysis_plan'][step_idx + 1:]}"
        )},
    ])

    done = result.analysis_complete or (step_idx + 1 >= total)
    new_idx = total if done else step_idx + 1
    return {
        "current_step_index": new_idx,
        "fix_attempts": 0,
        "iteration": state.get("iteration", 0) + 1,
    }


def generate_report(state: AnalysisState) -> dict:
    all_output = "\n\n".join(
        f"Step {i + 1} — {r.step}\nOutput:\n{r.stdout[:1200]}"
        for i, r in enumerate(state["code_history"])
    )
    charts_desc = "\n".join(
        f"- {Path(c.path).name}: {c.description}"
        for c in state.get("charts", [])
    )

    llm = _llm.with_structured_output(AnalysisReport)
    result: AnalysisReport = llm.invoke([
        {"role": "system", "content": (
            "You are a senior data analyst writing a final report. "
            "Synthesize all analysis outputs into a clear, actionable answer."
        )},
        {"role": "user", "content": (
            f"Original question: {state['question']}\n\n"
            f"Analysis outputs:\n{all_output}\n\n"
            f"Charts generated:\n{charts_desc or 'None'}"
        )},
    ])
    return {"report": result}
