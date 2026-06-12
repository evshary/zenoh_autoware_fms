export const CamImageWithStatus = (props) => {
    const telemetry = props.telemetry || {};

    const velocity = Math.abs((telemetry.velocity || 0) * 3.6).toFixed(1);
    const steerAngle = ((telemetry.steer_angle || 0) * 180 / Math.PI).toFixed(0);
    const targetVelocity = ((telemetry.target_velocity || 0) * 3.6).toFixed(1);
    const targetSteer = ((telemetry.target_steer || 0) * 180 / Math.PI).toFixed(0);

    const pendingGear = telemetry.pending_gear || '';
    const currentGear = telemetry.gear || '';
    const gearDisplay = pendingGear
        ? pendingGear.charAt(0).toUpperCase() + pendingGear.slice(1).toLowerCase()
        : currentGear
            ? currentGear.charAt(0).toUpperCase() + currentGear.slice(1).toLowerCase()
            : '---';

    const isShifting = telemetry.shift_state && telemetry.shift_state !== 'IDLE';

    return (
        <div className={props.classname}>
            <img src={props.bgUrl} className="absolute inset-0 w-full h-full object-cover z-0" alt="" />
            <div className="relative w-[40%] max-w-sm p-6 z-10 text-base-content">
                <div className="bg-base-100/70 backdrop-blur-md rounded-3xl shadow-2xl border border-white/20 p-5">
                    <h3 className="font-extrabold text-sm uppercase tracking-wider mb-4 flex items-center text-base-content/80">
                        <svg className="w-4 h-4 mr-2 opacity-70" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                        Vehicle Telemetry
                    </h3>
                    <table className="w-full text-base text-left font-bold table-fixed">
                        <tbody>
                            <tr className="border-b border-base-content/10">
                                <th className="py-2.5 font-medium whitespace-nowrap text-base-content/70">Latency</th>
                                <td className="text-right font-mono text-lg tracking-tight whitespace-nowrap">
                                    <span className={(props.latency > 250) ? 'text-error animate-pulse' : ((props.latency > 100) ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400')}>
                                        {props.latency || '0'}
                                    </span>
                                </td>
                                <td className="pl-2 w-12 text-[10px] font-medium text-base-content/50 uppercase text-right">ms</td>
                            </tr>
                            <tr className="border-b border-base-content/10">
                                <th className="py-2.5 font-medium whitespace-nowrap text-base-content/70">Velocity</th>
                                <td className="text-right font-mono text-xl tracking-tight whitespace-nowrap">
                                    <span className="tooltip tooltip-top" data-tip="Actual velocity from Carla">
                                        <span className="text-emerald-600 dark:text-emerald-400">{velocity}</span>
                                    </span>
                                    <span className="mx-1 text-base-content/30 text-sm">/</span>
                                    <span className="tooltip tooltip-top" data-tip="Target velocity from Teleop">
                                        <span className="text-base-content/60 text-lg">{targetVelocity}</span>
                                    </span>
                                </td>
                                <td className="pl-2 w-12 text-[10px] font-medium text-base-content/50 uppercase text-right">km/h</td>
                            </tr>
                            <tr className="border-b border-base-content/10">
                                <th className="py-2.5 font-medium whitespace-nowrap text-base-content/70">Steering</th>
                                <td className="text-right font-mono text-xl tracking-tight whitespace-nowrap">
                                    <span className="tooltip tooltip-top" data-tip="Actual steering from Carla">
                                        <span className="text-indigo-500 dark:text-indigo-400">{steerAngle}</span>
                                    </span>
                                    <span className="mx-1 text-base-content/30 text-sm">/</span>
                                    <span className="tooltip tooltip-top" data-tip="Target steering from teleop">
                                        <span className="text-base-content/60 text-lg">{targetSteer}</span>
                                    </span>
                                </td>
                                <td className="pl-2 w-12 text-[10px] font-medium text-base-content/50 uppercase text-right">deg</td>
                            </tr>
                            <tr className="border-b border-base-content/10">
                                <th className="py-2.5 font-medium whitespace-nowrap text-base-content/70">Gear / Mode</th>
                                <td colSpan="2" className="text-right">
                                    <span className="tooltip tooltip-top" data-tip="Current gear (pending target flashes yellow while shifting)">
                                        <span className={`font-mono text-lg font-bold tracking-tight ${isShifting ? 'text-warning animate-pulse' : 'text-blue-500 dark:text-blue-400'}`}>
                                            {gearDisplay}
                                        </span>
                                    </span>
                                    <span className="mx-2 text-base-content/20 font-light">|</span>
                                    <span className="tooltip tooltip-top" data-tip="Teleop drive mode (cycle with M)">
                                        <span className="font-mono text-lg font-bold tracking-tight text-amber-500 dark:text-amber-400">
                                            {telemetry.mode || '---'}
                                        </span>
                                    </span>
                                </td>
                            </tr>
                            <tr className="border-b border-base-content/10">
                                <th className="py-2.5 font-medium whitespace-nowrap text-base-content/70">Operation</th>
                                <td colSpan="2" className="text-right">
                                    <span className="tooltip tooltip-top" data-tip="Autoware operation mode (REMOTE = engaged)">
                                        <span className={`font-mono text-lg font-bold tracking-tight ${telemetry.operation_mode === 'REMOTE' ? 'text-emerald-500 dark:text-emerald-400' : 'text-base-content/60'}`}>
                                            {telemetry.operation_mode || '---'}
                                        </span>
                                    </span>
                                    <span className="mx-2 text-base-content/20 font-light">|</span>
                                    <span className="tooltip tooltip-top" data-tip="Whether you hold control (Preempted = another operator took over)">
                                        <span className={`font-mono text-lg font-bold tracking-tight ${props.isControlling ? 'text-emerald-500 dark:text-emerald-400' : 'text-error'}`}>
                                            {props.isControlling ? 'Active' : 'Preempted'}
                                        </span>
                                    </span>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    )
}
