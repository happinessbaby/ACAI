import React from "react"
import ReactDOM from "react-dom"
import MyComponent from "./MyComponent"
import { GoogleOAuthProvider } from '@react-oauth/google';


ReactDOM.render(
  <React.StrictMode>
    <MyComponent />
  </React.StrictMode>,
  document.getElementById("root")
)

