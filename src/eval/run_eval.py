"""
src/eval/run_eval.py
====================
Runs the 21-case ClaimSense AI eval suite and enforces the 92% accuracy CI gate.

Exit codes
----------
  0  — accuracy >= 92% (gate passes)
  1  — accuracy <  92% (gate fails — blocks image push in CI)

Usage
-----
  # Full suite
  python src/eval/run_eval.py

  # Single case (by case_id, for debugging)
  python src/eval/run_eval.py EVAL-001

  # Skip agent cases (deterministic denies only — fast, no OpenAI calls)
  python src/eval/run_eval.py --deterministic-only
"""

from __future__ import annotations

import asyncio
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — eval runs from project root or src/eval/
# ---------------------------------------------------------------------------

_SRC = Path(__file__).parent.parent
_AGENTS = _SRC / "agents"
for p in [str(_SRC), str(_AGENTS)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from cases import ALL_CASES, EvalCase
from pipeline import run_pipeline, PipelineResult

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ACCURACY_GATE = 0.92          # 92% — must pass to unblock CI image push
CONCURRENCY   = 3             # max parallel pipeline runs (respects OpenAI rate limits)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class EvalResult:
    case:                  EvalCase
    actual_verdict:        str | None
    actual_model_generated: bool | None
    passed:                bool
    error:                 str | None
    duration_s:            float


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def _run_case(case: EvalCase, sem: asyncio.Semaphore) -> EvalResult:
    start = time.monotonic()
    async with sem:
        try:
            result: PipelineResult = await run_pipeline(
                case.claim_id or "SYNTHETIC",
                claim=case.claim,
                policy=case.policy,
                documents=case.documents if case.documents else None,
            )
            verdict_ok  = result.verdict == case.expected_verdict
            model_gen_ok = result.model_generated == case.expected_model_generated
            passed = verdict_ok and model_gen_ok
            return EvalResult(
                case=case,
                actual_verdict=result.verdict,
                actual_model_generated=result.model_generated,
                passed=passed,
                error=None,
                duration_s=time.monotonic() - start,
            )
        except Exception as e:
            return EvalResult(
                case=case,
                actual_verdict=None,
                actual_model_generated=None,
                passed=False,
                error=str(e),
                duration_s=time.monotonic() - start,
            )


async def run_suite(cases: list[EvalCase]) -> list[EvalResult]:
    sem = asyncio.Semaphore(CONCURRENCY)
    return await asyncio.gather(*[_run_case(c, sem) for c in cases])


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

_PASS = "\033[32m✓\033[0m"
_FAIL = "\033[31m✗\033[0m"
_ERR  = "\033[33m!\033[0m"


def _print_results(results: list[EvalResult]) -> None:
    print()
    print(f"{'Case':12} {'Expected':16} {'Actual':16} {'Mg':4} {'S':2}  {'Time':6}  Description")
    print("-" * 100)

    for r in results:
        icon = _PASS if r.passed else (_ERR if r.error else _FAIL)
        actual  = r.actual_verdict  or ("ERROR" if r.error else "—")
        mg_flag = str(r.actual_model_generated)[0] if r.actual_model_generated is not None else "?"
        time_s  = f"{r.duration_s:.1f}s"
        print(
            f"{r.case.case_id:12} "
            f"{r.case.expected_verdict:16} "
            f"{actual:16} "
            f"{mg_flag:4} "
            f"{icon}  "
            f"{time_s:6}  "
            f"{r.case.description[:55]}"
        )
        if r.error:
            print(f"  {'':12} ERROR: {r.error[:80]}")

    print("-" * 100)
    passed = sum(1 for r in results if r.passed)
    total  = len(results)
    pct    = passed / total if total else 0

    # Breakdown by expected verdict
    verdicts = ["Deny", "Refer-Fraud", "Refer-Adjuster", "Approve"]
    print()
    print("Results by verdict:")
    for v in verdicts:
        subset = [r for r in results if r.case.expected_verdict == v]
        if subset:
            n_pass = sum(1 for r in subset if r.passed)
            print(f"  {v:16} {n_pass}/{len(subset)}")

    print()
    print(f"Overall: {passed}/{total}  ({pct:.1%})")
    gate_str = f"≥ {ACCURACY_GATE:.0%}"
    needed   = math.ceil(ACCURACY_GATE * total)
    if pct >= ACCURACY_GATE:
        print(f"\033[32mPASS\033[0m  Accuracy {pct:.1%} meets CI gate ({gate_str})")
    else:
        print(f"\033[31mFAIL\033[0m  Accuracy {pct:.1%} is below CI gate ({gate_str})")
        print(f"       Need {needed}/{total} correct; got {passed}/{total}.")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    args = sys.argv[1:]

    # Filter to a single case for debugging
    if args and not args[0].startswith("--"):
        target = args[0]
        cases  = [c for c in ALL_CASES if c.case_id == target or c.claim_id == target]
        if not cases:
            print(f"No case matching '{target}'.")
            return 1
        print(f"Running single case: {cases[0].case_id}")
    elif "--deterministic-only" in args:
        cases = [c for c in ALL_CASES if not c.expected_model_generated]
        print(f"Running {len(cases)} deterministic-only cases (no OpenAI calls).")
    else:
        cases = ALL_CASES
        print(f"Running full eval suite ({len(cases)} cases, gate: {ACCURACY_GATE:.0%}).")

    print()
    results = asyncio.run(run_suite(cases))
    _print_results(results)

    passed = sum(1 for r in results if r.passed)
    pct    = passed / len(results) if results else 0
    return 0 if pct >= ACCURACY_GATE else 1


if __name__ == "__main__":
    sys.exit(main())
