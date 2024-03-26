import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
// import { useDispatch } from "react-redux"
import axios from 'axios'

// export const selectVehicle = createAsyncThunk('map/startup', async (scope) => {
// 	if(scope !== "None"){
// 		const res = await axios.get(`/map/startup?scope=${scope}`, {})
// 	}
//     return scope
// })

export const getVehicleList = createAsyncThunk('map/list', async () => {
	const response = await axios.get(`/map/list`, {})
	return response.data
})

export const setVehicleGoal =  createAsyncThunk('map/setGoal', async (scope, lat, lon) => {
	const response = await axios.get(`/map/setGoal?scope=${scope}&lat=${lat}&lon=${lon}`, {});
	return response;
})

export const setEngage =  createAsyncThunk('map/engage', async (scope) => {
	const response = await axios.get(`/map/engage?scope=${scope}`, {});
	return response;
})

export const mapViewSlice = createSlice({
    name: 'mapview',
    initialState: {
		listIsLoading: false,
		setGoalIsLoading: false,
		engageIsLoading: false,
        list: []
    },
    reducers: {
    },
    extraReducers: builder => {
		builder.addCase(getVehicleList.pending, state => {
			state.listIsLoading = true
			return state;
		})
		builder.addCase(getVehicleList.fulfilled, (state, action) => {
			state.listIsLoading = false
			state.list = action.payload
			return state;
		})
		builder.addCase(getVehicleList.rejected, state => {
			state.listIsLoading = false
			return state;
		})

		builder.addCase(setVehicleGoal.pending, state => {
			state.setGoalIsLoading = true
			return state;
		})
		builder.addCase(setVehicleGoal.fulfilled, state => {
			state.setGoalIsLoading = false
			return state;
		})
		builder.addCase(setVehicleGoal.rejected, state => {
			state.setGoalIsLoading = false
			return state;
		})

		builder.addCase(setEngage.pending, state => {
			state.engageIsLoading = true
			return state;
		})
		builder.addCase(setEngage.fulfilled, state => {
			state.engageIsLoading = false
			return state;
		})
		builder.addCase(setEngage.rejected, state => {
			state.engageIsLoading = false
			return state;
		})
	},
})

export default mapViewSlice.reducer