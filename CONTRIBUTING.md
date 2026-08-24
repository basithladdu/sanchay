# Contributing to SANCHAY

Thank you for your interest in SANCHAY — Regret-Aware Storage Intelligence for Linux.

## Development Workflow

1. Fork and clone the repository.
2. Install in editable mode:
   ```bash
   pip install -e .
   ```
3. Run the test suite:
   ```bash
   make test  # or: python -m unittest discover tests
   ```
4. Run a local scan:
   ```bash
   make scan  # or: python -m sanchay.cli .
   ```

## Design Philosophy

- **Safety by Construction**: The AI model never decides what is safe to delete. Unique files must remain mathematically excluded from candidates.
- **Fast by Design**: Metadata-only traversal with tiered hash escalation.

## License

SANCHAY is open source under the [MIT License](LICENSE).
