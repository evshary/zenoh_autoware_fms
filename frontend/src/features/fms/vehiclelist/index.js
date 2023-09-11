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
    }, [])

    return(
        <>
            <TitleCard title="Vehicles" topMargin="mt-2" TopSideButtons={<Refresh />}>

            {/* Vehicle list after api call */}
            <div className="overflow-x-auto w-full">
                <table className="table w-full">
                    <thead>
                    <tr>
                        <th>Name</th>
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
                                                <div className="font-bold">{l.scope}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td>{l.address}</td>
                                    <td>test</td>
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