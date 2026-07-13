import asyncio
import os
import re
import signal
import subprocess
import threading
import time

import yaml

# ROS-free native teleop; takes --config <yaml> (see just build-teleop)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TELEOP_BINARY = os.environ.get(
    'FLEET_TELEOP_BINARY',
    os.path.join(
        PROJECT_ROOT,
        'tmp/teleop-native-ws/install/lib/autoware_manual_control/zenoh_control',
    ),
)


def _zenoh_vendor_lib():
    backend_root = os.environ.get('BACKEND_ROOT', os.path.join(PROJECT_ROOT, '../autoware_carla_launch'))
    return os.path.join(backend_root, 'rmw_zenoh_ws/install/zenoh_cpp_vendor/opt/zenoh_cpp_vendor/lib')


ZENOH_VENDOR_LIB = _zenoh_vendor_lib()
# Set by `just up --ros`: the single-vehicle path drives via an in-container
# rclcpp teleop, so the fleet must not spawn a second (native) one.
ROS_SINGLE = os.environ.get('FMS_ROS_SINGLE') == '1'

TELEOP_OPERATOR_MODE = os.environ.get('FLEET_TELEOP_OPERATOR_MODE', 'remote')
TELEOP_ARRIVAL_TIMEOUT_MS = os.environ.get('FLEET_TELEOP_ARRIVAL_TIMEOUT_MS', '500.0')

# same params file up --ros feeds rclcpp; fleet overrides only the operator scalars
TELEOP_CONFIG_TEMPLATE = os.environ.get(
    'FLEET_TELEOP_CONFIG_TEMPLATE',
    os.path.join(PROJECT_ROOT, 'fms_teleop_config.yaml'),
)

# each teleop connects explicitly to its three producers: FMS plane, this
# vehicle's ros2dds bridge, and the sim bridge (vehicle/status/* source;
# without it gear confirmation never arrives = shift blocks forever)
FMS_OPERATOR_ENDPOINT = os.environ.get('FLEET_FMS_ENDPOINT', 'tcp/localhost:7887')
SIM_BRIDGE_ENDPOINT = os.environ.get('FLEET_SIM_BRIDGE_ENDPOINT', 'tcp/localhost:7447')
# Each vehicle's ros2dds bridge listens on BRIDGE_PORT_BASE + its ROS domain
# (rendered into its bridge json5 by the backend); the backend records
# scope=domain in tmp/vehicle_domains.env, and _bridge_endpoint reads it back.
BRIDGE_HOST = os.environ.get('FLEET_BRIDGE_HOST', 'localhost')
BRIDGE_PORT_BASE = int(os.environ.get('FLEET_BRIDGE_PORT_BASE', '7448'))

# Repo-owned, not /tmp: a predictable world-writable path could be
# pre-placed by another user and injected into a vehicle commander's config.
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'tmp')
SUPERVISE_INTERVAL = 1.0  # s
TERM_GRACE = 5.0          # s

# give up so a binary that dies on every spawn cannot storm-fork forever
BACKOFF_BASE = 1.0        # s
BACKOFF_CAP = 30.0        # s
RESTART_LIMIT = 5         # consecutive crashes before giving up until re-attach

# A scope is a zenoh key segment, a tmp/ filename component and a YAML value, so
# it must be a tame token: reject path traversal, keyexpr wildcards and YAML/shell
# injection up front at every operator entry point (same token rule as the just CLI).
_SCOPE_RE = re.compile(r'^[A-Za-z][A-Za-z0-9_]*$')


class InvalidScope(ValueError):
    pass


def validate_scope(scope):
    if not isinstance(scope, str) or not _SCOPE_RE.match(scope):
        raise InvalidScope(f'invalid scope (allowed: [A-Za-z][A-Za-z0-9_]*): {scope!r}')
    return scope


def _zenoh_config_path(scope):
    return os.path.join(CONFIG_DIR, f'fleet_teleop_{scope}_zenoh.json5')


def _teleop_config_path(scope):
    return os.path.join(CONFIG_DIR, f'fleet_teleop_{scope}.yaml')


def _bridge_endpoint(scope):
    override = os.environ.get(f'FLEET_BRIDGE_ENDPOINT_{scope}')
    if override:
        return override
    domain = None
    env_path = os.path.join(PROJECT_ROOT, 'tmp/vehicle_domains.env')
    try:
        with open(env_path) as f:
            for line in f:
                if line.startswith(f'{scope}='):
                    domain = int(line.split('=')[1].strip())
                    break
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as e:
        print(f'[FleetManager] {scope}: unreadable {env_path}: {e}')
    if domain is None:
        # Offline fallback (no domains file): guess domain = trailing digit,
        # right only if vehicles came up in name order.
        m = re.search(r'(\d+)$', scope)
        domain = int(m.group(1)) if m else 1
    return f'tcp/{BRIDGE_HOST}:{BRIDGE_PORT_BASE + domain}'


