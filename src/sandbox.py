"""Run untrusted JavaScript in a locked-down container.

The agent has so far only ever *reasoned* about whether code breaks. This lets
it check. A claim like "Object.keys(undefined) throws" stops being an opinion
and becomes something with an exit code.

The code being run comes from a language model that just read a stranger's pull
request, so it is treated as hostile:

  --network none   no internet, no exfiltration, no downloading anything
  --memory 256m    an infinite loop allocating memory cannot take the machine down
  --pids-limit     fork bombs cannot spawn unbounded processes
  --rm             the container is destroyed after every single run
  timeout          a hung script is killed rather than waited on forever

The script is piped to `node` over stdin rather than mounted as a file. That
avoids Windows/Linux volume-path differences entirely — there is no shared
directory at any point.
"""
import shutil
import subprocess
from dataclasses import dataclass

IMAGE = "node:20-alpine"
DEFAULT_TIMEOUT = 20


@dataclass
class RunResult:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool
    available: bool = True

    @property
    def output(self) -> str:
        return f"{self.stdout}\n{self.stderr}".strip()


def docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        proc = subprocess.run(
            ["docker", "info"], capture_output=True, timeout=15, text=True
        )
        return proc.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def run_js(script: str, timeout: int = DEFAULT_TIMEOUT) -> RunResult:
    """Execute a self-contained JS snippet. Never raises."""
    if not docker_available():
        return RunResult("", "docker unavailable", -1, False, available=False)

    cmd = [
        "docker", "run", "--rm", "-i",
        "--network", "none",
        "--memory", "256m",
        "--pids-limit", "128",
        IMAGE,
        "node",
    ]

    try:
        proc = subprocess.run(
            cmd,
            input=script,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return RunResult("", f"timed out after {timeout}s", -1, True)
    except Exception as err:  # noqa: BLE001
        return RunResult("", str(err)[:300], -1, False)

    return RunResult(
        stdout=(proc.stdout or "")[:4000],
        stderr=(proc.stderr or "")[:2000],
        exit_code=proc.returncode,
        timed_out=False,
    )


def ensure_image() -> bool:
    """Pull the runtime image once, so the first review is not mysteriously slow."""
    if not docker_available():
        return False
    try:
        subprocess.run(
            ["docker", "image", "inspect", IMAGE],
            capture_output=True, timeout=15, check=True,
        )
        return True
    except Exception:  # noqa: BLE001
        pass
    try:
        subprocess.run(["docker", "pull", IMAGE], timeout=300, check=True)
        return True
    except Exception:  # noqa: BLE001
        return False
