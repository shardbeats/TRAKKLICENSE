"""Single source of truth for the app version.

Bumped manually per release. pyproject.toml reads it dynamically and
build_exe.py parses it with regex (no import needed).
"""

__version__ = "1.0.0"