def _write_zenoh_config(scope):
    validate_scope(scope)
    path = _zenoh_config_path(scope)
    bridge_ep = _bridge_endpoint(scope)
    config = (
        '{\n'
        '  mode: "peer",\n'
        '  connect: { endpoints: [\n'
        f'    "{FMS_OPERATOR_ENDPOINT}",\n'
        f'    "{SIM_BRIDGE_ENDPOINT}",\n'
        f'    "{bridge_ep}"\n'
        '  ] },\n'
        '}\n'
    )
    with open(path, 'w') as f:
        f.write(config)
    return path


def _write_teleop_config(scope):
    # Template fields pass through; only per-scope operator fields are
    # overridden (missing presets fall back to the binary's code defaults).
    validate_scope(scope)
    os.makedirs(CONFIG_DIR, exist_ok=True)
    zenoh_cfg = _write_zenoh_config(scope)
    path = _teleop_config_path(scope)
    with open(TELEOP_CONFIG_TEMPLATE) as f:
        params = yaml.safe_load(f) or {}
    # Unwrap a ROS 2 params file: `<node>: {ros__parameters: {...}}`.
    if len(params) == 1:
        (inner,) = params.values()
        if isinstance(inner, dict) and 'ros__parameters' in inner:
            params = inner['ros__parameters']
    params.update({
        'operator_mode': TELEOP_OPERATOR_MODE,
        'scope': scope,
        'arrival_timeout_ms': float(TELEOP_ARRIVAL_TIMEOUT_MS),
        'zenoh_config': zenoh_cfg,
    })
    with open(path, 'w') as f:
        yaml.safe_dump(params, f, default_flow_style=False, sort_keys=False)
    return path


class TeleopProcess:
    """One operator-side native teleop subprocess for a single scope."""

    def __init__(self, scope):
        self.scope = validate_scope(scope)
        self.intent = 'detached'  # attached | detached
        self.proc = None
        self.last_error = None
        self.restarts = 0          # consecutive crash-restarts since last clean attach
        self.next_spawn_at = 0.0   # monotonic deadline before the next restart is allowed

    def _fail(self, msg):
        self.last_error = msg
        print(f'[FleetManager] {self.scope}: {msg}')

    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def _reap(self):
        # else the crashed child stays a zombie until GC
        if self.proc is not None and self.proc.poll() is not None:
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                print(f'[FleetManager] {self.scope}: reap timed out; leaving to GC')
            self.proc = None

    def spawn(self):
        if self.alive():
            return  # idempotent: one process per scope
        self._reap()
        binary = TELEOP_BINARY
        if not (os.path.isfile(binary) and os.access(binary, os.X_OK)):
            self._fail(f'teleop binary not runnable: {binary} (run `just build-teleop`)')
            return
        try:
            config = _write_teleop_config(self.scope)
        except (OSError, InvalidScope, ValueError) as e:
            self._fail(f'cannot write teleop config: {e}')
            return
        # Clean, ROS-free env: no ROS/AMENT/RMW vars so the binary cannot join a
        # sourced ROS graph; libzenohc comes from the vendored LD_LIBRARY_PATH.
        env = {
            'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
            'LD_LIBRARY_PATH': f"{ZENOH_VENDOR_LIB}:{os.environ.get('LD_LIBRARY_PATH', '')}".rstrip(':')
        }
        log_path = os.path.join(CONFIG_DIR, f'fleet_teleop_{self.scope}.log')
        try:
            log = open(log_path, 'ab')
        except OSError as e:
            self._fail(f'cannot open log {log_path}: {e}')
            return
        # A stale commander from a previous api run would double-drive the scope.
        # Anchored on the exact config path so v1 never matches v10's.
        subprocess.run(
            ['pkill', '-9', '-f', f'zenoh_control --config {re.escape(config)}$'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        try:
            # start_new_session: own process group so a terminate/kill reaches the
            # binary even if it ever re-execs; stdin closed (no keyboard input).
            self.proc = subprocess.Popen(
                [binary, '--config', config],
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                start_new_session=True,
                close_fds=True,
            )
            self.last_error = None
            print(f'[FleetManager] {self.scope}: spawned native teleop '
                  f'pid={self.proc.pid} config={config} (log {log_path})')
        except OSError as e:
            self._fail(f'spawn failed: {e}')
        finally:
            log.close()

    def note_clean_attach(self):
        self.restarts = 0
        self.next_spawn_at = 0.0

    def restart_after_crash(self, now):
        if self.restarts >= RESTART_LIMIT:
            if self.last_error is None or 'giving up' not in self.last_error:
                self._fail(f'giving up after {RESTART_LIMIT} restarts; re-attach to retry')
            return
        if now < self.next_spawn_at:
            return
        delay = min(BACKOFF_CAP, BACKOFF_BASE * (2 ** self.restarts))
        self.restarts += 1
        self.next_spawn_at = now + delay
        print(f'[FleetManager] {self.scope}: teleop died while present + attached '
              f'-> restart {self.restarts}/{RESTART_LIMIT} (next backoff {delay:.0f}s)')
        self.spawn()

    def stop(self):
        proc = self.proc
        if proc is None or not self.alive():
            self._reap()
            return
        pid = proc.pid
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError) as e:
            print(f'[FleetManager] {self.scope}: SIGTERM failed ({e}); killing')
        deadline = time.monotonic() + TERM_GRACE
        while self.alive() and time.monotonic() < deadline:
            time.sleep(0.1)
        if self.alive():
            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError) as e:
                print(f'[FleetManager] {self.scope}: SIGKILL failed ({e})')
        try:
            proc.wait(timeout=2)
            print(f'[FleetManager] {self.scope}: stopped teleop pid={pid}')
        except subprocess.TimeoutExpired:
            print(f'[FleetManager] {self.scope}: teleop pid={pid} did not die after SIGKILL')
        self.proc = None


