import time

TELEMETRY_KEY_GLOB = 'manual_control/*/telemetry'
# Presence = the latched initialization_state key: published at bringup,
# before and independent of any teleop.
PRESENCE_KEY_GLOB = '**/api/localization/initialization_state'
LIVE_TIMEOUT = 3.0  # teleop telemetry is ~60 Hz; drop a scope this long unheard
BRIDGE_LIVE_TIMEOUT = 3600.0  # latched key has no heartbeat; age out slowly


class TeleopTracker:
    """Liveness of vehicles = which teleops are publishing telemetry."""

    def __init__(self, session):
        self._seen = {}
        self._sub = session.declare_subscriber(TELEMETRY_KEY_GLOB, self._on_sample)

    def _on_sample(self, sample):
        parts = str(sample.key_expr).lstrip('/').split('/')
        if len(parts) < 2:
            print(f'[TeleopTracker] ignoring sample with no scope segment: {sample.key_expr}')
            return
        scope = parts[1]
        if scope:
            self._seen[scope] = time.time()

    def list(self):
        now = time.time()
        return [{'scope': s, 'address': f'teleop:{s}'}
                for s, t in list(self._seen.items()) if now - t < LIVE_TIMEOUT]


class BridgeTracker:
    """Presence of vehicles = which bridges have forwarded AD-API to the FMS plane.

    ROS2-mode bridges declare no liveliness token, so a data key is the signal;
    the startup query catches states latched before this session.
    """

    def __init__(self, session):
        self._seen = {}
        self._sub = session.declare_subscriber(PRESENCE_KEY_GLOB, self._on_sample)
        try:
            for reply in session.get(PRESENCE_KEY_GLOB):
                scope = self._note(reply.sample)
                if scope:
                    print(f'[BridgeTracker] discovered via initial query: {scope}')
        except Exception as e:  # presence recovers via the subscriber; logged
            print(f'[BridgeTracker] initial presence query failed: {e}')

    def _note(self, sample):
        key = str(sample.key_expr).lstrip('/')
        idx = key.find('/api/localization/initialization_state')
        if idx <= 0:
            return None
        scope = key[:idx].split('/')[0]
        self._seen[scope] = time.time()
        return scope

    def _on_sample(self, sample):
        self._note(sample)

    def list(self):
        now = time.time()
        return [s for s, t in list(self._seen.items()) if now - t < BRIDGE_LIVE_TIMEOUT]
