from dataclasses import dataclass


@dataclass
class IOC:
    name: str
    top_path: str
    startup_script: str
    procserv_port: int
    description: str