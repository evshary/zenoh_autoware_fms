import { useEffect, useState, useRef, forwardRef } from "react"
import { useDispatch, useSelector } from "react-redux"
import TitleCard from "../../../components/Cards/TitleCard"
import { startupTeleop, setGear, setVelocity, setTurn } from "./remoteDriveSlice"
import { Refresh } from "../vehiclelist"
import { StyleSelect, StyleTextArea } from "../common"
import { CamImageWithStatus } from "./cameraImg"
import axios from 'axios'

const VehicleSelect = forwardRef((props, ref) => {
    return (
        <select ref={ref} className="bg-gray-50 border border-gray-300 text-gray-900 text-lg rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-1/2 p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500">
            <option value="None">None</option>
            {
                props.state.map((element, idx) => {
                    var V = JSON.parse(element)
                    return (<option key={V.name} value={V.name}>{V.name}</option>)
                })
            }
        </select>
    )
})


const VehicleSelectButton = (props) => {const dispatch = useDispatch()
    return(
        <button 
            className="btn px-6 btn-sm normal-case btn-info" 
            onClick={() => {dispatch(startupTeleop((props.refon.current)?(props.refon.current.value):"None"))}}>{props.text}</button>
    )
}

const TeleopButton = (props) => {
    return(
        <button 
            className="btn px-6 btn-sm normal-case btn-info" 
            onClick={() => {props.handleClick(props.scope, (props.refon.current)?(props.refon.current.value):"None")}}>{props.text}</button>
    )
}

function TeleopPnael() {
    const scopeRef = useRef(null);
    const gearRef = useRef(null);
    const velocityRef = useRef(null);
    const {list} = useSelector(state => state.list)
    const teleopScope = useSelector(state => state.teleop.teleopScope)
    const cameraUrl = useSelector(state => state.teleop.cameraUrl)
    const [teleopStatus, setTeleopStatus] = useState( () => {
        return {
            velocity: '---',
            gear: '---',
            steering: '---'
        }
    })


    useEffect(() => {
        /* Get the status of vehicle */
        const getTeleopStatus = async () => {
            
            if(teleopScope === 'None') return;
            const response = await axios.get('/teleop/status', {});
            console.log(response.data)
            let newStatus = Object.assign({}, {
                velocity: response.data.velocity,
                gear: response.data.gear,
                steering: response.data.steering
            })
            setTeleopStatus(newStatus)
        }

        /* Get status of vehicle every 1 sec after startup */
        const set_interval = setInterval(getTeleopStatus, 1000);

        /* Clear the timer when unmount */
        return () => {
            clearInterval(set_interval);
        }

    }, [teleopScope])

    return (
        <>
            <TitleCard title={(teleopScope !== "None")?`Remote Driving on ${teleopScope}` : "Remote Driving"} TopSideButtons={<Refresh />}>
                <div className="grid grid-rows-4 grid-flow-col gap-4">
                    <CamImageWithStatus classname="row-span-4 col-span-10 bg-no-repeat bg-cover" bgUrl={cameraUrl} status={teleopStatus} />

                    <div className="row-span-1 col-span-1">
                        <label className="block mb-2 text-lg font-medium text-gray-900 dark:text-white">Select a vehicle</label>
                        <div className="flex">
                            <VehicleSelect state={list} ref={scopeRef} /> 
                            <div className="inline-block w-1/4 p-2">
                                <VehicleSelectButton text="Teleop" handleClick={startupTeleop} refon={scopeRef} reftype="select" />
                            </div>
                        </div>
                    </div>
                    {/* <hr></hr> */}
                    
                    {/* list of gear in <select></select> 
                        * Parking, Drive, Reverse, Neutral, Low
                        */}
                    <div className="row-span-1 col-span-1">
                        <label className="block mb-2 text-lg font-medium text-gray-900 dark:text-white">Gear</label>
                        <div className="flex">
                            <StyleSelect options={["Parking", "Drive", "Reverse", "Neutral", "Low"]} ref={gearRef} />
                            <div className="inline-block w-1/4 p-2">
                                <TeleopButton text="Set" handleClick={setGear} scope={teleopScope} refon={gearRef} reftype="select" />
                            </div>
                        </div>
                    </div>
                    
                    <div className="row-span-1 col-span-1">
                        <label className="block mb-2 text-lg font-medium text-gray-900 dark:text-white">Velocity</label>
                        <div className="flex">
                            <StyleTextArea placeHolder="km/hr" ref={velocityRef} />
                            <div className="inline-block w-1/4 p-2">
                                <TeleopButton text="Set" handleClick={setVelocity} scope={teleopScope} refon={velocityRef} reftype="textarea"/>
                            </div>
                        </div>
                    </div>

                    <div className="row-span-1 col-span-1 flex justify-center items-center">
                        <img src={require('./steering-wheel.png')} className="h-40" />
                    </div>
                </div>
            </TitleCard>
        </>
    )
}

export default TeleopPnael