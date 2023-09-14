import { useEffect } from "react"
import { useDispatch, useSelector } from "react-redux"
import TitleCard from "../../../components/Cards/TitleCard"
import { getListContent } from "./vehiclelistSlice"

const Refresh = () => {
    // TODO: Add Refresh function
    return(
        <div className="inline-block float-right">
            <button className="btn px-6 btn-sm normal-case btn-primary">Refresh</button>
        </div>
    )
}

function Lists() {
    const {list} = useSelector(state => state.list)
    const dispatch = useDispatch()

    useEffect(() => {
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
                            list.map((l, k) => {

                                return(
                                    <tr key={k}>
                                    <td>
                                        <div className="flex items-center space-x-3">
                                            <div>
                                                <div className="font-bold">{l.name}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td>{l.address}</td>
                                    <td>
                                        idle: {l.status.cpu.all.idle}  <br/>
                                        used: {l.status.cpu.all.total} <br/>
                                        system: {l.status.cpu.all.sys} <br/>
                                        user: {l.status.cpu.all.usr}   <br/>
                                    </td>
                                    <td>
                                        Turn: {l.status.vehicle.status.turn_signal.data}<br/>
                                        Gear: {l.status.vehicle.status.gear_shift.data}<br/>
                                        Steering: {l.status.vehicle.status.steering.data}<br/>
                                        Velocity: {l.status.vehicle.status.twist.linear.x}<br/>
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