import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { useDispatch } from "react-redux"
import axios from 'axios'

export const startupTeleop = createAsyncThunk('teleop/startup', async (scope) => {
	if(scope !== "None"){
		const res = await axios.get(`/teleop/startup?scope=${scope}`, {})
	}
    return scope
})

export const setGear =  async (scope, gear) => {
	const response = await axios.get(`/teleop/gear?scope=${scope}&gear=${gear}`, {});
	console.log(response)
	return response;
}

export const setVelocity =  async (scope, velocity) => {
	const response = await axios.get(`/teleop/velocity?scope=${scope}&velocity=${velocity}`, {});
	console.log(response)
	return response;
}

export const setTurn =  async (scope, angle) => {
	const response = await axios.get(`/teleop/turn?scope=${scope}&angle=${angle}`, {});
	console.log(response)
	return response;
}

export const teleopSlice = createSlice({
    name: 'teleop',
    initialState: {
        teleopScope: "None",
		cameraUrl: "http://127.0.0.1:5000/video"
    },
    reducers: {
    },
    extraReducers: builder => {
		builder.addCase(startupTeleop.pending, state => {
			// state.isLoading = true
			return state;
		})
		builder.addCase(startupTeleop.fulfilled, (state, action) => {
			const currentTime = new Date();
			const newUrl = `${state.cameraUrl}?${currentTime.getTime()}`
			state.cameraUrl = newUrl
			state.teleopScope = action.payload
			return state;
		})
		builder.addCase(startupTeleop.rejected, state => {
			// state.isLoading = false
			return state;
		})
	},
})

export default teleopSlice.reducer