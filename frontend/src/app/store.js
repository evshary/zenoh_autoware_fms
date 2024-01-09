import { configureStore } from '@reduxjs/toolkit'
import headerSlice from '../features/common/headerSlice'
import modalSlice from '../features/common/modalSlice'
import rightDrawerSlice from '../features/common/rightDrawerSlice'
import listSlice from '../features/fms/vehiclelist/vehiclelistSlice'
import teleopSlice from '../features/fms/remotedrive/remoteDriveSlice'
import mapViewSlice from '../features/fms/mapview/mapViewSlice'


const combinedReducer = {
  header : headerSlice,
  rightDrawer : rightDrawerSlice,
  modal : modalSlice,
  list : listSlice,
  teleop: teleopSlice,
  mapview: mapViewSlice
}

export default configureStore({
    reducer: combinedReducer
})