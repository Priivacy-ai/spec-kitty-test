"""Human-readable test report generation for agentic E2E tests.

T041: Generate human-readable summary reports

This module provides:
- TestSummary: Aggregated test results
- ReportGenerator: Generates Markdown and JSON reports

Per CLAUDE.md: These are distribution tests - spec-kitty is installed from PyPI,
NOT from local source. No SPEC_KITTY_TEMPLATE_ROOT is ever set.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .fixtures.workflow_fixtures import TestRun


@dataclass
class TestSummary:
    """Summary of a test run.

    Aggregates results from multiple TestRun instances into a single
    summary suitable for reporting.

    Attributes:
        timestamp: When the summary was generated
        total_tests: Total number of tests
        passed: Number of passed tests
        failed: Number of failed tests
        skipped: Number of skipped tests
        errors: Number of tests with errors
        duration_seconds: Total test duration
        agents_used: List of agent IDs that were tested
        paths_tested: List of test path IDs
        failures: Details of failed tests
    """

    timestamp: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration_seconds: float
    agents_used: List[str]
    paths_tested: List[str]
    failures: List[Dict[str, Any]]

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate as percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100

    @property
    def success(self) -> bool:
        """Return True if all tests passed (no failures or errors)."""
        return self.failed == 0 and self.errors == 0


@dataclass
class ReportConfig:
    """Configuration for report generation.

    Attributes:
        include_failures: Include detailed failure information
        include_agents: Include agent list
        include_paths: Include path list
        include_metrics: Include performance metrics
        max_failure_details: Maximum failures to include details for
    """

    include_failures: bool = True
    include_agents: bool = True
    include_paths: bool = True
    include_metrics: bool = True
    max_failure_details: int = 10


class ReportGenerator:
    """Generates human-readable test reports.

    Creates Markdown and JSON reports from test results.

    Attributes:
        results_dir: Directory to write reports to
        config: Report configuration
    """

    def __init__(
        self,
        results_dir: Path,
        config: Optional[ReportConfig] = None,
    ):
        """Initialize the report generator.

        Args:
            results_dir: Directory for output files
            config: Optional report configuration
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or ReportConfig()

    def generate_summary(self, test_runs: List["TestRun"]) -> TestSummary:
        """Generate summary from test runs.

        Args:
            test_runs: List of completed TestRun instances

        Returns:
            TestSummary aggregating all runs
        """
        from .fixtures.workflow_fixtures import TestStatus

        passed = sum(1 for r in test_runs if r.status == TestStatus.PASSED)
        failed = sum(1 for r in test_runs if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in test_runs if r.status == TestStatus.SKIPPED)
        errors = sum(1 for r in test_runs if r.status == TestStatus.ERROR)

        agents = set()
        paths = set()
        failures = []

        for run in test_runs:
            for agent_id in run.agent_assignments.values():
                agents.add(agent_id)
            paths.add(run.path_id)

            if run.status in (TestStatus.FAILED, TestStatus.ERROR):
                failures.append({
                    "run_id": run.run_id,
                    "path_id": run.path_id,
                    "reason": run.failure_reason or "Unknown",
                    "agents": list(run.agent_assignments.values()),
                    "status": run.status.value,
                })

        total_duration = sum(
            (r.completed_at - r.started_at).total_seconds()
            for r in test_runs
            if r.completed_at and r.started_at
        )

        return TestSummary(
            timestamp=datetime.utcnow().isoformat() + "Z",
            total_tests=len(test_runs),
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration_seconds=total_duration,
            agents_used=sorted(agents),
            paths_tested=sorted(paths),
            failures=failures[:self.config.max_failure_details],
        )

    def write_markdown_report(
        self,
        summary: TestSummary,
        output_path: Optional[Path] = None,
    ) -> Path:
        """Write summary as Markdown report.

        Args:
            summary: Test summary to report
            output_path: Optional custom output path

        Returns:
            Path to the generated report
        """
        if output_path is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_path = self.results_dir / f"report-{timestamp}.md"

        with open(output_path, 'w') as f:
            f.write("# Agentic E2E Test Report\n\n")
            f.write(f"**Generated**: {summary.timestamp}\n\n")

            # Status badge
            if summary.success:
                f.write("**Status**: ✅ All tests passed\n\n")
            else:
                f.write(f"**Status**: ❌ {summary.failed + summary.errors} tests failed\n\n")

            # Summary table
            f.write("## Summary\n\n")
            f.write("| Metric | Value |\n")
            f.write("|--------|-------|\n")
            f.write(f"| Total Tests | {summary.total_tests} |\n")
            f.write(f"| Passed | {summary.passed} |\n")
            f.write(f"| Failed | {summary.failed} |\n")
            f.write(f"| Skipped | {summary.skipped} |\n")
            f.write(f"| Errors | {summary.errors} |\n")
            f.write(f"| Pass Rate | {summary.pass_rate:.1f}% |\n")
            f.write(f"| Duration | {summary.duration_seconds:.1f}s |\n")
            f.write("\n")

            # Agents tested
            if self.config.include_agents and summary.agents_used:
                f.write("## Agents Tested\n\n")
                for agent in summary.agents_used:
                    f.write(f"- {agent}\n")
                f.write("\n")

            # Test paths
            if self.config.include_paths and summary.paths_tested:
                f.write("## Test Paths\n\n")
                for path in summary.paths_tested:
                    f.write(f"- {path}\n")
                f.write("\n")

            # Failures
            if self.config.include_failures and summary.failures:
                f.write("## Failures\n\n")
                for i, failure in enumerate(summary.failures, 1):
                    f.write(f"### {i}. {failure['run_id']}\n\n")
                    f.write(f"- **Path**: {failure['path_id']}\n")
                    f.write(f"- **Status**: {failure['status']}\n")
                    f.write(f"- **Agents**: {', '.join(failure['agents'])}\n")
                    f.write(f"- **Reason**: {failure['reason']}\n\n")

            # Footer
            f.write("---\n")
            f.write("*Generated by spec-kitty agentic E2E test framework*\n")

        return output_path

    def write_json_report(
        self,
        summary: TestSummary,
        output_path: Optional[Path] = None,
    ) -> Path:
        """Write summary as JSON report.

        Args:
            summary: Test summary to report
            output_path: Optional custom output path

        Returns:
            Path to the generated report
        """
        if output_path is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_path = self.results_dir / f"report-{timestamp}.json"

        report_data = {
            "timestamp": summary.timestamp,
            "total_tests": summary.total_tests,
            "passed": summary.passed,
            "failed": summary.failed,
            "skipped": summary.skipped,
            "errors": summary.errors,
            "pass_rate": summary.pass_rate,
            "success": summary.success,
            "duration_seconds": summary.duration_seconds,
            "agents_used": summary.agents_used,
            "paths_tested": summary.paths_tested,
            "failures": summary.failures,
        }

        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2)

        return output_path

    def generate_all_reports(
        self,
        test_runs: List["TestRun"],
    ) -> Dict[str, Path]:
        """Generate all report types from test runs.

        Args:
            test_runs: List of completed TestRun instances

        Returns:
            Dict mapping report type to output path
        """
        summary = self.generate_summary(test_runs)

        return {
            "markdown": self.write_markdown_report(summary),
            "json": self.write_json_report(summary),
        }


