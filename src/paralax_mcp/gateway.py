import hashlib
import json
import os
import re
import stat
from pathlib import Path
from axionorm import Engine, PolicyDenied
from parabiont.store import Store


class Gateway:
    def __init__(self, config):
        self.config = config
        self.root = Path(config["workspace"]).resolve(strict=True)
        self.output = Path(config["output"]).resolve(strict=True)
        self.store = Store(config["store"])
        if os.name != "posix":
            raise RuntimeError("Use Linux, macOS or WSL2 for the protected filesystem gateway")

    def authority(self):
        engine = Engine(self.config["policy"], self.config["opa"])
        capsule = self.store.read(self.config["bond_id"])
        if capsule["policy_digest"] != engine.policy_digest or capsule["audience"] != engine.policy["audience"]:
            raise PolicyDenied("Bond policy changed; issue a new handoff")
        return engine, capsule

    def manifest(self):
        value = json.loads(Path(self.config["manifest"]).read_text())
        if value.get("version") != "paralax-files/v0.1" or not isinstance(value.get("files"), dict):
            raise PolicyDenied("Invalid workspace manifest")
        return value["files"]

    @staticmethod
    def safe_name(name):
        return bool(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,100}", name)) and ".." not in name

    def workspace_list(self):
        engine, _ = self.authority()
        files = [n for n in self.manifest() if self.safe_name(n) and not engine.sensitive(n)]
        result = json.dumps(sorted(files))
        engine.authorize_tool("workspace_list", size=len(result.encode()), scope_valid=True)
        return files

    def context_read(self):
        engine, capsule = self.authority()
        state = capsule["state"]
        engine.authorize_tool("context_read", size=len(json.dumps(state).encode()), scope_valid=True)
        return {"purpose": capsule["purpose"], "state": state, "expires_at": capsule["expires_at"]}

    def workspace_read(self, name):
        engine, _ = self.authority()
        if not self.safe_name(name) or name not in self.manifest():
            raise PolicyDenied("File not approved")
        rule = next((r for r in engine.policy["tools"] if r["name"] == "workspace_read"), None)
        if not rule:
            raise PolicyDenied("Read unavailable")
        engine.authorize_tool("workspace_read", extension=Path(name).suffix, scope_valid=True)
        root_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root_fd)
            with os.fdopen(fd, "rb") as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > rule["max_bytes"]:
                    raise PolicyDenied("File type or size denied")
                content = stream.read(rule["max_bytes"] + 1)
        finally:
            os.close(root_fd)
        engine.authorize_tool("workspace_read", extension=Path(name).suffix, size=len(content), scope_valid=True)
        if hashlib.sha256(content).hexdigest() != self.manifest()[name]:
            raise PolicyDenied("File changed after approval")
        text = content.decode("utf-8")
        if engine.sensitive(text):
            raise PolicyDenied("Sensitive content blocked")
        return text

    def workspace_write(self, name, content):
        engine, _ = self.authority()
        if not self.safe_name(name) or engine.sensitive(name) or engine.sensitive(content):
            raise PolicyDenied("Artifact name or content denied")
        data = content.encode()
        engine.authorize_tool("workspace_write", extension=Path(name).suffix, size=len(data), scope_valid=True)
        root_fd = os.open(self.output, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            # Create only: never overwrite policy, source files, symlinks or previous artifacts.
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=root_fd)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
        finally:
            os.close(root_fd)
        return {"created": name, "bytes": len(data), "trust": "untrusted-agent-output"}
