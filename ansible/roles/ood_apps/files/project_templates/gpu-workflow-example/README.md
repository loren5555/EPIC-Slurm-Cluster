# GPU Workflow Example

This is a Project Manager template. In Open OnDemand, select **Create a new
project**, choose **GPU Workflow Example**, then create your own private copy.
The system-owned source is never edited by users.

## What this project demonstrates

The project contains three scripts for a Project Manager workflow:

```text
preprocess -> train -> evaluate
```

Each workflow run uses `OOD_WORKFLOW_SYNC_KEY` in its output path. Concurrent
workflow runs therefore do not overwrite one another.

## Create the launchers

In your copied project, create these three launchers:

| Launcher | Script | Suggested environment variables |
| --- | --- | --- |
| Preprocess | `scripts/preprocess.sh` | `DATASET=example-dataset`, `EXPERIMENT_NAME=baseline` |
| Train | `scripts/train.sh` | `EXPERIMENT_NAME=baseline` |
| Evaluate | `scripts/evaluate.sh` | `EXPERIMENT_NAME=baseline` |

For every launcher, choose cluster `epic`, select the target host partition,
and request only the resources the stage needs. The Train launcher is the only
stage that normally needs a GPU. Select a full GPU by default; select a GPU
shard only for small jobs that can share a GPU.

Then create a Workflow, add the launchers in the order above, and connect
Preprocess to Train and Train to Evaluate.

## Adapt it to a real project

1. Replace the placeholder commands in `scripts/preprocess.sh`,
   `scripts/train.sh`, and `scripts/evaluate.sh`.
2. Put configuration files in `configs/` and source code in `src/`.
3. Keep generated files below `outputs/`; do not write results into the shared
   template.
4. Add environment variables to launchers instead of copying scripts for each
   experiment.
