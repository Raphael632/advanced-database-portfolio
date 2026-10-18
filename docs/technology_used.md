# Technologies used

## Implementation and development

| Technology | Use in this project |
| --- | --- |
| Python 3.12 | Data import, validation, analytical checks, benchmarks, transaction scenarios, document conversion and replication exercises. |
| SQLite 3.53.1 and Python sqlite3 | Relational storage, constraints, triggers, indexes, query plans, WAL transactions, backups and the local primary/replica/shard exercise. |
| SQL | Schema definition, joins, aggregation, window functions, indexes and transactional updates. |
| openpyxl 3.1.5 | Reading the NBS Excel workbooks and reconciling imported values with source cells. |
| TinyDB 4.9.0 | Persisting and querying the Portfolio 4 JSON document model and fictional review records. |
| Python unittest | Automated unit tests; additional Python assertions check integration scenarios and source reconciliation. |
| Python standard library | Decimal price conversion, SHA-256 checksums, JSON evidence, timing, file handling and source retrieval. |
| Windows and PowerShell | Local development environment, launch scripts and command execution. |
| Git, GitHub and GitHub CLI/API | Version history, phased commits, repository hosting and verified publication. |

## Documentation and presentation

| Technology or format | Use in this project |
| --- | --- |
| Markdown | Portfolio reports, README guides, references and technical explanations. |
| HTML and CSS | Local evidence preview pages. |
| Pillow and PNG | ER, transaction, document-model and architecture diagrams with reliable GitHub display. |
| Mermaid | Earlier diagram notation; displayed diagrams were replaced by PNGs after rendering problems. |
| ReportLab and PDF | Generating the three-page portfolio summary. |
| Poppler | Rendering PDF pages to images for visual layout checks. |
| JSON and plain-text logs | Structured results, source manifests, checksums and execution evidence. |
| Microsoft Excel workbook format (.xlsx) | Original NBS source tables, read programmatically with openpyxl. |

## AI assistance and student review

I used OpenAI Codex to assist with source research, project planning, SQL and Python implementation, debugging, diagrams, explanations, document preparation and automated verification. I directed the phased workflow and requested corrections to repository organisation and diagram display.

On 18 October 2026, I confirmed that I had reviewed Portfolios 1–5 and found them satisfactory. I first reviewed and approved Portfolio 1 on 14 October 2026. This records my review and approval; automated execution results are documented separately in the test and audit evidence.

I have included the assessment's required AI declaration in the submission summary. My personal reflection will describe my own learning and experience.

## Data source and proposed architecture

The National Bureau of Statistics (Nigeria) Selected Food Price Watch supplies the real source data. It is a data provider, not a software tool. Source URLs, checksums and usage limits are recorded in Portfolio 1.

Managed PostgreSQL, standby/read replicas and cloud backup services are discussed as a proposed production architecture in Portfolio 5. They were not deployed. The executed distributed exercise uses separate local SQLite files.
