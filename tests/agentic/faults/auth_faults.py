"""Authentication fault injection for adversarial testing.

This module provides fault injectors that simulate authentication failures:
- Credential invalidation: Remove or corrupt credentials
- Token expiration: Simulate expired API tokens
- Permission revocation: Remove access to resources
- Rate limiting: Simulate API rate limit errors

Per CLAUDE.md: These are distribution tests - spec-kitty is installed from PyPI,
NOT from local source. No SPEC_KITTY_TEMPLATE_ROOT is ever set.
"""

import json
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from .process_faults import (
    BaseFaultInjector,
    ContainerNotRunningError,
    FaultInjectionError,
    FaultInjectionResult,
    TriggerCondition,
)

if TYPE_CHECKING:
    from ..fixtures.container_fixtures import TestContainer


class AuthFaultType(Enum):
    """Types of authentication faults to inject.

    CREDENTIAL_REMOVAL: Remove credential files entirely
    CREDENTIAL_CORRUPTION: Corrupt credential content
    TOKEN_EXPIRATION: Modify token to appear expired
    PERMISSION_DENIED: Simulate permission/scope issues
    RATE_LIMIT: Simulate rate limit exceeded
    INVALID_API_KEY: Replace API key with invalid value
    NETWORK_AUTH_FAIL: Simulate network-level auth failure
    """

    CREDENTIAL_REMOVAL = "credential_removal"
    CREDENTIAL_CORRUPTION = "credential_corruption"
    TOKEN_EXPIRATION = "token_expiration"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMIT = "rate_limit"
    INVALID_API_KEY = "invalid_api_key"
    NETWORK_AUTH_FAIL = "network_auth_fail"


class CredentialType(Enum):
    """Types of credentials that can be targeted.

    ANTHROPIC_API_KEY: Anthropic API key (ANTHROPIC_API_KEY env var)
    OPENAI_API_KEY: OpenAI API key (OPENAI_API_KEY env var)
    GITHUB_TOKEN: GitHub personal access token
    GIT_CREDENTIALS: Git credential helper cache
    SSH_KEY: SSH private keys
    OAUTH_TOKEN: OAuth2 access tokens
    AWS_CREDENTIALS: AWS access key and secret
    CUSTOM: Custom credential path
    """

    ANTHROPIC_API_KEY = "anthropic_api_key"
    OPENAI_API_KEY = "openai_api_key"
    GITHUB_TOKEN = "github_token"
    GIT_CREDENTIALS = "git_credentials"
    SSH_KEY = "ssh_key"
    OAUTH_TOKEN = "oauth_token"
    AWS_CREDENTIALS = "aws_credentials"
    CUSTOM = "custom"


@dataclass
class CredentialBackup:
    """Backup of credential for restoration.

    Attributes:
        credential_type: Type of credential backed up
        original_path: Original path or env var name
        backup_value: Backed up value (env var) or path (file)
        is_env_var: Whether this is an environment variable
        created_at: When backup was created
    """

    credential_type: CredentialType
    original_path: str
    backup_value: Optional[str]
    is_env_var: bool = False
    created_at: datetime = field(default_factory=datetime.now)


