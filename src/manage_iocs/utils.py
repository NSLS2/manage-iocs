import functools
import os
import socket
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from subprocess import PIPE, Popen

IOC_SEARCH_PATH = [Path("/epics/iocs"), Path("/opt/epics/iocs"), Path("/opt/iocs")]
if "MANAGE_IOCS_SEARCH_PATH" in os.environ:
    IOC_SEARCH_PATH.extend(
        [Path(p) for p in os.environ["MANAGE_IOCS_SEARCH_PATH"].split(os.pathsep)]
    )

SYSTEMD_SERVICE_PATH = Path("/etc/systemd/system")
MANAGE_IOCS_LOG_PATH = Path("/var/log/softioc")


@dataclass
class IOC:
    name: str
    user: str
    procserv_port: int
    path: Path
    host: str
    exec_path: str
    chdir: str


def read_config_file(config_path: Path) -> dict[str, str]:
    """Read config file for IOC"""
    config: dict[str, str] = {}
    with open(config_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config


def find_iocs() -> dict[str, IOC]:
    """Get a list of IOCs available in the search paths."""
    iocs = {}
    search_paths = IOC_SEARCH_PATH
    for search_path in search_paths:
        if os.path.exists(search_path):
            for item in os.listdir(search_path):
                if os.path.isdir(search_path / item) and os.path.exists(
                    search_path / item / "config"
                ):
                    config = read_config_file(search_path / item / "config")
                    iocs[item] = IOC(
                        name=item,
                        procserv_port=int(config["PORT"]),
                        path=search_path / item,
                        host=config.get("HOST", "localhost"),
                        user=config.get("USER", "iocuser"),
                        exec_path=config.get("EXEC", "st.cmd"),
                        chdir=config.get("CHDIR", "."),
                    )
    return iocs


def find_iocs_on_host() -> dict[str, IOC]:
    """Get a list of IOCs available on the given host."""
    all_iocs = find_iocs()
    return {
        name: ioc
        for name, ioc in all_iocs.items()
        if ioc.host == socket.gethostname() or ioc.host == "localhost"
    }


def find_installed_iocs() -> dict[str, IOC]:
    """Get a list of IOCs that have systemd service files installed."""
    iocs = {}
    for ioc in find_iocs().values():
        service_file = SYSTEMD_SERVICE_PATH / f"softioc-{ioc.name}.service"
        if service_file.exists():
            iocs[ioc.name] = ioc
    return iocs


def get_ioc_procserv_port(ioc: str) -> int:
    """Get the procServ port number for the given IOC."""

    return find_iocs()[ioc].procserv_port


def systemctl_passthrough(action: str, ioc: str) -> tuple[str, str, int]:
    """Helper to call systemctl with the given action and IOC name."""
    proc = Popen(["systemctl", action, f"softioc-{ioc}.service"], stdin=PIPE, stdout=PIPE)
    out, err = proc.communicate()
    decoded_out = out.decode().strip() if out else ""
    decoded_err = err.decode().strip() if err else ""
    return decoded_out, decoded_err, proc.returncode


def get_ioc_status(ioc_name: str) -> tuple[str, bool]:
    """Get the active and enabled status of the given IOC."""

    state, err, _ = systemctl_passthrough("is-active", ioc_name)

    # Convert to more user-friendly terms
    if state == "active":
        state = "Running"
    elif state == "inactive":
        state = "Stopped"

    enabled, err, _ = systemctl_passthrough("is-enabled", ioc_name)
    if enabled not in ("enabled", "disabled"):
        raise RuntimeError(err)

    return state.capitalize(), enabled == "enabled"


def requires_root(func: Callable):
    @functools.wraps(func)
    def wrapper(*args):
        if os.geteuid() != 0:
            raise PermissionError(f"Command {func.__name__} requires root privileges.")
        return func(*args)

    return wrapper


def requires_ioc_installed(func: Callable):
    @functools.wraps(func)
    def wrapper(ioc: str, *args, **kwargs):
        installed_iocs = find_installed_iocs()
        if ioc not in installed_iocs:
            raise RuntimeError(f"No IOC with name '{ioc}' is installed!")
        return func(ioc, *args, **kwargs)

    return wrapper
