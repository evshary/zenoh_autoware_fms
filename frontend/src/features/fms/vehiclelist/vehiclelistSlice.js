import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import axios from 'axios'

export class Vehicle {
	constructor(name) {
		this.name = name
		this.address = ""
		this.status = ""
	}
}

export const getListContent = createAsyncThunk('/vehicle/list', async () => {
	const response = await axios.get('/list', {})
    var vehiclelist = [];
    var promises = []
    response.data.forEach(element => {
	    var p = axios.get('/status/'+element.scope, {})
             .then((response) => {
                var v = new Vehicle(element.scope)
                v.address = element.address
                v.status = response.data
                vehiclelist.push(JSON.stringify(v))
             })
        promises.push(p)
    })
    await Promise.all(promises)
    console.log("All vehicle list: ", vehiclelist)
	return vehiclelist
})

export const listSlice = createSlice({
    name: 'list',
    initialState: {
        isLoading: false,
        list : []
    },
    reducers: {
    },
    extraReducers: builder => {
		builder.addCase(getListContent.pending, state => {
			state.isLoading = true
			return state;
		})
		builder.addCase(getListContent.fulfilled, (state, action) => {
            state.list = action.payload
			state.isLoading = false
			return state;
		})
		builder.addCase(getListContent.rejected, state => {
			state.isLoading = false
			return state;
		})
	},
})

export default listSlice.reducer