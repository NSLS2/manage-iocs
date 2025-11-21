"""Interface for ``python -m manage_iocs``."""

import inspect
import sys
from collections.abc import Callable

from . import commands


def get_command_from_args(args: list[str]) -> Callable:
    if len(args) < 2:
        raise RuntimeError("No command provided!")

    command = getattr(commands, args[1], None)
    if not command or not inspect.isfunction(command):
        raise RuntimeError(f"Unknown command: {args[1]}")

    if not bool(inspect.signature(command).parameters):
        return command
    elif len(args) < 3:
        raise RuntimeError(f"Command '{command.__name__}' requires additional arguments!")

    # Return a lambda that calls the command with the additional args
    # Assign it the same name as the original command for testing purposes
    def command_w_args():
        return command(*args[2:])

    command_w_args.__name__ = command.__name__

    return command_w_args


def main():
    get_command_from_args(sys.argv)()


if __name__ == "__main__":
    sys.exit(main())
