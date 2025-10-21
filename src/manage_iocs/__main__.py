"""Interface for ``python -m manage_iocs``."""

import inspect
import sys

from . import commands


def main():
    if len(sys.argv) < 2:
        raise RuntimeError("No command provided!")

    command = getattr(commands, sys.argv[1], None)
    if not command or not inspect.isfunction(command):
        raise RuntimeError(f"Unknown command: {sys.argv[1]}")

    if not bool(inspect.signature(command).parameters):
        return command()
    elif len(sys.argv) < 3:
        raise RuntimeError(f"Command '{command.__name__}' requires additional arguments!")
    return command(*sys.argv[2:])


if __name__ == "__main__":
    sys.exit(main())
