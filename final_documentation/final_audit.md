# Final technical and originality review

Review date: 5 October 2026. This is an automated technical review, not institutional similarity clearance or certification of personal authorship.

## Technical result

All nine audit commands completed successfully. **54 unit tests passed**: Portfolio 1 (20), Portfolio 2 (12), Portfolio 4 (12), Portfolio 5 (10). Portfolio 3's nine integration scenarios and Portfolio 5's eight integration scenarios also passed in fresh executions. These are separate counts; they are not described as 71 unit tests.

The audit rebuilt Portfolio 1 from the eleven pinned local NBS resources and compared every row in all eight tables with the original database. They matched exactly. All 3,528 observations reconciled with their source cells. Subsequent phases were executed again on isolated copies without replacing their original dated evidence.

| Area | Fresh result |
|---|---|
| Relational design/import | Exact eight-table rebuild match; integrity and FK checks pass |
| Query processing | Eight analytical queries, 106 result rows identical to captured results; before/after equivalence and independent oracle checks pass |
| Transactions | Nine commit, rollback, isolation and concurrency scenarios pass |
| NoSQL | 516 persisted documents preserve 3,528 rows; six queries agree with SQL; fictional CRUD persists |
| Replication/recovery/sharding | Eight scenarios pass; shard union matches all 3,528 source projection rows |
| Documentation | Existing local Markdown/image links resolve; live Mermaid blocks already replaced with image displays |
| Data separation | No populated database, source workbook/archive or local-only data export in deliverables |
| Original source | SHA-256 unchanged throughout the audit |

The fresh performance run produced speed ratios of 1.13x, 1.40x, 1.99x and 0.99x. Portfolio 2 continues to report its original dated run (1.13x, 1.40x, 2.12x, 0.99x), rather than quietly replacing measurements. The variation is consistent with the stated warm-cache, local timing limitations; the control query still shows no useful improvement.

Code review also examined explicit transaction cleanup, affected-row checks, event/checkpoint atomicity, document validation, fixed source manifests and truthful distinctions between real data, fictional workflow records and simulated faults. No additional correctness defect was identified within the tested scope. This is not a guarantee that every possible input, machine or concurrent schedule is error-free.

## Originality and citation review

A limited exact-phrase comparison was performed over the five main phase reports against **nine cited official documentation pages** and the assessment PDF. It compared normalised 12-word windows after excluding fenced code, Markdown tables and URLs. No matching 12-word windows were found against the nine documentation pages. The machine-readable evidence records the assessment comparison separately.

Three sampled web phrase searches did not establish an exact matching passage in the returned results. Those results were broad or unrelated. This is supplementary evidence only: search indexing is incomplete, and the selected phrases are not representative of every sentence.

This method does not detect all paraphrases, translations, structural copying, code similarity or matches in closed student-paper collections. Standard database terminology and code idioms can also match legitimately. References and source-use notes are present in the phase reports. No complete private portfolio document was uploaded to an external checking service.

**No institutional similarity percentage or plagiarism clearance has been obtained.** The required maximum of 20% therefore remains unverified. A local phrase check cannot be converted into a Turnitin score, and absence of a detected match does not prove originality. Use the institution-approved draft-check process if available; do not consume the one final submission attempt as a test.

## AI disclosure and remaining submission items

OpenAI Codex is the AI tool used. It assisted with source research, code and documentation generation, diagrams, debugging and automated execution. Python, SQLite, TinyDB, openpyxl, Git and ReportLab are software tools/libraries, not additional AI services. The detailed assistance record remains in [Technologies used](technology_used.md).

The three-page summary includes the student's reflection and approval dated 18 October 2026. Before submission, obtain the approved similarity result if available, confirm the assessor can access the public repository, and finish the named submission package. No final submission has been made.

Evidence files: `audit_evidence.json`, `audit_log.txt`, and `originality_check_evidence.json`.
