"""
parallel.py — Runs multiple agents concurrently using threads.

Each agent gets its own thread + subprocess. Output is interleaved
in the terminal (same behaviour as bash `&`), and we collect exit codes
so the summary can report which agents succeeded or failed.

Why threads instead of asyncio?
  subprocess.run() is blocking I/O — threads are the right tool here.
  asyncio would require asyncio.create_subprocess_exec throughout.
"""

import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path

from agent_runner.executor import build_prompt
from agent_runner.spinner import Spinner


@dataclass
class AgentJob:
    agent: str
    task: str
    instruction: str


@dataclass
class JobResult:
    job: AgentJob
    exit_code: int = 0
    error: str = ""


def _run_job(job: AgentJob, project_dir: Path, results: list, lock: threading.Lock) -> None:
    prompt = build_prompt(job.agent, job.task, job.instruction)
    cmd = ["claude", "--print", "--dangerously-skip-permissions", prompt]
    result = subprocess.run(cmd, cwd=str(project_dir), shell=True)
    with lock:
        results.append(JobResult(job=job, exit_code=result.returncode))


def run_parallel(jobs: list[AgentJob], project_dir: Path) -> list[JobResult]:
    """
    Launch all jobs concurrently, wait for all to finish, return results.
    """
    results: list[JobResult] = []
    lock = threading.Lock()
    threads = []

    labels = ", ".join(f"[{j.agent}]" for j in jobs)
    with Spinner(f"Running {labels} in parallel"):
        for job in jobs:
            t = threading.Thread(
                target=_run_job,
                args=(job, project_dir, results, lock),
                daemon=False,
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

    # Preserve original job order in results
    order = {id(job): i for i, job in enumerate(jobs)}
    results.sort(key=lambda r: order.get(id(r.job), 0))

    return results
