"""Dataset entity.

Represents a loaded data source as a domain object.
The domain layer never imports pandas directly — infrastructure readers
produce a Dataset that the domain can reason about without knowing
how the data was loaded.

Design
------
- Immutable (frozen=True): a Dataset is a snapshot; it is never mutated.
- Metadata-only at the domain level: column names and row count are enough
  for rules to validate. Raw data lives in the infrastructure layer.
- The ``data`` field holds a generic mapping so the domain stays
  decoupled from pandas DataFrame specifics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from dataguard.shared.types import ColumnName, SourcePath


@dataclass(frozen=True)
class Dataset:
    """An immutable snapshot of a loaded data source.

    This entity is produced by an IDataReader implementation and consumed
    by quality rules. The domain works with ``columns`` and ``row_count``
    for structural validation, while the actual row data is accessed
    through the ``data`` mapping.

    Attributes:
        source_path: File-system path from which the data was loaded.
        columns: Ordered list of column names present in the source.
        row_count: Total number of rows in the dataset.
        data: Column-oriented mapping of {column_name: list_of_values}.
            Values are kept as Python native types (str, int, float, None).

    Raises:
        ValueError: If ``row_count`` is negative.
        ValueError: If ``data`` keys don't match ``columns``.
    """

    source_path: SourcePath
    columns: tuple[ColumnName, ...]
    row_count: int
    data: dict[ColumnName, list[object]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate invariants after construction."""
        if self.row_count < 0:
            raise ValueError(
                f"row_count must be non-negative, got {self.row_count}."
            )
        if self.data and set(self.data.keys()) != set(self.columns):
            extra = set(self.data.keys()) - set(self.columns)
            missing = set(self.columns) - set(self.data.keys())
            raise ValueError(
                f"data keys must match columns exactly. "
                f"Extra: {extra}, Missing: {missing}"
            )

    # ── Convenience properties ─────────────────────────────────────────────

    @property
    def source_name(self) -> str:
        """Return only the filename portion of the source path."""
        return Path(self.source_path).name

    @property
    def column_count(self) -> int:
        """Return the number of columns in the dataset."""
        return len(self.columns)

    def has_column(self, column: ColumnName) -> bool:
        """Check whether a named column exists in the dataset.

        Args:
            column: Column name to look up.

        Returns:
            True if the column is present, False otherwise.
        """
        return column in self.columns

    def get_column_values(self, column: ColumnName) -> list[object]:
        """Return all values for a given column.

        Args:
            column: Column name to retrieve values for.

        Returns:
            List of values (may include None for missing entries).

        Raises:
            KeyError: If the column does not exist in the dataset.
        """
        if column not in self.columns:
            raise KeyError(
                f"Column '{column}' not found in dataset '{self.source_name}'. "
                f"Available columns: {list(self.columns)}"
            )
        return self.data.get(column, [])

    def __repr__(self) -> str:
        return (
            f"Dataset(source='{self.source_name}', "
            f"columns={self.column_count}, rows={self.row_count})"
        )
