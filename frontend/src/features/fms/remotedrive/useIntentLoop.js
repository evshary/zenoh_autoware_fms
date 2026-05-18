import { useEffect, useRef, useState } from 'react';

export default function useIntentLoop(teleopScope, activeKeys, pendingActions) {
    const [cameraUrl, setCameraUrl] = useState('');
    const [telemetry, setTelemetry] = useState({});
    const clientIdRef = useRef(crypto.randomUUID());

    useEffect(() => {
        if (teleopScope === 'None') return;

        // (1) Camera WebSocket
        const camWs = new WebSocket(`ws://${window.location.hostname}:8000/video`);
        camWs.binaryType = 'blob';
        camWs.onmessage = (e) => {
            const url = URL.createObjectURL(e.data);
            setCameraUrl(prev => {
                if (prev?.startsWith('blob:')) URL.revokeObjectURL(prev);
                return url;
            });
        };

        // (2) Intent WebSocket — 20Hz sending WASD + one-shot
        const intentWs = new WebSocket(`ws://${window.location.hostname}:8000/teleop/intent/ws`);
        const sendInterval = setInterval(() => {
            if (intentWs.readyState !== WebSocket.OPEN) return;

            const intent = {
                client_id: clientIdRef.current,
                w: activeKeys.current.w,
                a: activeKeys.current.a,
                s: activeKeys.current.s,
                d: activeKeys.current.d,
                space: activeKeys.current.space,
                timestamp: Date.now()
            };

            // Attach pending one-shot actions (only include when non-null)
            const actions = pendingActions.current;
            if (actions.gear) { intent.gear = actions.gear; actions.gear = null; }
            if (actions.mode) { intent.mode = actions.mode; actions.mode = null; }
            if (actions.cmd)  { intent.cmd  = actions.cmd;  actions.cmd  = null; }

            intentWs.send(JSON.stringify(intent));
        }, 50);

        // (3) Telemetry WebSocket
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

    return { cameraUrl, telemetry, clientId: clientIdRef.current };
}
