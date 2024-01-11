import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
// import { useDispatch } from "react-redux"
import axios from 'axios'

export const selectVehicle = createAsyncThunk('map/startup', async (scope) => {
	if(scope !== "None"){
		const res = await axios.get(`/map/startup?scope=${scope}`, {})
	}
    return scope
})

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