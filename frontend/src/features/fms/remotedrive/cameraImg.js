export const CamImageWithStatus = (props) => {
    /********************************************************
     * props.classname: class name
     * props.bgUrl: URL of background image
     * props.status: The status about vehicle being teleoped
     ********************************************************/
    return (
        <div className={props.classname} style={{
            backgroundImage: `url(${props.bgUrl})`,
            height: 650
        }}>
            <div className="relative w-1/3 p-4">
                <table className="w-full text-sm text-left font-bold text-black-500 dark:text-gray-400">
                    <tbody>
                         <tr className="border-b dark:bg-gray-800 dark:border-gray-700">
                            <th scope="row" className="px-6 py-4 font-bold text-gray-900 whitespace-nowrap dark:text-white">
                                Velocity
                            </th>
                            <td>{(props.status)?props.status.velocity: '0'}</td>
                            <td>km/hr</td>
                        </tr>
                         <tr className="border-b dark:bg-gray-800 dark:border-gray-700">
                            <th scope="row" className="px-6 py-4 font-bold text-gray-900 whitespace-nowrap dark:text-white">
                                Gear
                            </th>
                            <td>{(props.status)?props.status.gear: 'None'}</td>
                            <td></td>
                        </tr>
                         <tr className="border-b dark:bg-gray-800 dark:border-gray-700">
                            <th scope="row" className="px-6 py-4 font-bold text-gray-900 whitespace-nowrap dark:text-white">
                                Steering
                            </th>
                            <td>{(props.status)?props.status.steering: '0'}</td>
                            <td></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    )
}