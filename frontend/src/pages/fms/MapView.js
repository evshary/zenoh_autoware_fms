import { useEffect } from 'react'
import { useDispatch } from 'react-redux'
import { setPageTitle } from '../../features/common/headerSlice'
import MapPanel from '../../features/fms/mapview'

function InternalPage(){

    const dispatch = useDispatch()

    useEffect(() => {
        dispatch(setPageTitle({ title : "Map View"}))
      }, [])
      
    return(
        <MapPanel />
    )
}

export default InternalPage