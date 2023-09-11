import { useEffect } from 'react'
import { useDispatch } from 'react-redux'
import { setPageTitle } from '../../features/common/headerSlice'
import Lists from '../../features/fms/vehiclelist'

function InternalPage(){
    const dispatch = useDispatch()

    useEffect(() => {
        dispatch(setPageTitle({ title : "Vehicle List"}))
      }, [])

    return(
        <Lists />
    )
}

export default InternalPage