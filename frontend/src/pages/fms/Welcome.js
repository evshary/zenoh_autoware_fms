import { useEffect } from 'react'
import { useDispatch } from 'react-redux'
import { setPageTitle } from '../../features/common/headerSlice'
import GetStarted from '../../features/fms/GetStarted'

function InternalPage(){

    const dispatch = useDispatch()

    useEffect(() => {
        dispatch(setPageTitle({ title : ""}))
      }, [])

    return(
      <div className="hero h-4/5 bg-base-200">
      <div className="hero-content">
        <div className="max-w-md">
            <GetStarted />
        </div>
      </div>
    </div>
    )
}

export default InternalPage