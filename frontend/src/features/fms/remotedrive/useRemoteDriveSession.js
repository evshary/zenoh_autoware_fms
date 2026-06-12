import { useEffect, useState } from 'react';

export default function useRemoteDriveSession(teleopScope, activeKeys, pendingActions) {
    const [cameraUrl, setCameraUrl] = useState('');
    const [telemetry, setTelemetry] = useState({});

    useEffect(() => {
        if (teleopScope === 'None') return;

        const camWs = new WebSocket(`ws://${window.location.hostname}:8000/video`);
        camWs.binaryType = 'blob';
        camWs.onmessage = (e) => {
            const url = URL.createObjectURL(e.data);
            setCameraUrl(prev => {
                if (prev?.startsWith('blob:')) URL.revokeObjectURL(prev);
                return url;
            });
        };

        // level throttle/brake/steer + gear; monotonic counters for discrete events (drop/dup-safe).
        const intentWs = new WebSocket(`ws://${window.location.hostname}:8000/teleop/intent/ws`);
        let gear = 'PARK';
        const counters = { mode_cycle: 0, toggle_auto: 0, reset_pose: 0 };
        const sendInterval = setInterval(() => {
            if (intentWs.readyState !== WebSocket.OPEN) return;
            const k = activeKeys.current;
            const a = pendingActions.current;

            if (a.gear) { gear = a.gear; a.gear = null; }
            if (a.mode) { counters.mode_cycle++; a.mode = null; }
            if (a.cmd === 'toggle_auto') { counters.toggle_auto++; a.cmd = null; }
            if (a.cmd === 'reset_pose')  { counters.reset_pose++;  a.cmd = null; }

            const intent = {
                throttle: (k.w && !k.s) ? 1.0 : 0.0,
                brake:    k.s           ? 1.0 : 0.0,
                steer:    (k.a && !k.d) ? 1 : (k.d && !k.a) ? -1 : 0,
                gear,
                mode_cycle:  counters.mode_cycle,
                toggle_auto: counters.toggle_auto,
                reset_pose:  counters.reset_pose,
            };
            intentWs.send(JSON.stringify(intent));
        }, 50);

        const teleWs = new WebSocket(`ws://${window.location.hostname}:8000/telemetry/stream`);
        teleWs.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                if (data && Object.keys(data).length > 0) {
                    setTelemetry(data);
                }
            } catch {}
        };

        return () => {
            clearInterval(sendInterval);
            camWs.close();
            intentWs.close();
            teleWs.close();
        };
    }, [teleopScope]);

    return { cameraUrl, telemetry };
}
