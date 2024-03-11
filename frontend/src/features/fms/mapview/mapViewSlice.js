import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
// import { useDispatch } from "react-redux"
import axios from 'axios'

export const selectVehicle = createAsyncThunk('map/startup', async (scope) => {
	if(scope !== "None"){
		const res = await axios.get(`/map/startup?scope=${scope}`, {})
	}
    return scope
})

export const setVehicleGoal =  async (scope, lat, lon) => {
	const response = await axios.get(`/map/setGoal?scope=${scope}&lat=${lat}&lon=${lon}`, {});
	return response;
}

export const setEngage =  async (scope) => {
	const response = await axios.get(`/map/engage?scope=${scope}`, {});
	return response;
}

export const mapViewSlice = createSlice({
    name: 'mapview',
    initialState: {
		isLoading: false,
        scope: "None"
    },
    reducers: {
    },
    extraReducers: builder => {
		builder.addCase(selectVehicle.pending, state => {
			state.isLoading = true
			return state;
		})
		builder.addCase(selectVehicle.fulfilled, (state, action) => {
			state.isLoading = false
			state.scope = action.payload
			return state;
		})
		builder.addCase(selectVehicle.rejected, state => {
			state.isLoading = false
			return state;
		})
	},
})

export default mapViewSlice.reducer