#!/usr/bin/env bash
# =============================================================
# agent.sh — CLI wrapper for running named agents + tasks
#
# Usage:
#   ./agent.sh run <agent> <task> "<instruction>"
#   ./agent.sh run <agent1> <agent2> --parallel "<instruction1>" "<instruction2>"
#   ./agent.sh list
#
# Examples:
#   ./agent.sh run core add_strategy "Add a networking category"
#   ./agent.sh run api add_endpoint "Add GET /categories"
#   ./agent.sh run core api --parallel "Add networking category" "Add GET /categories"
# =============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- Agent registry ---
declare -A AGENTS=(
    [schema]="agents/agent_schema.md"
    [api]="agents/agent_api.md"
    [core]="agents/agent_core.md"
    [test]="agents/agent_tests.md"
)

# --- Task registry ---
declare -A TASKS=(
    [add_strategy]="prompts/add_strategy.md"
    [add_endpoint]="prompts/add_endpoint.md"
    [add_telemetry]="prompts/add_telemetry.md"
    [add_tests]="prompts/add_tests.md"
    [improve_error_handling]="prompts/improve_error_handling.md"
    [create_schema]="prompts/create_schema.md"
    [create_api]="prompts/create_api.md"
    [create_core]="prompts/create_core.md"
    [create_tests]="prompts/create_tests.md"
)

# --- Helpers ---

list_agents() {
    echo ""
    echo "Available agents:"
    for key in "${!AGENTS[@]}"; do
        echo "  $key  →  ${AGENTS[$key]}"
    done | sort
    echo ""
    echo "Available tasks:"
    for key in "${!TASKS[@]}"; do
        echo "  $key  →  ${TASKS[$key]}"
    done | sort
    echo ""
}

run_agent() {
    local agent=$1
    local task=$2
    local instruction=$3

    if [[ -z "${AGENTS[$agent]}" ]]; then
        echo "[ERROR] Unknown agent: '$agent'"
        echo "        Run './agent.sh list' to see available agents."
        exit 1
    fi

    if [[ -z "${TASKS[$task]}" ]]; then
        echo "[ERROR] Unknown task: '$task'"
        echo "        Run './agent.sh list' to see available tasks."
        exit 1
    fi

    local agent_file="${AGENTS[$agent]}"
    local task_file="${TASKS[$task]}"
    local prompt="Read $agent_file and $task_file. $instruction Run verification."

    echo ""
    echo "  Agent:       $agent"
    echo "  Task:        $task"
    echo "  Instruction: $instruction"
    echo ""

    cd "$PROJECT_DIR"
    claude --print --dangerously-skip-permissions "$prompt"
}

run_parallel() {
    local agent1=$1
    local task1=$2
    local instruction1=$3
    local agent2=$4
    local task2=$5
    local instruction2=$6

    echo ""
    echo "Running agents in parallel..."
    echo "  [$agent1] $task1 — $instruction1"
    echo "  [$agent2] $task2 — $instruction2"
    echo ""

    local agent_file1="${AGENTS[$agent1]}"
    local task_file1="${TASKS[$task1]}"
    local prompt1="Read $agent_file1 and $task_file1. $instruction1 Run verification."

    local agent_file2="${AGENTS[$agent2]}"
    local task_file2="${TASKS[$task2]}"
    local prompt2="Read $agent_file2 and $task_file2. $instruction2 Run verification."

    cd "$PROJECT_DIR"

    (claude --print --dangerously-skip-permissions "$prompt1" && echo "[$agent1] Done") &
    PID1=$!

    (claude --print --dangerously-skip-permissions "$prompt2" && echo "[$agent2] Done") &
    PID2=$!

    wait $PID1; STATUS1=$?
    wait $PID2; STATUS2=$?

    echo ""
    echo "===== PARALLEL RUN SUMMARY ====="
    [ $STATUS1 -eq 0 ] && echo "  [$agent1] SUCCESS" || echo "  [$agent1] FAILED"
    [ $STATUS2 -eq 0 ] && echo "  [$agent2] SUCCESS" || echo "  [$agent2] FAILED"
    echo ""
}

# --- Usage ---

usage() {
    echo ""
    echo "Usage:"
    echo "  ./agent.sh run <agent> <task> \"<instruction>\""
    echo "  ./agent.sh run <agent1> <agent2> --parallel \"<instruction1>\" \"<instruction2>\" <task1> <task2>"
    echo "  ./agent.sh list"
    echo ""
    echo "Examples:"
    echo "  ./agent.sh run core add_strategy \"Add a networking category\""
    echo "  ./agent.sh run api add_endpoint \"Add GET /categories\""
    echo "  ./agent.sh run core api --parallel \"Add networking category\" \"Add GET /categories\" add_strategy add_endpoint"
    echo ""
}

# --- Entry point ---

COMMAND=$1

case "$COMMAND" in
    run)
        AGENT1=$2
        AGENT2_OR_TASK=$3

        if [[ "$4" == "--parallel" ]]; then
            # Parallel mode: agent.sh run <agent1> <agent2> --parallel "<inst1>" "<inst2>" <task1> <task2>
            run_parallel "$AGENT1" "$6" "$5" "$AGENT2_OR_TASK" "$7" "${8:-Run verification}"
        else
            # Single mode: agent.sh run <agent> <task> "<instruction>"
            TASK=$AGENT2_OR_TASK
            INSTRUCTION=$4
            run_agent "$AGENT1" "$TASK" "$INSTRUCTION"
        fi
        ;;
    list)
        list_agents
        ;;
    *)
        usage
        ;;
esac
