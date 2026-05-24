import { useRef, useEffect, forwardRef } from "react"
import { useDispatch, useSelector } from "react-redux"
import { startupTeleop, updateLatency, updateControlStatus } from "./remoteDriveSlice"
import { Refresh } from "../vehiclelist"
import { getListContent } from "../vehiclelist/vehiclelistSlice"
import { CamImageWithStatus } from "./cameraImg"
import SteeringWheel from "./steering"
import useDriveInput from "./useDriveInput"
import useRemoteDriveSession from "./useRemoteDriveSession"

const VehicleSelect = forwardRef((props, ref) => (
    <select ref={ref} className="bg-gray-50 border border-gray-300 text-gray-900 text-lg rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-1/2 p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white">
        <option value="None">None</option>
        {props.state.map((el) => { const V = JSON.parse(el); return <option key={V.name} value={V.name}>{V.name}</option>; })}
    </select>
));

const VehicleSelectButton = ({ isLoading, refon, text }) => {
    const dispatch = useDispatch();
    if (isLoading) return <button className="btn px-6 btn-sm normal-case btn-primary"><span className="loading loading-spinner loading-sm" /></button>;
    return <button className="btn px-6 btn-sm normal-case btn-info text-info-content"
        onClick={() => dispatch(startupTeleop(refon.current?.value || "None"))}>{text}</button>;
};

