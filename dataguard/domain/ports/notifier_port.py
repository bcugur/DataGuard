"""INotifier port — abstract contract for sending validation notifications.

Any adapter that notifies users about a validation result (console output,
email, Slack, webhook, …) must implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from dataguard.domain.entities.report import ValidationReport


class INotifier(ABC):
    """Abstract base class for result notifiers.

    Infrastructure adapters (ConsoleNotifier, EmailNotifier, …) inherit
    from this class and implement ``notify()``.
    """

    @abstractmethod
    def notify(self, report: ValidationReport) -> None:
        """Send a notification summarising the validation report.

        Args:
            report: The fully populated ValidationReport to summarise.

        Note:
            Implementations should not raise exceptions for notification
            failures that are non-critical (e.g. email delivery issues).
            Log the error and return gracefully instead.
        """
