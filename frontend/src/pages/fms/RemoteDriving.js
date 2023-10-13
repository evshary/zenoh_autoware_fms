import { useEffect } from 'react'
import { useDispatch } from 'react-redux'
import TeleopPnael from '../../features/fms/remotedrive'
import { setPageTitle } from '../../features/common/headerSlice'

function InternalPage(){
    const dispatch = useDispatch()

    useEffect(() => {
        dispatch(setPageTitle({ title : "Remote Driving"}))
      }, [])


    return(
        <TeleopPnael />
    )
}

export default InternalPage