class AuthFaultInjector(BaseFaultInjector):
    """Inject authentication-related faults for testing error handling.

    Supports:
    - Credential removal/corruption
    - Token expiration simulation
    - API key invalidation
    - Rate limit simulation (via mock responses)

    All operations support backup and restore for test cleanup.

    Example usage:
        injector = AuthFaultInjector(
            fault_type=AuthFaultType.CREDENTIAL_REMOVAL,
            credential_type=CredentialType.ANTHROPIC_API_KEY
        )
        result = injector.inject()  # Removes ANTHROPIC_API_KEY
        # ... test auth failure handling ...
        injector.restore()  # Restores original key

    For containers:
        result = injector.inject_container(
            container,
            credential_path="/root/.anthropic/credentials"
        )
    """

    # Known credential file paths for each type
    CREDENTIAL_PATHS: Dict[CredentialType, List[str]] = {
        CredentialType.GIT_CREDENTIALS: [
            "~/.git-credentials",
            "~/.config/git/credentials",
        ],
        CredentialType.SSH_KEY: [
            "~/.ssh/id_rsa",
            "~/.ssh/id_ed25519",
            "~/.ssh/id_ecdsa",
        ],
        CredentialType.AWS_CREDENTIALS: [
            "~/.aws/credentials",
            "~/.aws/config",
        ],
        CredentialType.GITHUB_TOKEN: [
            "~/.config/gh/hosts.yml",
        ],
    }

    # Environment variables for each credential type
    CREDENTIAL_ENV_VARS: Dict[CredentialType, str] = {
        CredentialType.ANTHROPIC_API_KEY: "ANTHROPIC_API_KEY",
        CredentialType.OPENAI_API_KEY: "OPENAI_API_KEY",
        CredentialType.GITHUB_TOKEN: "GITHUB_TOKEN",
        CredentialType.AWS_CREDENTIALS: "AWS_ACCESS_KEY_ID",
    }

    def __init__(
        self,
        fault_type: AuthFaultType = AuthFaultType.CREDENTIAL_REMOVAL,
        credential_type: CredentialType = CredentialType.ANTHROPIC_API_KEY,
        custom_path: Optional[str] = None,
        trigger: TriggerCondition = TriggerCondition.IMMEDIATE,
        delay_seconds: float = 0.0,
    ):
        """Initialize auth fault injector.

        Args:
            fault_type: Type of authentication fault to inject
            credential_type: Type of credential to target
            custom_path: Custom credential path (for CUSTOM type)
            trigger: When to trigger the fault
            delay_seconds: Delay for DELAYED trigger
        """
        super().__init__(trigger=trigger, delay_seconds=delay_seconds)
        self.fault_type = fault_type
        self.credential_type = credential_type
        self.custom_path = custom_path
        self._backups: Dict[str, CredentialBackup] = {}
        self._backup_dir = Path(tempfile.mkdtemp(prefix="auth_backup_"))

    def inject(self, target: Any = None, **kwargs) -> FaultInjectionResult:
        """Inject authentication fault.

        Args:
            target: Optional target (path or env var name)
            **kwargs: Additional parameters

        Returns:
            FaultInjectionResult with injection details
        """
        self._apply_trigger_delay()

        if self.fault_type == AuthFaultType.CREDENTIAL_REMOVAL:
            return self._inject_credential_removal(target)
        elif self.fault_type == AuthFaultType.CREDENTIAL_CORRUPTION:
            return self._inject_credential_corruption(target)
        elif self.fault_type == AuthFaultType.TOKEN_EXPIRATION:
            return self._inject_token_expiration(target)
        elif self.fault_type == AuthFaultType.INVALID_API_KEY:
            return self._inject_invalid_api_key(target)
        elif self.fault_type == AuthFaultType.RATE_LIMIT:
            return self._inject_rate_limit(target)
        else:
            raise FaultInjectionError(f"Unknown fault type: {self.fault_type}")

    def inject_container(
        self,
        container: "TestContainer",
        credential_path: Optional[str] = None,
        env_var: Optional[str] = None,
        **kwargs,
    ) -> FaultInjectionResult:
        """Inject authentication fault inside a container.

        Args:
            container: TestContainer instance
            credential_path: Path to credential file inside container
            env_var: Environment variable to modify
            **kwargs: Additional parameters

        Returns:
            FaultInjectionResult with injection details
        """
        if not container.is_running:
            raise ContainerNotRunningError(
                f"Container {container.container_id} is not running"
            )

        self._apply_trigger_delay()

        if self.fault_type == AuthFaultType.CREDENTIAL_REMOVAL:
            return self._inject_container_credential_removal(
                container, credential_path, env_var
            )
        elif self.fault_type == AuthFaultType.CREDENTIAL_CORRUPTION:
            return self._inject_container_credential_corruption(
                container, credential_path
            )
        elif self.fault_type == AuthFaultType.INVALID_API_KEY:
            return self._inject_container_invalid_api_key(container, env_var)
        else:
            # For other types, use generic container approach
            return self._inject_container_generic(container, **kwargs)

    def _inject_credential_removal(
        self, target: Optional[Any] = None
    ) -> FaultInjectionResult:
        """Remove credential file or environment variable."""
        # Try environment variable first
        env_var = self.CREDENTIAL_ENV_VARS.get(self.credential_type)
        if env_var and env_var in os.environ:
            original_value = os.environ[env_var]
            self._backups[env_var] = CredentialBackup(
                credential_type=self.credential_type,
                original_path=env_var,
                backup_value=original_value,
                is_env_var=True,
            )
            del os.environ[env_var]

            result = FaultInjectionResult(
                success=True,
                fault_type=f"auth_removal_{self.credential_type.value}",
                target=env_var,
                metadata={
                    "credential_type": self.credential_type.value,
                    "removed_env_var": env_var,
                },
            )
            self._injections.append(result)
            return result

        # Try file paths
        paths = self.CREDENTIAL_PATHS.get(self.credential_type, [])
        if self.custom_path:
            paths = [self.custom_path]

        for path_str in paths:
            path = Path(path_str).expanduser()
            if path.exists():
                # Backup file
                backup_path = self._backup_dir / f"{path.name}.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                shutil.copy2(path, backup_path)

                self._backups[str(path)] = CredentialBackup(
                    credential_type=self.credential_type,
                    original_path=str(path),
                    backup_value=str(backup_path),
                    is_env_var=False,
                )

                # Remove original
                path.unlink()

                result = FaultInjectionResult(
                    success=True,
                    fault_type=f"auth_removal_{self.credential_type.value}",
                    target=str(path),
                    metadata={
                        "credential_type": self.credential_type.value,
                        "removed_file": str(path),
                        "backup_path": str(backup_path),
                    },
                )
                self._injections.append(result)
                return result

        # No credential found
        result = FaultInjectionResult(
            success=False,
            fault_type=f"auth_removal_{self.credential_type.value}",
            target=str(target) if target else "none",
            error=f"No {self.credential_type.value} credential found to remove",
        )
        self._injections.append(result)
        return result

    def _inject_credential_corruption(
        self, target: Optional[Any] = None
    ) -> FaultInjectionResult:
        """Corrupt credential content."""
        # Try environment variable first
        env_var = self.CREDENTIAL_ENV_VARS.get(self.credential_type)
        if env_var and env_var in os.environ:
            original_value = os.environ[env_var]
            self._backups[env_var] = CredentialBackup(
                credential_type=self.credential_type,
                original_path=env_var,
                backup_value=original_value,
                is_env_var=True,
            )
            # Corrupt by replacing with invalid value
            os.environ[env_var] = "corrupted_invalid_credential_value_xyz"

            result = FaultInjectionResult(
                success=True,
                fault_type=f"auth_corruption_{self.credential_type.value}",
                target=env_var,
                metadata={
                    "credential_type": self.credential_type.value,
                    "corrupted_env_var": env_var,
                },
            )
            self._injections.append(result)
            return result

        # Try file paths
        paths = self.CREDENTIAL_PATHS.get(self.credential_type, [])
        if self.custom_path:
            paths = [self.custom_path]

        for path_str in paths:
            path = Path(path_str).expanduser()
            if path.exists():
                # Backup file
                backup_path = self._backup_dir / f"{path.name}.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                shutil.copy2(path, backup_path)

                self._backups[str(path)] = CredentialBackup(
                    credential_type=self.credential_type,
                    original_path=str(path),
                    backup_value=str(backup_path),
                    is_env_var=False,
                )

                # Corrupt file content
                with open(path, "w") as f:
                    f.write("CORRUPTED_CREDENTIAL_CONTENT_INVALID")

                result = FaultInjectionResult(
                    success=True,
                    fault_type=f"auth_corruption_{self.credential_type.value}",
                    target=str(path),
                    metadata={
                        "credential_type": self.credential_type.value,
                        "corrupted_file": str(path),
                    },
                )
                self._injections.append(result)
                return result

        result = FaultInjectionResult(
            success=False,
            fault_type=f"auth_corruption_{self.credential_type.value}",
            target=str(target) if target else "none",
            error=f"No {self.credential_type.value} credential found to corrupt",
        )
        self._injections.append(result)
        return result

    def _inject_token_expiration(
        self, target: Optional[Any] = None
    ) -> FaultInjectionResult:
        """Simulate token expiration by modifying token metadata."""
        # For OAuth tokens stored in JSON files
        paths = self.CREDENTIAL_PATHS.get(self.credential_type, [])
        if self.custom_path:
            paths = [self.custom_path]

        for path_str in paths:
            path = Path(path_str).expanduser()
            if path.exists():
                # Backup file
                backup_path = self._backup_dir / f"{path.name}.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                shutil.copy2(path, backup_path)

                self._backups[str(path)] = CredentialBackup(
                    credential_type=self.credential_type,
                    original_path=str(path),
                    backup_value=str(backup_path),
                    is_env_var=False,
                )

                # Try to parse as JSON and modify expiry
                try:
                    with open(path) as f:
                        content = json.load(f)

                    # Modify common expiry fields
                    if "expires_at" in content:
                        content["expires_at"] = "2020-01-01T00:00:00Z"
                    if "expiry" in content:
                        content["expiry"] = 0
                    if "exp" in content:
                        content["exp"] = 0

                    with open(path, "w") as f:
                        json.dump(content, f)

                except json.JSONDecodeError:
                    # Not JSON, just corrupt it
                    with open(path, "w") as f:
                        f.write("EXPIRED_TOKEN")

                result = FaultInjectionResult(
                    success=True,
                    fault_type=f"auth_expiration_{self.credential_type.value}",
                    target=str(path),
                    metadata={
                        "credential_type": self.credential_type.value,
                        "modified_file": str(path),
                    },
                )
                self._injections.append(result)
                return result

        result = FaultInjectionResult(
            success=False,
            fault_type=f"auth_expiration_{self.credential_type.value}",
            target=str(target) if target else "none",
            error=f"No {self.credential_type.value} token found to expire",
        )
        self._injections.append(result)
        return result

    def _inject_invalid_api_key(
        self, target: Optional[Any] = None
    ) -> FaultInjectionResult:
        """Replace API key with invalid value."""
        env_var = self.CREDENTIAL_ENV_VARS.get(self.credential_type)
        if not env_var:
            raise FaultInjectionError(
                f"No environment variable mapping for {self.credential_type.value}"
            )

        original_value = os.environ.get(env_var)
        if original_value:
            self._backups[env_var] = CredentialBackup(
                credential_type=self.credential_type,
                original_path=env_var,
                backup_value=original_value,
                is_env_var=True,
            )

        # Set invalid API key that looks valid but isn't
        invalid_keys = {
            CredentialType.ANTHROPIC_API_KEY: "sk-ant-api03-INVALID-KEY-FOR-TESTING-xxxxxxxxxxxxxxxx",
            CredentialType.OPENAI_API_KEY: "sk-INVALID-KEY-FOR-TESTING-xxxxxxxxxxxxxxxxxxxx",
            CredentialType.GITHUB_TOKEN: "ghp_INVALID_TOKEN_FOR_TESTING_xxxxxxxxxx",
        }

        invalid_key = invalid_keys.get(
            self.credential_type, "INVALID_API_KEY_FOR_TESTING"
        )
        os.environ[env_var] = invalid_key

        result = FaultInjectionResult(
            success=True,
            fault_type=f"auth_invalid_key_{self.credential_type.value}",
            target=env_var,
            metadata={
                "credential_type": self.credential_type.value,
                "env_var": env_var,
                "had_original": original_value is not None,
            },
        )
        self._injections.append(result)
        return result

    def _inject_rate_limit(self, target: Optional[Any] = None) -> FaultInjectionResult:
        """Simulate rate limiting.

        This creates a marker that can be checked by test code.
        Actual rate limiting simulation requires mocking HTTP responses.
        """
        rate_limit_marker = self._backup_dir / "rate_limit_active"
        rate_limit_marker.write_text(
            json.dumps(
                {
                    "credential_type": self.credential_type.value,
                    "activated_at": datetime.now().isoformat(),
                    "retry_after": 60,
                }
            )
        )

        self._backups["rate_limit_marker"] = CredentialBackup(
            credential_type=self.credential_type,
            original_path=str(rate_limit_marker),
            backup_value=None,
            is_env_var=False,
        )

        result = FaultInjectionResult(
            success=True,
            fault_type=f"auth_rate_limit_{self.credential_type.value}",
            target=str(rate_limit_marker),
            metadata={
                "credential_type": self.credential_type.value,
                "marker_path": str(rate_limit_marker),
                "note": "Test code should check marker to simulate rate limit responses",
            },
        )
        self._injections.append(result)
        return result

    def _inject_container_credential_removal(
        self,
        container: "TestContainer",
        credential_path: Optional[str],
        env_var: Optional[str],
    ) -> FaultInjectionResult:
        """Remove credentials inside container."""
        removed_items = []

        # Handle environment variable
        if env_var:
            # We can't directly unset env vars in a running container
            # but we can modify the entrypoint or use docker exec with unset
            exit_code, stdout, stderr = container.exec_command(
                f"unset {env_var} && echo 'unset'", timeout=10
            )
            removed_items.append(f"env:{env_var}")

        # Handle file path
        if credential_path:
            # Backup first
            backup_path = f"/tmp/cred_backup_{os.urandom(4).hex()}"
            container.exec_command(
                f"cp '{credential_path}' '{backup_path}' 2>/dev/null || true",
                timeout=30,
            )

            # Remove
            exit_code, stdout, stderr = container.exec_command(
                f"rm -f '{credential_path}'", timeout=10
            )
            if exit_code == 0:
                removed_items.append(f"file:{credential_path}")

        result = FaultInjectionResult(
            success=len(removed_items) > 0,
            fault_type=f"container_auth_removal_{self.credential_type.value}",
            target=container.container_id,
            metadata={
                "container_id": container.container_id,
                "removed_items": removed_items,
            },
            error="No credentials found to remove" if not removed_items else None,
        )
        self._injections.append(result)
        return result

    def _inject_container_credential_corruption(
        self,
        container: "TestContainer",
        credential_path: Optional[str],
    ) -> FaultInjectionResult:
        """Corrupt credentials inside container."""
        if not credential_path:
            raise FaultInjectionError("credential_path required for container corruption")

        # Backup first
        backup_path = f"/tmp/cred_backup_{os.urandom(4).hex()}"
        container.exec_command(
            f"cp '{credential_path}' '{backup_path}' 2>/dev/null || true",
            timeout=30,
        )

        # Corrupt
        exit_code, stdout, stderr = container.exec_command(
            f"echo 'CORRUPTED_CREDENTIAL' > '{credential_path}'", timeout=10
        )

        result = FaultInjectionResult(
            success=exit_code == 0,
            fault_type=f"container_auth_corruption_{self.credential_type.value}",
            target=f"{container.container_id}:{credential_path}",
            metadata={
                "container_id": container.container_id,
                "credential_path": credential_path,
                "backup_path": backup_path,
            },
            error=stderr if exit_code != 0 else None,
        )
        self._injections.append(result)
        return result

    def _inject_container_invalid_api_key(
        self,
        container: "TestContainer",
        env_var: Optional[str],
    ) -> FaultInjectionResult:
        """Set invalid API key in container environment."""
        env_var = env_var or self.CREDENTIAL_ENV_VARS.get(self.credential_type)
        if not env_var:
            raise FaultInjectionError("Environment variable name required")

        # Set invalid key via export (for subsequent commands)
        invalid_key = "INVALID_API_KEY_FOR_TESTING_xxxxxxxxxx"
        exit_code, stdout, stderr = container.exec_command(
            f"export {env_var}='{invalid_key}' && echo ${{env_var}}",
            timeout=10,
        )

        result = FaultInjectionResult(
            success=True,  # We can't verify the export persists
            fault_type=f"container_auth_invalid_key_{self.credential_type.value}",
            target=f"{container.container_id}:{env_var}",
            metadata={
                "container_id": container.container_id,
                "env_var": env_var,
                "note": "Export only affects subsequent commands in same shell",
            },
        )
        self._injections.append(result)
        return result

    def _inject_container_generic(
        self,
        container: "TestContainer",
        **kwargs,
    ) -> FaultInjectionResult:
        """Generic container auth fault injection."""
        result = FaultInjectionResult(
            success=False,
            fault_type=f"container_auth_{self.fault_type.value}",
            target=container.container_id,
            error=f"Fault type {self.fault_type.value} not implemented for containers",
        )
        self._injections.append(result)
        return result

    def is_rate_limited(self) -> bool:
        """Check if rate limit simulation is active.

        Test code should call this to simulate rate limit responses.

        Returns:
            True if rate limit is simulated as active
        """
        marker = self._backup_dir / "rate_limit_active"
        return marker.exists()

    def get_rate_limit_info(self) -> Optional[Dict[str, Any]]:
        """Get rate limit simulation info.

        Returns:
            Dict with rate limit details or None if not active
        """
        marker = self._backup_dir / "rate_limit_active"
        if marker.exists():
            return json.loads(marker.read_text())
        return None

    def can_restore(self) -> bool:
        """Check if credentials can be restored."""
        return len(self._backups) > 0

    def restore(self) -> bool:
        """Restore all backed up credentials."""
        if not self.can_restore():
            return False

        success = True

        for key, backup in list(self._backups.items()):
            try:
                if backup.is_env_var:
                    # Restore environment variable
                    if backup.backup_value is not None:
                        os.environ[backup.original_path] = backup.backup_value
                    elif backup.original_path in os.environ:
                        del os.environ[backup.original_path]
                else:
                    # Restore file
                    if backup.backup_value and Path(backup.backup_value).exists():
                        shutil.copy2(backup.backup_value, backup.original_path)

                del self._backups[key]
            except Exception:
                success = False

        return success

    def cleanup(self) -> None:
        """Clean up backup directory."""
        try:
            shutil.rmtree(self._backup_dir)
        except Exception:
            pass


