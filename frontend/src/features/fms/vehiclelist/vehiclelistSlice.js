import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import axios from 'axios'

export const getListContent = createAsyncThunk('/vehicle/list', async () => {
	const response = await axios.get('/list', {})
	return response;
})

export const listSlice = createSlice({
    name: 'list',
    initialState: {
        isLoading: false,
        list : []
    },
    reducers: {
    },
    extraReducers: {
		[getListContent.pending]: state => {
			state.isLoading = true
		},
		[getListContent.fulfilled]: (state, action) => {
			state.list = action.payload.data
			state.isLoading = false
		},
		[getListContent.rejected]: state => {
			state.isLoading = false
		},
    }
})

export default listSlice.reducer