function TeleopPanel() {
    const scopeRef = useRef(null);
    const dispatch = useDispatch();
    const { list } = useSelector(s => s.list);
    const refreshLoading = useSelector(s => s.list.isLoading);
    const teleopScope = useSelector(s => s.teleop.teleopScope);
    const teleopLoading = useSelector(s => s.teleop.isLoading);
    const latency = useSelector(s => s.teleop.latency);
    const isControlling = useSelector(s => s.teleop.isControlling);

    useEffect(() => {
        if (list.length === 0) dispatch(getListContent());
    }, []);  // eslint-disable-line react-hooks/exhaustive-deps

    const {
        activeKeys, pendingActions,
        pressedKeys, flashedKey, rotation, setRotation,
        pressKey, releaseKey, triggerOneShot,
    } = useDriveInput();

    const { cameraUrl, telemetry, clientId } = useRemoteDriveSession(
        teleopScope, activeKeys, pendingActions
    );

    useEffect(() => {
        if (telemetry.timestamp) {
            dispatch(updateLatency(Date.now() - telemetry.timestamp));
        }
        if (telemetry.active_client_id !== undefined) {
            dispatch(updateControlStatus(telemetry.active_client_id === clientId));
        }
    }, [telemetry, clientId, dispatch]);

    const KeyBadge = ({ keyName, label, width = "w-10", onClick, onPressStart, onPressEnd }) => {
        const isPressed = pressedKeys.includes(keyName) || flashedKey === keyName;
        const interactive = Boolean(onClick || onPressStart);
        const pressHandlers = onPressStart
            ? {
                onMouseDown: (e) => { e.preventDefault(); onPressStart(); },
                onMouseUp: () => onPressEnd && onPressEnd(),
                onMouseLeave: () => onPressEnd && onPressEnd(),
                onTouchStart: (e) => { e.preventDefault(); onPressStart(); },
                onTouchEnd: (e) => { e.preventDefault(); onPressEnd && onPressEnd(); },
            }
            : onClick
                ? { onClick: (e) => { e.preventDefault(); onClick(); } }
                : {};
        return (
            <div className="flex flex-col items-center mx-1 my-1">
                <kbd
                    {...pressHandlers}
                    className={`kbd ${width} transition-all duration-150 ease-out
                        ${interactive ? 'cursor-pointer select-none hover:bg-base-300 active:scale-90' : ''}
                        ${isPressed
                            ? 'bg-primary text-primary-content border-primary scale-90 shadow-lg ring-2 ring-primary/40'
                            : ''}`}
                >
                    {label || keyName.toUpperCase()}
                </kbd>
            </div>
        );
    };

    return (
        <div className="w-full h-[calc(100vh-100px)] grid grid-cols-12 gap-4 bg-base-100 overflow-hidden">
            {/* Camera Panel */}
            <div className="col-span-8 lg:col-span-9 h-full relative rounded-2xl overflow-hidden shadow-2xl border border-base-300">
                <CamImageWithStatus
                    classname="w-full h-full bg-no-repeat bg-cover absolute inset-0"
                    bgUrl={cameraUrl}
                    telemetry={telemetry}
                    latency={latency}
                    isControlling={isControlling}
                />
                <div className="absolute top-4 right-4 z-10 flex items-center space-x-3 bg-base-100/80 backdrop-blur-md p-2 rounded-xl shadow-lg">
                    {teleopScope !== "None" ?
                        <span className="badge badge-primary font-bold">Driving: {teleopScope}</span> :
                        <span className="badge badge-ghost font-bold">No Vehicle Selected</span>}
                    <Refresh isLoading={refreshLoading} />
                </div>
            </div>

            <div className="col-span-4 lg:col-span-3 h-full grid grid-rows-[3fr_7fr_10fr] gap-4 overflow-hidden pr-2 pb-2">
                <div className="bg-gradient-to-br from-base-200 to-base-300 backdrop-blur-sm p-4 rounded-2xl shadow-lg border border-base-300/50 grid grid-rows-[auto_1fr] gap-2 h-full overflow-hidden">
                    <h3 className="font-extrabold uppercase tracking-wider text-base-content/70">Vehicle Selection</h3>
                    <div className="grid grid-cols-[1fr_auto] gap-2 items-center">
                        <VehicleSelect state={list} ref={scopeRef} />
                        <VehicleSelectButton text="Teleop" refon={scopeRef} isLoading={teleopLoading} />
                    </div>
                </div>

                <div className="bg-gradient-to-br from-base-200 to-base-300 backdrop-blur-sm px-4 py-2 rounded-2xl shadow-lg border border-base-300/50 grid grid-rows-[auto_1fr] gap-2 h-full overflow-hidden">
                    <div className="grid grid-cols-[auto_1fr] gap-4 items-center justify-items-center">
                        <div className="grid grid-rows-2 grid-cols-3 justify-items-center scale-95">
                            <div className="col-start-2"><KeyBadge keyName="w" /></div>
                            <div className="col-start-1"><KeyBadge keyName="a" /></div>
                            <div className="col-start-2"><KeyBadge keyName="s" /></div>
                            <div className="col-start-3"><KeyBadge keyName="d" /></div>
                        </div>
                        <div className="grid grid-rows-2 items-center">
                            <h3 className="font-extrabold uppercase tracking-wider text-base-content/70">Key</h3>
                            <h3 className="font-extrabold uppercase tracking-wider text-base-content/70">Controls</h3>
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-x-2 gap-y-1 w-full text-xs font-medium text-base-content/80 content-center">
                        <div className="grid grid-cols-[auto_1fr] gap-2 items-center min-w-0">
                            <KeyBadge keyName="z" width="w-7" onClick={() => triggerOneShot('z')} />
                            <span className="truncate">Engage</span>
                        </div>
                        <div className="grid grid-cols-[auto_1fr] gap-2 items-center min-w-0">
                            <KeyBadge keyName="x" width="w-7" onClick={() => triggerOneShot('x')} />
                            <span className="truncate">Drive</span>
                        </div>
                        <div className="grid grid-cols-[auto_1fr] gap-2 items-center min-w-0">
                            <KeyBadge keyName="c" width="w-7" onClick={() => triggerOneShot('c')} />
                            <span className="truncate">Reverse</span>
                        </div>
                        <div className="grid grid-cols-[auto_1fr] gap-2 items-center min-w-0">
                            <KeyBadge keyName="v" width="w-7" onClick={() => triggerOneShot('v')} />
                            <span className="truncate">Park</span>
                        </div>
                        <div className="grid grid-cols-[auto_1fr] gap-2 items-center min-w-0">
                            <KeyBadge keyName="m" width="w-7" onClick={() => triggerOneShot('m')} />
                            <span className="truncate">Cycle Mode</span>
                        </div>
                        <div className="grid grid-cols-[auto_1fr] gap-2 items-center min-w-0">
                            <KeyBadge keyName="r" width="w-7" onClick={() => triggerOneShot('r')} />
                            <span className="truncate">Reset Pose</span>
                        </div>
                    </div>
                </div>

                <div className="bg-gradient-to-br from-base-200 to-base-300 px-10 py-4 rounded-3xl shadow-xl border border-base-300/50 grid grid-cols-2 grid-rows-2 gap-4 h-full overflow-hidden">
                    <div className="flex items-center justify-center">
                        <SteeringWheel rotation={rotation} onRotationChange={setRotation} />
                    </div>
                    <div className="flex flex-col items-start justify-center px-1 min-w-0">
                        <h3 className="font-extrabold uppercase tracking-wider text-base-content/70">Cockpit</h3>
                        <p className="text-sm leading-snug text-base-content/60 mt-1">
                            Drag the wheel to steer.<br />
                            Hold the pedals for gas / brake.
                        </p>
                    </div>
                    <button
                        className={`w-full h-full rounded-3xl transition-all duration-200 select-none border backdrop-blur-md flex items-center justify-center ${pressedKeys.includes('s') ? 'bg-red-500/20 border-red-500/50 scale-95' : 'bg-base-100/40 border-base-content/10 shadow-xl'}`}
                        onMouseDown={() => pressKey('s')}
                        onMouseUp={() => releaseKey('s')}
                        onMouseLeave={() => { if (pressedKeys.includes('s')) releaseKey('s'); }}
                        onTouchStart={(e) => { e.preventDefault(); pressKey('s'); }}
                        onTouchEnd={(e) => { e.preventDefault(); releaseKey('s'); }}
                    >
                        <span className={`font-medium tracking-widest text-xs uppercase ${pressedKeys.includes('s') ? 'text-red-500' : 'text-base-content/60'}`}>Brake</span>
                    </button>
                    <button
                        className={`w-full h-full rounded-3xl transition-all duration-200 select-none border backdrop-blur-md flex items-center justify-center ${pressedKeys.includes('w') ? 'bg-emerald-500/20 border-emerald-500/50 scale-95' : 'bg-base-100/40 border-base-content/10 shadow-xl'}`}
                        onMouseDown={() => pressKey('w')}
                        onMouseUp={() => releaseKey('w')}
                        onMouseLeave={() => { if (pressedKeys.includes('w')) releaseKey('w'); }}
                        onTouchStart={(e) => { e.preventDefault(); pressKey('w'); }}
                        onTouchEnd={(e) => { e.preventDefault(); releaseKey('w'); }}
                    >
                        <span className={`font-medium tracking-widest text-xs uppercase ${pressedKeys.includes('w') ? 'text-emerald-500' : 'text-base-content/60'}`}>Gas</span>
                    </button>
                </div>
            </div>
        </div>
    );
}

export default TeleopPanel