class FleetManager:
    """Owns one TeleopProcess per scope and a supervision loop that reconciles
    intent vs liveness against bridge-plane presence.

    attach(scope):  intent=attached, spawn if not running (idempotent).
    detach(scope):  intent=detached, stop; never restart.
    supervise():    attached + crashed + still present -> restart with backoff;
                    detached -> ensure stopped. Presence loss alone never stops
                    a held process (manual teardown only).
    """

    def __init__(self, bridge_tracker):
        self._bridge = bridge_tracker
        self._procs = {}
        self._task = None
        # attach/detach run on request threads, supervision on its own: an
        # unserialized spawn() pair would leave an untracked second commander.
        self._lock = threading.Lock()

    def _get(self, scope):
        validate_scope(scope)
        if scope not in self._procs:
            self._procs[scope] = TeleopProcess(scope)
        return self._procs[scope]

    def attach(self, scope):
        # `up --ros` runs one in-container rclcpp teleop that owns control; a
        # fleet spawn here would double-command the vehicle on the same intent.
        if ROS_SINGLE:
            validate_scope(scope)
            print(f'[FleetManager] {scope}: attach skipped (ros-single mode)')
            return {'scope': scope, 'intent': 'skipped', 'running': False, 'error': None}
        with self._lock:
            tp = self._get(scope)
            tp.intent = 'attached'
            tp.note_clean_attach()
            tp.spawn()
            return self.status(scope)

    def detach(self, scope):
        with self._lock:
            tp = self._get(scope)
            tp.intent = 'detached'
            tp.stop()
            return self.status(scope)

    def held_scopes(self):
        return [s for s, tp in self._procs.items() if tp.intent == 'attached']

    def status(self, scope):
        tp = self._procs.get(scope)
        if tp is None:
            return {'scope': scope, 'intent': 'detached', 'running': False, 'error': None}
        return {'scope': scope, 'intent': tp.intent, 'running': tp.alive(),
                'error': tp.last_error}

    def supervise_once(self):
        now = time.monotonic()
        present = set(self._bridge.list())
        with self._lock:
            for scope, tp in list(self._procs.items()):
                if tp.intent == 'attached':
                    # Crash auto-restart, but only while the vehicle is still present:
                    # a dead process for a present vehicle is a crash; for an absent
                    # one it is a zombie the operator must detach manually.
                    if not tp.alive() and scope in present:
                        tp.restart_after_crash(now)
                elif tp.alive():
                    tp.stop()

    async def _run(self):
        while True:
            try:
                # Off the loop: stop() blocks up to TERM_GRACE.
                await asyncio.to_thread(self.supervise_once)
            except Exception as e:  # loop must survive a single bad cycle; logged
                print(f'[FleetManager] supervision cycle error: {e!r}')
            await asyncio.sleep(SUPERVISE_INTERVAL)

    def start(self):
        if self._task is None:
            self._task = asyncio.ensure_future(self._run())

    def shutdown(self):
        if self._task is not None:
            self._task.cancel()
            self._task = None
        with self._lock:
            for tp in self._procs.values():
                tp.stop()
