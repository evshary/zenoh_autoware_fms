import { useEffect } from "react"
import { useDispatch, useSelector } from "react-redux"
import TitleCard from "../../../components/Cards/TitleCard"
import { getListContent } from "./vehiclelistSlice"

export const Refresh = () => {
    const dispatch = useDispatch()
    return(
        <div className="inline-block float-right">
            <button className="btn px-6 btn-sm normal-case btn-primary" onClick={() => {dispatch(getListContent())}}>Refresh</button>
        </div>
    )
}

function Lists() {
    const {list} = useSelector(state => state.list)
    const dispatch = useDispatch()

    useEffect(() => {
        // TODO: We can show loading on webpage
        dispatch(getListContent())
    }, [dispatch])

    return(
        <>
            <TitleCard title="Vehicles" topMargin="mt-2" TopSideButtons={<Refresh />}>
            {/* Vehicle list after api call */}
            <div className="overflow-x-auto w-full">
                <table className="table w-full">
                    <thead>
                    <tr>
                        <th>Name</th>
                        <th>IP address</th>
                        <th>CPU Overview</th>
                        <th>Vehicle Status</th>
                    </tr>
                    </thead>
                    <tbody>
                        {
                            list.map((element, idx) => {
                                var v = JSON.parse(element)
                                return(
                                    <tr key={idx}>
                                    <td>
                                        <div className="flex items-center space-x-3">
                                            <div>
                                                <div className="font-bold">{v.name}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td>{v.address}</td>
                                    <td>
                                        idle: {v.status.cpu.all.idle}  <br/>
                                        used: {v.status.cpu.all.total} <br/>
                                        system: {v.status.cpu.all.sys} <br/>
                                        user: {v.status.cpu.all.usr}   <br/>
                                    </td>
                                    <td>
                                        Turn: {v.status.vehicle.status.turn_signal.data}<br/>
                                        Gear: {v.status.vehicle.status.gear_shift.data}<br/>
                                        Steering: {v.status.vehicle.status.steering.data}<br/>
                                        Velocity: {v.status.vehicle.status.twist.linear.x}<br/>
                                    </td>
                                    </tr>
                                )
                            })
                        }
                    </tbody>
                </table>
            </div>
            </TitleCard>
        </>
    )
}

export default Lists