# Slurm shared resource policy implementation plan

**Goal:** Add opt-in CPU oversubscription, non-blocking memory accounting, GPU shards, and matching OOD controls for the A100 and RTX 4070 partitions.

**Constraints:** Keep all changes uncommitted in the current workspace. Run only focused tests for this policy.

## Task 1: Add focused contract tests

- Extend the Slurm role contract to cover partition oversubscription, `CR_Core`, CPU billing weight, shard GRES/accounting, and disabled RAM cgroup enforcement.
- Extend the OOD role contract to cover the CPU-sharing checkbox, `--oversubscribe`, the GPU resource dropdown, shard choices, full-GPU default, and rejection of conflicting advanced GPU flags.
- Run only the new shared-resource-policy test methods and confirm that they fail before implementation.

## Task 2: Configure Slurm resources

- Add per-host oversubscription, select parameters, shard count, and updated billing weights.
- Render GPU and shard resources in `slurm.conf.j2` and `gres.conf.j2`.
- Keep core/device cgroup enforcement enabled and RAM enforcement disabled.

## Task 3: Update OOD resource forms

- Publish shard metadata to each app.
- Add an uncached, unchecked CPU oversubscription checkbox to all five apps and emit `--oversubscribe` only when selected.
- Replace numeric GPU inputs in the four GPU-capable apps with a partition-aware dropdown whose default is one full GPU.
- Emit at most one GPU `--gres` argument and reject GPU resource flags in `extra_sbatch`.

## Task 4: Minimal verification

- Run only the two focused shared-resource-policy test methods.
- Inspect the final diff and working-tree status.
- Do not commit.
