# Portfolio 1: Database design and modelling

**Status:** implemented and tested; student reviewed and approved on 14 October 2026.

- [Design, normalisation and data dictionary](design.md)
- [ER diagram](er_diagram.png)
- [Schema](schema.sql)
- [Verification and source reconciliation](verification.md)
- [Source manifest](sources.json)

From the repository root:

```powershell
python -m pip install -r portfolio1/requirements.txt
python portfolio1/build.py all
python portfolio1/tests.py
```

Use `validate` instead of `all` to check an existing database. The optional PowerShell launcher is `./portfolio1/run.ps1`. Sources and the populated database stay in the ignored `.local` folder. See the [project guide](../final_documentation/project_guide.md) for source-use restrictions and reproduction details.
