import { useEffect } from 'react'
import { useDispatch } from 'react-redux'
import { setPageTitle } from '../../features/common/headerSlice'
import MapViewer from '../../features/fms/mapview'

function InternalPage(){

    const dispatch = useDispatch()

    useEffect(() => {
        dispatch(setPageTitle({ title : "Map View"}))
      }, [])
      
    return(
        <MapViewer xmlFile="/carla_map/Town01/lanelet2_map.osm" center={[0.0, 0.0]}/>
    )
}

export default InternalPage