"""IRuleRepository port — abstract contract for loading quality rules.

Any adapter that loads QualityRule definitions (YAML file, SQLite database,
REST API, …) must implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from dataguard.domain.entities.rule import QualityRule


class IRuleRepository(ABC):
    """Abstract base class for rule definition repositories.

    Infrastructure adapters (FileRuleRepository, SQLiteRuleRepository, …)
    inherit from this class and implement ``load()``.
    """

    @abstractmethod
    def load(self, path: Path) -> list[QualityRule]:
        """Load and return all quality rules from the given source.

        Args:
            path: Path to the rule definition file (e.g. rules.yaml).

        Returns:
            list[QualityRule]: Ordered list of validated rule objects.
                May be empty if the source contains no rules.

        Raises:
            RuleLoadError: If the source cannot be read or parsed.
            InvalidRuleSchemaError: If a rule definition is malformed.
            UnknownRuleTypeError: If a rule specifies an unsupported type.
        """