def create_report_from_junit_xml(
    junit_path: Path,
    output_dir: Path,
) -> Dict[str, Path]:
    """Create reports from a JUnit XML file.

    Useful for generating reports from existing pytest runs.

    Args:
        junit_path: Path to JUnit XML file
        output_dir: Directory for output reports

    Returns:
        Dict mapping report type to output path
    """
    import xml.etree.ElementTree as ET

    tree = ET.parse(junit_path)
    root = tree.getroot()

    # Parse JUnit XML
    testsuite = root if root.tag == "testsuite" else root.find("testsuite")

    if testsuite is None:
        raise ValueError("No testsuite found in JUnit XML")

    total = int(testsuite.get("tests", 0))
    failures = int(testsuite.get("failures", 0))
    errors = int(testsuite.get("errors", 0))
    skipped = int(testsuite.get("skipped", 0))
    passed = total - failures - errors - skipped
    duration = float(testsuite.get("time", 0))

    # Collect failure details
    failure_details = []
    for testcase in testsuite.findall("testcase"):
        failure = testcase.find("failure")
        error = testcase.find("error")

        if failure is not None or error is not None:
            element = failure if failure is not None else error
            failure_details.append({
                "run_id": testcase.get("name", "unknown"),
                "path_id": testcase.get("classname", "unknown"),
                "reason": element.get("message", "Unknown"),
                "agents": [],
                "status": "failed" if failure is not None else "error",
            })

    summary = TestSummary(
        timestamp=datetime.utcnow().isoformat() + "Z",
        total_tests=total,
        passed=passed,
        failed=failures,
        skipped=skipped,
        errors=errors,
        duration_seconds=duration,
        agents_used=[],
        paths_tested=[],
        failures=failure_details[:10],
    )

    generator = ReportGenerator(output_dir)
    return {
        "markdown": generator.write_markdown_report(summary),
        "json": generator.write_json_report(summary),
    }
