import { forwardRef } from "react"

export const StyleSelect = forwardRef((props, ref) => {
    /*********************************************
     *  props.options: the option list of select
     *********************************************/
    return (
        <select ref={ref} className="bg-gray-50 border border-gray-300 text-gray-900 text-lg rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-1/2 p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500">
            {
                props.options.map((opt, idx) => {
                    return (<option key={opt} value={opt}>{opt}</option>)
                })
            }
        </select>
    )
})

export const StyleTextArea = forwardRef((props, ref) => {
    /*********************************************
     *  props.numRows: rows of textarea
     *  props.placeHolder: placeholder of textarea
     *********************************************/
    return (
        <textarea ref={ref} rows={(props.numRows)?props.rows:(1)} placeholder={props.placeHolder} className="block p-2 w-1/2 text-lg text-gray-900 bg-gray-50 rounded-lg border border-gray-300 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"></textarea>
    )
})