"""
cli.py — Entry point for the agent CLI.

Usage:
  agent run <agent> <task> "<instruction>"
  agent run <agent> <task> "<instruction>" --parallel <agent2> <task2> "<instruction2>"
  agent list

Install (editable):
  pip install -e .

Then use:
  agent run core add_strategy "Add a networking category"
  agent run api add_endpoint "Add GET /categories"
  agent run core add_strategy "Add networking" --parallel api add_endpoint "Add /categories"
  agent list
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from agent_runner.executor import run
from agent_runner.parallel import AgentJob, run_parallel
from agent_runner.registry import AGENTS, TASKS, resolve_agent, resolve_task

PROJECT_DIR = Path(__file__).parent.parent.resolve()

app = typer.Typer(
    name="agent",
    help="CLI harness for running named Claude agents against named task prompts.",
    add_completion=False,
)


@app.command(name="run")
def run_cmd(
    agent: str = typer.Argument(..., help="Agent name (e.g. core, api, test, schema)"),
    task: str = typer.Argument(..., help="Task name (e.g. add_strategy, add_endpoint)"),
    instruction: str = typer.Argument(..., help="Free-text instruction appended to the prompt"),
    parallel: bool = typer.Option(False, "--parallel", help="Run a second agent concurrently"),
    agent2: str = typer.Option("", "--agent2", help="Second agent name (requires --parallel)"),
    task2: str = typer.Option("", "--task2", help="Second task name (requires --parallel)"),
    instruction2: str = typer.Option("", "--instruction2", help="Second instruction (requires --parallel)"),
):
    """Run one agent, or two agents in parallel with --parallel."""

    # Validate primary agent/task early for a clean error message
    try:
        resolve_agent(agent)
        resolve_task(task)
    except ValueError as e:
        typer.echo(f"[ERROR] {e}", err=True)
        raise typer.Exit(1)

    if parallel:
        if not agent2 or not task2 or not instruction2:
            typer.echo(
                "[ERROR] --parallel requires --agent2, --task2, and --instruction2",
                err=True,
            )
            raise typer.Exit(1)

        try:
            resolve_agent(agent2)
            resolve_task(task2)
        except ValueError as e:
            typer.echo(f"[ERROR] {e}", err=True)
            raise typer.Exit(1)

        jobs = [
            AgentJob(agent=agent,  task=task,  instruction=instruction),
            AgentJob(agent=agent2, task=task2, instruction=instruction2),
        ]

        typer.echo("")
        typer.echo("Running agents in parallel...")
        for j in jobs:
            typer.echo(f"  [{j.agent}] {j.task} — {j.instruction}")
        typer.echo("")

        results = run_parallel(jobs, PROJECT_DIR)

        typer.echo("")
        typer.echo("===== PARALLEL RUN SUMMARY =====")
        all_ok = True
        for r in results:
            status = "SUCCESS" if r.exit_code == 0 else "FAILED"
            typer.echo(f"  [{r.job.agent}] {status}")
            if r.exit_code != 0:
                all_ok = False
        typer.echo("")

        raise typer.Exit(0 if all_ok else 1)

    else:
        typer.echo("")
        typer.echo(f"  Agent:       {agent}")
        typer.echo(f"  Task:        {task}")
        typer.echo(f"  Instruction: {instruction}")
        typer.echo("")

        exit_code = run(agent, task, instruction, PROJECT_DIR)
        raise typer.Exit(exit_code)


@app.command(name="list")
def list_cmd():
    """List all registered agents and tasks."""
    typer.echo("")
    typer.echo("Available agents:")
    for name, path in sorted(AGENTS.items()):
        typer.echo(f"  {name:<12}  ->  {path}")

    typer.echo("")
    typer.echo("Available tasks:")
    for name, path in sorted(TASKS.items()):
        typer.echo(f"  {name:<25}  ->  {path}")
    typer.echo("")


def main():
    app()


if __name__ == "__main__":
    main()
