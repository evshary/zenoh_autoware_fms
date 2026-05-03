import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import axios from 'axios'

export const startupTeleop = createAsyncThunk('teleop/startup', async (scope) => {
    if (scope !== "None") {
        await axios.get(`/teleop/startup?scope=${scope}`, {})
    }
    return scope
})

export const teleopSlice = createSlice({
    name: 'teleop',
    initialState: {
        isLoading: false,
        teleopScope: "None",
        latency: 0,
        isControlling: false,
    },
    reducers: {
        updateLatency: (state, action) => { state.latency = action.payload; },
        updateControlStatus: (state, action) => { state.isControlling = action.payload; },
    },
    extraReducers: builder => {
        builder.addCase(startupTeleop.pending, state => { state.isLoading = true })
        builder.addCase(startupTeleop.fulfilled, (state, action) => {
            state.isLoading = false
            state.teleopScope = action.payload
        })
        builder.addCase(startupTeleop.rejected, state => { state.isLoading = false })
    },
})

export const { updateLatency, updateControlStatus } = teleopSlice.actions
export default teleopSlice.reducer
