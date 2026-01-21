export const initialState = {
  loading: false,
  error: "",
  history: [],
  form: {
    style: 'none',
    aspectRatio: '16:9',
    clothing: '',
    shot: '',
    accessory: '',
    body: '',
    cup: '',
    action: '',
    scene: '',
    effect: '',
    customText: ''
  }
};

export function reducer(state, action) {
  switch (action.type) {
    case "INIT_SUCCESS":
      return {
        ...state,
        loading: false,
        history: action.history || [],
        error: "",
      };

    case "FORM_UPDATE":
      return {
        ...state,
        form: { ...state.form, ...action.patch }
      };

    case "REQUEST_START":
      return { ...state, loading: true, error: "" };

    case "REQUEST_ERROR":
      return { ...state, loading: false, error: action.message || "Unknown error" };

    case "GENERATE_SUCCESS":
      return {
        ...state,
        loading: false,
        error: "",
        history: [action.record, ...(state.history || [])],
      };

    default:
      return state;
  }
}
