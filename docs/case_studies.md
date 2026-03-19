# Case Studies

## Using DeCodifier with Codex on a Real OS Repo

This dogfood run tested DeCodifier in the workflow it is designed for:

1. retrieval first
2. change-surface planning
3. coordinated edit
4. focused verification

### Task

Upgrade a calculator in a local OS project from basic arithmetic to a broader integer-math feature set.

### Before Retrieval

At first glance, this looked like a simple single-file change in the guest calculator source.

That is exactly the kind of task where code agents often make incomplete edits: they patch the obvious implementation file and miss mirrored behavior elsewhere in the repo.

### What DeCodifier Surfaced

Using the MCP-connected DeCodifier retrieval layer, Codex surfaced the real behavioral change surface:

- **Guest implementation surface:** `user/calc.c`
- **Host-side mirrored behavior surface:** `model/qwen_chat.py`
- **User-facing capability text:** guest help and prompt text plus host-side router and prompt text
- **Bridge-related context:** bridge and routing logic relevant to how calculator sessions are entered and handled

### Why This Changed the Edit Plan

The important insight was that calculator behavior existed in two coordinated paths:

- the real guest calculator implementation
- the host-side mirrored simulation and routing logic

Without retrieval of the full surface, Codex could easily have patched only `user/calc.c` and left the host-side behavior behind.

DeCodifier changed the task from:

> edit the calculator file

to:

> edit the full set of surfaces that define calculator behavior and keep them aligned

The bridge transport itself did not need protocol changes. The risk was semantic drift between the guest and host behavior layers above that transport.

### Change Made

The final patch added a wider integer-math feature set across both paths, including:

- new unary helpers
- new binary and bitwise helpers
- parser and alias expansion
- host-side safe-eval and simulated parser alignment
- updated capability and help text

### Verification

Focused verification passed:

- `python3 -m py_compile model/qwen_chat.py`
- `make kernel.elf`
- targeted calculator harness covering success cases, chained operations, function-style forms, and invalid or overflow cases

This was a focused verification pass rather than a full system regression.

In that environment, direct import of the host bridge module was blocked by a missing `torch` dependency, so the calculator verification used a calc-only extracted harness from the mirrored Python logic instead.

### Why This Case Matters

This run demonstrates the difference between **relevant retrieval** and **change-surface retrieval**.

A normal retrieval system might find the calculator file.

DeCodifier surfaced the broader set of aligned behavior surfaces that needed to change together.

That is the practical value of method, caller, entrypoint, and behavior-surface retrieval for code agents.

### Summary

DeCodifier helped Codex recover the full calculator behavior surface in a real repo before editing:

- implementation
- mirrored host logic
- routing and bridge context
- user-facing capability text

That reduced the risk of a one-sided patch and produced a safer coordinated change.
