# Portfolio 3: executed transaction evidence

Run: `20261003T220409895229Z`

All task notes below are fictional demonstration data. No raw prices are exported.

## T01_commit_and_reopen

**PASS**

```json
[
  {
    "event": "Before commit",
    "writer": {
      "status": "in_review",
      "version": 1,
      "note": "DEMO: checked provenance"
    },
    "other_reader": {
      "status": "open",
      "version": 0,
      "note": "DEMO: initial review"
    }
  },
  {
    "event": "Committed row visible on new connection",
    "row": {
      "status": "in_review",
      "version": 1,
      "note": "DEMO: checked provenance"
    }
  }
]
```

## T02_atomic_rollback_on_constraint_failure

**PASS**

```json
[
  {
    "event": "Expected database error",
    "code": 275,
    "name": "SQLITE_CONSTRAINT_CHECK",
    "message": "CHECK constraint failed: status IN ('open','in_review','resolved')"
  },
  {
    "event": "Statement failure alone leaves transaction active",
    "in_transaction": true,
    "first_operation": {
      "status": "in_review",
      "version": 1,
      "note": "DEMO: first operation succeeds"
    }
  },
  {
    "event": "Explicit rollback restores both tasks",
    "before": [
      {
        "status": "open",
        "version": 0,
        "note": "DEMO: initial review"
      },
      {
        "status": "open",
        "version": 0,
        "note": "DEMO: initial review"
      }
    ],
    "after": [
      {
        "status": "open",
        "version": 0,
        "note": "DEMO: initial review"
      },
      {
        "status": "open",
        "version": 0,
        "note": "DEMO: initial review"
      }
    ]
  }
]
```

## T03_savepoint_partial_rollback

**PASS**

```json
[
  {
    "event": "Outer edit retained; optional edit undone",
    "row": {
      "status": "in_review",
      "version": 1,
      "note": "DEMO: keep this check"
    }
  }
]
```

## T04_stale_form_overwrite_without_guard

**PASS**

```json
[
  {
    "event": "Both forms loaded outside a long transaction",
    "A": {
      "status": "open",
      "version": 0,
      "note": "DEMO: initial review"
    },
    "B": {
      "status": "open",
      "version": 0,
      "note": "DEMO: initial review"
    }
  },
  {
    "event": "Unsafe stale form overwrote A despite version-increment trigger",
    "row": {
      "status": "resolved",
      "version": 2,
      "note": "DEMO: B stale form replaces A note"
    }
  }
]
```

## T05_optimistic_version_guard

**PASS**

```json
[
  {
    "event": "Stale B edit rejected with zero affected rows",
    "accepted": false,
    "row": {
      "status": "in_review",
      "version": 1,
      "note": "DEMO: A approved provenance"
    }
  },
  {
    "event": "B refreshes, reconciles and submits a new edit",
    "row": {
      "status": "resolved",
      "version": 2,
      "note": "DEMO: A approved provenance; B checked label"
    }
  }
]
```

## T06_WAL_reader_snapshot

**PASS**

```json
[
  {
    "event": "B committed but existing A snapshot is stable",
    "before": {
      "status": "open",
      "version": 0,
      "note": "DEMO: initial review"
    },
    "during": {
      "status": "open",
      "version": 0,
      "note": "DEMO: initial review"
    }
  },
  {
    "event": "After ending read transaction A sees new commit",
    "row": {
      "status": "in_review",
      "version": 1,
      "note": "DEMO: B committed while A reads"
    }
  }
]
```

## T07_stale_snapshot_write_upgrade

**PASS**

```json
[
  {
    "event": "Expected database error",
    "code": 517,
    "name": "SQLITE_BUSY_SNAPSHOT",
    "message": "database is locked"
  },
  {
    "event": "Rollback, refresh and reconsider before new transaction",
    "row": {
      "status": "resolved",
      "version": 2,
      "note": "DEMO: B accepted edit; A reconciled after refresh"
    }
  }
]
```

## T08_single_writer_contention

**PASS**

```json
[
  {
    "event": "Expected database error",
    "code": 5,
    "name": "SQLITE_BUSY",
    "message": "database is locked"
  },
  {
    "event": "B succeeds after A commits and B rereads",
    "row": {
      "status": "resolved",
      "version": 2,
      "note": "DEMO: B edit after writer released"
    }
  }
]
```

## T09_error_cleanup_and_constraints

**PASS**

```json
[
  {
    "event": "Expected database error",
    "code": 1811,
    "name": "SQLITE_CONSTRAINT_TRIGGER",
    "message": "A task update must increment version by exactly one"
  },
  {
    "event": "Expected database error",
    "code": 787,
    "name": "SQLITE_CONSTRAINT_FOREIGNKEY",
    "message": "FOREIGN KEY constraint failed"
  },
  {
    "event": "Invalid edits left no transaction or partial change",
    "row": {
      "status": "open",
      "version": 0,
      "note": "DEMO: initial review"
    }
  }
]
```
