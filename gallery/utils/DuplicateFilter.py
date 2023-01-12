"""Filters out duplicate records from logging output."""

from logging import Filter, LogRecord


class DuplicateFilter(Filter):
    """Filters out duplicate records from logging output."""

    last = ''

    def filter(self, record: LogRecord) -> bool:
        if record.msg == self.last:
            return False

        self.last = record.msg

        return True
