"""Fault injection components for adversarial testing.

This module provides fault injectors for testing spec-kitty's error
handling and recovery mechanisms:

- process_faults.py: SIGTERM, SIGKILL, process crashes, timeouts
- file_faults.py: File corruption, permissions, git conflicts
- auth_faults.py: Credential invalidation, expiration, rate limits
- resource_faults.py: Disk exhaustion, memory pressure, CPU stress

All fault injectors support:
- Backup and restore for reversibility
- Trigger conditions (immediate, delayed, random)
- Container and local process targeting

Per CLAUDE.md: These are distribution tests - spec-kitty is installed from PyPI,
NOT from local source. No SPEC_KITTY_TEMPLATE_ROOT is ever set.

Example usage:
    from tests.agentic.faults import (
        ProcessFaultInjector,
        FileFaultInjector,
        AuthFaultInjector,
        ResourceFaultInjector,
    )

    # Kill agent process
    injector = ProcessFaultInjector(signal_type=signal.SIGKILL)
    result = injector.inject_container(container, "spec-kitty")

    # Corrupt spec file
    injector = FileFaultInjector(corruption_type=CorruptionType.TRUNCATE)
    result = injector.inject("/path/to/spec.md")

    # Invalidate API key
    injector = AuthFaultInjector(
        fault_type=AuthFaultType.INVALID_API_KEY,
        credential_type=CredentialType.ANTHROPIC_API_KEY
    )
    result = injector.inject()

    # Fill disk to 90%
    injector = ResourceFaultInjector(
        resource_type=ResourceType.DISK,
        exhaustion_level=ExhaustionLevel.SEVERE
    )
    result = injector.inject("/workspace")
"""

from .process_faults import (
    # Base classes
    BaseFaultInjector,
    TriggerCondition,
    FaultInjectionError,
    FaultInjectionResult,
    ProcessNotFoundError,
    ContainerNotRunningError,
    # Process fault injectors
    ProcessFaultInjector,
    TimeoutFaultInjector,
    ProcessCrashInjector,
)

from .file_faults import (
    # Enums
    CorruptionType,
    PermissionFault,
    # Data classes
    FileBackup,
    # Fault injectors
    FileFaultInjector,
    PermissionFaultInjector,
    GitFaultInjector,
)

from .auth_faults import (
    # Enums
    AuthFaultType,
    CredentialType,
    # Data classes
    CredentialBackup,
    # Fault injectors
    AuthFaultInjector,
    MultiCredentialFaultInjector,
)

from .resource_faults import (
    # Enums
    ResourceType,
    ExhaustionLevel,
    # Data classes
    ResourceState,
    # Fault injectors
    ResourceFaultInjector,
    DiskQuotaInjector,
    # Constants
    EXHAUSTION_PERCENTAGES,
)


__all__ = [
    # Base classes and common types
    "BaseFaultInjector",
    "TriggerCondition",
    "FaultInjectionError",
    "FaultInjectionResult",
    "ProcessNotFoundError",
    "ContainerNotRunningError",
    # Process faults
    "ProcessFaultInjector",
    "TimeoutFaultInjector",
    "ProcessCrashInjector",
    # File faults
    "CorruptionType",
    "PermissionFault",
    "FileBackup",
    "FileFaultInjector",
    "PermissionFaultInjector",
    "GitFaultInjector",
    # Auth faults
    "AuthFaultType",
    "CredentialType",
    "CredentialBackup",
    "AuthFaultInjector",
    "MultiCredentialFaultInjector",
    # Resource faults
    "ResourceType",
    "ExhaustionLevel",
    "ResourceState",
    "ResourceFaultInjector",
    "DiskQuotaInjector",
    "EXHAUSTION_PERCENTAGES",
]
