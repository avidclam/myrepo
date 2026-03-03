## Language & Style
- Python 3.11+
- PEP8 formatting
- Type hints on all public functions
- Use built-in types for type hints (e.g. `list`, `dict`, `tuple`, `set`)
- Use `X | Y` union syntax, never `Optional[X]` or `Union[X, Y]`
- Never import from `typing` unless absolutely necessary (e.g. `Protocol`, `TypeVar`)
- Google-style docstrings for public APIs
- No unused imports or variables
- No wildcard imports
- Small, single-purpose functions

## Project Structure
- Package: `myrepo`
- One domain per module (e.g. `network`, `typechecks`)
- Keep modules small
- No circular imports
- Internal helpers start with `_`

## Testing
- pytest
- Every public function has at least one test in `tests/`
- Mirror structure:  
  `myrepo/x.py` → `tests/test_x.py`
- Tests must be deterministic (mock I/O, time, network)

## Error Handling
- No bare `except`
- Raise specific exceptions
- Do not swallow errors
- Use `logging`, never `print`

## Dependencies
- Minimize deps
- Prefer standard library
- Pin exact versions in `requirements.txt`

## Tooling
- Must pass: pytest, type checker, linter
- Use one formatter (black or ruff-format)
