"""Pure DataMatrix voting policy, independent from camera/decode libraries."""

from collections import Counter


class DataMatrixReadPolicy:
    """Count at most one vote per code and acquisition attempt.

    Decoder variants frequently return the same symbol more than once.  Raw
    symbols remain available for diagnostics, but confidence is based on
    independent capture attempts rather than duplicate decoder objects.
    """

    VALID_MATCH_MODES = {"exact", "prefix"}

    def __init__(
        self,
        expected_code=None,
        match_mode="exact",
        min_expected_reads=1,
        max_wrong_reads=0,
    ):
        self.expected_code = (
            expected_code.strip() if isinstance(expected_code, str) else None
        )
        self.match_mode = str(match_mode or "exact").strip().lower()
        if self.match_mode not in self.VALID_MATCH_MODES:
            raise ValueError(
                f"Modo de comparacion DataMatrix no soportado: {match_mode}"
            )
        self.min_expected_reads = max(1, int(min_expected_reads))
        self.max_wrong_reads = max(0, int(max_wrong_reads))

        self.attempts = 0
        self.no_read_count = 0
        self.expected_attempt_count = 0
        self.wrong_attempt_count = 0
        self.reads_by_attempt = []
        self.matching_reads = []
        self.wrong_reads = []
        self.votes = Counter()

    @staticmethod
    def _unique_codes(codes):
        unique = []
        seen = set()
        for raw_code in codes or []:
            code = str(raw_code or "").strip()
            if code and code not in seen:
                unique.append(code)
                seen.add(code)
        return unique

    def _matches(self, code):
        if not self.expected_code:
            return False
        if self.match_mode == "prefix":
            return code.startswith(self.expected_code)
        return code == self.expected_code

    def observe(self, codes):
        unique = self._unique_codes(codes)
        self.attempts += 1
        self.reads_by_attempt.append(unique)

        if not unique:
            self.no_read_count += 1
            return

        if self.expected_code:
            matching = [code for code in unique if self._matches(code)]
            wrong = [code for code in unique if not self._matches(code)]
            if matching:
                self.expected_attempt_count += 1
                self.matching_reads.extend(matching)
            if wrong:
                self.wrong_attempt_count += 1
                self.wrong_reads.extend(wrong)
            return

        for code in unique:
            self.votes[code] += 1

    @property
    def confirmed_code(self):
        if self.expected_code:
            if (
                self.expected_attempt_count >= self.min_expected_reads
                and self.wrong_attempt_count <= self.max_wrong_reads
            ):
                return self.expected_code
            return None

        if not self.votes:
            return None
        ranked = self.votes.most_common()
        best_code, best_count = ranked[0]
        if best_count < self.min_expected_reads:
            return None
        if len(ranked) > 1 and ranked[1][1] == best_count:
            return None
        return best_code

    @property
    def wrong_limit_exceeded(self):
        return self.wrong_attempt_count > self.max_wrong_reads

    def summary(self):
        return {
            "expected_code": self.expected_code,
            "match_mode": self.match_mode,
            "attempts": self.attempts,
            "reads_by_attempt": list(self.reads_by_attempt),
            "expected_attempt_count": self.expected_attempt_count,
            "wrong_attempt_count": self.wrong_attempt_count,
            "wrong_reads": list(self.wrong_reads),
            "no_read_count": self.no_read_count,
            "min_expected_reads": self.min_expected_reads,
            "max_wrong_reads": self.max_wrong_reads,
            "votes": dict(self.votes),
        }
