"""Per-provider cooldown; no network or wall-clock dependence."""
from time import monotonic


class PollBackoff:
    def __init__(self, base_seconds=120, cap_seconds=900, clock=monotonic):
        self.base_seconds = base_seconds
        self.cap_seconds = cap_seconds
        self.clock = clock
        self._delays = {}
        self._until = {}

    def ready(self, provider_id):
        return self.remaining(provider_id) <= 0

    def remaining(self, provider_id):
        return max(0, self._until.get(provider_id, 0) - self.clock())

    def observe(self, provider_id, status):
        if status == 'ok':
            self._delays.pop(provider_id, None)
            self._until.pop(provider_id, None)
        elif status == 'rate_limited':
            delay = min(self.cap_seconds, self._delays.get(provider_id, self.base_seconds) * 2)
            self._delays[provider_id] = delay
            self._until[provider_id] = self.clock() + delay
