"""Interface for ``python -m manage_iocs``."""

import argparse
from .commands import COMMANDS

def main():
    parser = argparse.ArgumentParser(
        description="Manage IOCs - Command Line Interface"
    )
    parser.add_argument(
        "command",
        choices=COMMANDS.keys(),
        help="Command to execute",
    )
    parser.add_argument(
        "ioc",
        help="Target IOC name (if applicable)",
        required=False,
        type=str,
    )

    args = parser.parse_args()
    command_info = COMMANDS[args.command]
    if command_info.requires_ioc_target and not args.ioc:
        parser.error(f"Command '{args.command}' requires a target IOC.")
    # Execute the command
    if command_info.requires_ioc_target:
        command_info.callable(args.ioc)
    else:
        command_info.callable()

if __name__ == "__main__":
    main()