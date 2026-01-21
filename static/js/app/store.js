// static/js/app/store.js
export function createStore(reducer, initialState) {
  let state = initialState;
  const listeners = new Set();

  function getState() {
    return state;
  }

  function dispatch(action) {
    state = reducer(state, action);
    for (const l of listeners) l(state, action);
  }

  function subscribe(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  }

  // 初始化一次（可选，但有时方便）
  dispatch({ type: "@@INIT" });

  return { getState, dispatch, subscribe };
}
