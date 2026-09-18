"""Finding types, shared by every checker in the toolkit.

Both `catcheck` (catalogue entries) and `check` (data files) emit these, so
there is one output format, one JSON shape and one severity model regardless
of what is being checked. A consumer parsing `--json` does not need to know
which checker produced it.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: Severity
    message: str
    subject: str | None = None
    """What the finding is about: a catalogue entry id, or a column name."""
    field: str | None = None

    def __str__(self) -> str:
        where = self.subject or "-"
        if self.field:
            where = f"{where}.{self.field}"
        return f"{self.severity.value.upper():7} {self.rule}  {where}: {self.message}"

    def as_dict(self) -> dict:
        return {
            "rule": self.rule,
            "severity": self.severity.value,
            "subject": self.subject,
            "field": self.field,
            "message": self.message,
        }

    def escalated(self) -> Finding:
        """The same finding at ERROR severity, for --strict."""
        if self.severity is Severity.ERROR:
            return self
        return Finding(self.rule, Severity.ERROR, self.message, self.subject, self.field)


def summarise(findings: Iterable[Finding]) -> dict[Severity, int]:
    counts = dict.fromkeys(Severity, 0)
    for f in findings:
        counts[f.severity] += 1
    return counts


def sort_key(f: Finding):
    """Errors first, then by rule, then by subject."""
    return (f.severity is not Severity.ERROR, f.rule, f.subject or "")
