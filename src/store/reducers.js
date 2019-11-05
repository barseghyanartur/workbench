import {combineReducers} from "redux"

function activities(state = [], action) {
  switch (action.type) {
    case "ADD_ACTIVITY":
      return state.concat([action.activity])
    case "REMOVE_ACTIVITY":
      return state.filter(activity => activity.id != action.activity)
    default:
      return state
  }
}

const reducer = combineReducers({
  activities,
})

export default reducer
