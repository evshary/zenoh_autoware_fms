import { useEffect, useRef, useState, useCallback } from 'react';

const MODES = ['PHYSICS', 'CRUISE', 'STOP'];

export default function useKeyboardControl(telemetryRef) {
    const activeKeys = useRef({ w: false, a: false, s: false, d: false, space: false });
    const pendingActions = useRef({ gear: null, mode: null, cmd: null });
    const [pressedKeys, setPressedKeys] = useState([]);
    const [rotation, setRotation] = useState(0);
    const [flashedKey, setFlashedKey] = useState(null);

    const syncPressedKeys = useCallback(() => {
        setPressedKeys(Object.entries(activeKeys.current).filter(([, v]) => v).map(([k]) => k));
    }, []);

    // Map a one-shot key (x/c/v/m/z) to pendingActions; shared by physical
    // keydown and on-screen badges. Returns true if key matched.
    const applyOneShot = useCallback((key) => {
        if (key === 'x') { pendingActions.current.gear = 'DRIVE'; return true; }
        if (key === 'c') { pendingActions.current.gear = 'REVERSE'; return true; }
        if (key === 'v') { pendingActions.current.gear = 'PARK'; return true; }
        if (key === 'z') { pendingActions.current.cmd = 'toggle_auto'; return true; }
        if (key === 'm') {
            const current = telemetryRef.current?.mode || 'PHYSICS';
            const idx = MODES.indexOf(current);
            pendingActions.current.mode = MODES[((idx === -1 ? 0 : idx) + 1) % MODES.length];
            return true;
        }
        return false;
    }, [telemetryRef]);

    useEffect(() => {
        const handleKeyDown = (e) => {
            if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target?.tagName)) return;
            if (e.repeat) return;
            const k = e.key.toLowerCase();

            if (k === 'w') activeKeys.current.w = true;
            if (k === 'a') { activeKeys.current.a = true; setRotation(-45); }
            if (k === 's') activeKeys.current.s = true;
            if (k === 'd') { activeKeys.current.d = true; setRotation(45); }
            if (k === ' ') { activeKeys.current.space = true; e.preventDefault(); }

            applyOneShot(k);

            syncPressedKeys();
        };

        const handleKeyUp = (e) => {
            const k = e.key.toLowerCase();
            if (k === 'w') activeKeys.current.w = false;
            if (k === 'a') { activeKeys.current.a = false; if (!activeKeys.current.d) setRotation(0); }
            if (k === 's') activeKeys.current.s = false;
            if (k === 'd') { activeKeys.current.d = false; if (!activeKeys.current.a) setRotation(0); }
            if (k === ' ') activeKeys.current.space = false;
            syncPressedKeys();
        };

        const handleBlur = () => {
            activeKeys.current = { w: false, a: false, s: false, d: false, space: false };
            syncPressedKeys();
            setRotation(0);
        };

        window.addEventListener('keydown', handleKeyDown);
        window.addEventListener('keyup', handleKeyUp);
        window.addEventListener('blur', handleBlur);
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
            window.removeEventListener('keyup', handleKeyUp);
            window.removeEventListener('blur', handleBlur);
        };
    }, [syncPressedKeys, applyOneShot]);

    const pressKey = useCallback((key) => {
        activeKeys.current[key] = true;
        syncPressedKeys();
    }, [syncPressedKeys]);

    const releaseKey = useCallback((key) => {
        activeKeys.current[key] = false;
        syncPressedKeys();
    }, [syncPressedKeys]);

    const triggerOneShot = useCallback((key) => {
        if (!applyOneShot(key)) return;
        setFlashedKey(key);
        setTimeout(() => setFlashedKey(v => (v === key ? null : v)), 250);
    }, [applyOneShot]);

    return {
        activeKeys,
        pendingActions,
        pressedKeys,
        flashedKey,
        rotation,
        setRotation,
        pressKey,
        releaseKey,
        triggerOneShot,
    };
}
