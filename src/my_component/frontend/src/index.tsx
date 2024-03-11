import React from "react"
import ReactDOM from "react-dom"
import MyComponent from "./MyComponent"
import { GoogleOAuthProvider } from '@react-oauth/google';


ReactDOM.render(
  <GoogleOAuthProvider clientId="617595678646-95o6n84rc2a6v2c73uj538oc9dl4grua.apps.googleusercontent.com">
  <React.StrictMode>
    <MyComponent />
  </React.StrictMode>,
  </GoogleOAuthProvider>,
  document.getElementById("root")
)

