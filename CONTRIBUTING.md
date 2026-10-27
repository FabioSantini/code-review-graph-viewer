# Contributing

Please open an issue with reproduction steps, the viewer version, OS, browser, and Code Review Graph version.
Use synthetic examples instead of uploading private code or databases.

Run `uv run pytest -q` and `npm test` before opening a pull request. Keep database access read-only,
never infer that missing graph edges prove independence, and preserve direction when aggregating edges.
Hidden summary groups must be disjoint and their counts must sum to the hidden total.

The Python package includes the static frontend in `graphviewer/static`; there is no Node build step.
The application is designed for local, trusted, single-user use. Do not add public hosting assumptions without discussing authentication and isolation first.