class MultiCredentialFaultInjector:
    """Inject faults across multiple credential types simultaneously.

    Useful for testing scenarios where multiple auth mechanisms fail.

    Example usage:
        injector = MultiCredentialFaultInjector()
        injector.add_fault(
            AuthFaultType.CREDENTIAL_REMOVAL,
            CredentialType.ANTHROPIC_API_KEY
        )
        injector.add_fault(
            AuthFaultType.INVALID_API_KEY,
            CredentialType.GITHUB_TOKEN
        )
        results = injector.inject_all()
        # ... test multi-auth failure handling ...
        injector.restore_all()
    """

    def __init__(self):
        """Initialize multi-credential fault injector."""
        self._injectors: List[AuthFaultInjector] = []

    def add_fault(
        self,
        fault_type: AuthFaultType,
        credential_type: CredentialType,
        custom_path: Optional[str] = None,
    ) -> None:
        """Add a fault to be injected.

        Args:
            fault_type: Type of authentication fault
            credential_type: Type of credential to target
            custom_path: Custom credential path (for CUSTOM type)
        """
        self._injectors.append(
            AuthFaultInjector(
                fault_type=fault_type,
                credential_type=credential_type,
                custom_path=custom_path,
            )
        )

    def inject_all(self) -> List[FaultInjectionResult]:
        """Inject all configured faults.

        Returns:
            List of FaultInjectionResult for each fault
        """
        results = []
        for injector in self._injectors:
            try:
                result = injector.inject()
                results.append(result)
            except Exception as e:
                results.append(
                    FaultInjectionResult(
                        success=False,
                        fault_type=f"multi_{injector.fault_type.value}",
                        target=injector.credential_type.value,
                        error=str(e),
                    )
                )
        return results

    def restore_all(self) -> bool:
        """Restore all injected faults.

        Returns:
            True if all restorations succeeded
        """
        success = True
        for injector in self._injectors:
            if not injector.restore():
                success = False
        return success

    def cleanup(self) -> None:
        """Clean up all injectors."""
        for injector in self._injectors:
            injector.cleanup()
