# Portfolio 5: executed local exercise

Run: `20261004T110216717910Z`

Local single-process simulation with independent SQLite files; no cloud/network deployment

## S01_initial_snapshot

**PASS**

```json
{
  "case": "S01_initial_snapshot",
  "passed": true,
  "primary": {
    "version": 0,
    "status": "open",
    "note": "DEMO: initial review"
  },
  "replica": {
    "version": 0,
    "status": "open",
    "note": "DEMO: initial review"
  },
  "checkpoint": 0
}
```

## S02_paused_worker_stale_read

**PASS**

```json
{
  "case": "S02_paused_worker_stale_read",
  "passed": true,
  "acknowledged_sequence": 2,
  "pending_events": 2,
  "eventual_read": {
    "route": "replica",
    "satisfies_minimum": false,
    "applied_sequence": 0,
    "task": {
      "version": 0,
      "status": "open",
      "note": "DEMO: initial review"
    }
  },
  "strict_read": {
    "route": "primary",
    "satisfies_minimum": true,
    "applied_sequence": 2,
    "task": {
      "version": 2,
      "status": "in_review",
      "note": "DEMO: label checked"
    }
  }
}
```

## S03_simulated_primary_outage

**PASS**

```json
{
  "case": "S03_simulated_primary_outage",
  "passed": true,
  "refused": [
    {
      "operation": "strict_read",
      "message": "Replica is behind required sequence and primary is unavailable"
    },
    {
      "operation": "write",
      "message": "Primary unavailable: writes are not redirected to the replica"
    }
  ],
  "labelled_stale_read": {
    "route": "replica",
    "satisfies_minimum": false,
    "applied_sequence": 0,
    "task": {
      "version": 0,
      "status": "open",
      "note": "DEMO: initial review"
    }
  },
  "replica_promoted": false
}
```

## S04_catch_up_and_repeat

**PASS**

```json
{
  "case": "S04_catch_up_and_repeat",
  "passed": true,
  "applied_events": 2,
  "repeat_applied_events": 0,
  "checkpoint": 2,
  "task": {
    "version": 2,
    "status": "in_review",
    "note": "DEMO: label checked"
  }
}
```

## S05_worker_failure_and_retry

**PASS**

```json
{
  "case": "S05_worker_failure_and_retry",
  "passed": true,
  "error": "Injected worker failure before checkpoint",
  "rolled_back_task": {
    "version": 2,
    "status": "in_review",
    "note": "DEMO: label checked"
  },
  "rolled_back_checkpoint": 2,
  "recovered_task": {
    "version": 3,
    "status": "in_review",
    "note": "DEMO: reconciled note"
  },
  "recovered_checkpoint": 3
}
```

## S06_restore_recovery_point

**PASS**

```json
{
  "case": "S06_restore_recovery_point",
  "passed": true,
  "primary_sequence": 4,
  "backup_sequence": 3,
  "acknowledged_edits_absent_from_restore": 1,
  "restored_task": {
    "version": 3,
    "status": "in_review",
    "note": "DEMO: reconciled note"
  },
  "restored_source_observations": 3528
}
```

## S07_month_range_shards

**PASS**

```json
{
  "case": "S07_month_range_shards",
  "passed": true,
  "shard_observations": [
    1764,
    1764
  ],
  "total_observations": 3528,
  "source_projection_sha256": "0f7b3a980d9a165d301b5e86a6a9655d4fd1a9e74904c24b6266b0f81c18e23d",
  "shard_union_sha256": "0f7b3a980d9a165d301b5e86a6a9655d4fd1a9e74904c24b6266b0f81c18e23d",
  "january_route": 0,
  "december_route": 1,
  "exact_union": true,
  "no_overlap": true
}
```

## S08_missing_shard_refusal

**PASS**

```json
{
  "case": "S08_missing_shard_refusal",
  "passed": true,
  "message": "A required shard is missing: refusing a partial global result",
  "partial_result_reported_as_complete": false
}
```
