# CLAUDE.md — Python / ML Project

## Stack
- Python 3.12 · PyTorch (MPS on Mac, CUDA on mcai) · HuggingFace · FastAPI

## Pre-commit Checks
- Always run `ruff check --fix && ruff format` before committing, including auto-generated
  files like Alembic migrations.

## Coding Standards

### Comments
- Every public function, class, method, and module MUST have a doc comment.
- Use Google-style docstrings with Args / Returns / Raises / Example sections.
- Inline comments required for any non-obvious logic, algorithm steps, or magic values.
- Never leave TODO/FIXME without a brief explanation of what is needed and why.

### Unit Tests
- All new functions MUST have corresponding unit tests — no exceptions.
- Use `pytest`; test files mirror source structure under `tests/`.
- Minimum coverage: happy path + at least one edge case + one failure/error case.
- Tests must be runnable with: `pytest`

### General Conventions
- No magic numbers — define named constants with explanatory comments.
- Prefer explicit error handling over silent failures.
- Document all function parameters — no undocumented arguments.

## ML Pipeline Conventions
- Use a unified train/eval/test script — do not split into separate files without good reason.
- Log GPU utilization at the start and end of any training or inference run.
- When in doubt about which GPU a workload will hit, log `nvidia-smi` output before and after.

## mcai Server
- SSH alias: mcai | IP: 10.63.13.70 (subnet 10.63.13.0/24)
- CUDA 12.x · RTX 5080 (eval/inference) · RTX PRO 6000 Blackwell (training)
- Ollama models served on :11434
- UFW blocks port 11434 externally — access Ollama via SSH tunnel:
  `ssh -f -N -L 11435:localhost:11434 mcai`
- Local endpoint after tunnel: `http://localhost:11435`
- Confirm working directory before running any command on mcai via SSH.
