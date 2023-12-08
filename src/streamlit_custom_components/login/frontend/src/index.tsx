import { Streamlit, RenderData } from "streamlit-component-lib"
// import { OAuth2Client } from "google-auth-library";
// require('dotenv').config();

// declare global {
//   interface Window {
//    id_token?: void // Make it optional
//   }
//  }
// const CLIENT_ID = process.env.GOOGLE_DEFAULT_CLIENT_ID!;
const googleButton = document.getElementById("google")!;
const token = document.getElementById("token")!;


/**
 * The component's render function. This will be called immediately after
 * the component is initially loaded, and then again every time the
 * component gets new data from Python.
 */
function onRender(event: Event): void {
  // Get the RenderData from the event
  const data = (event as CustomEvent<RenderData>).detail

  // Maintain compatibility with older versions of Streamlit that don't send
  // a theme object.
  // if (data.theme) {
  //   // Use CSS vars to style our button border. Alternatively, the theme style
  //   // is defined in the data.theme object.
  //   // const borderStyling = `1px solid var(${
  //   //   isFocused ? "--primary-color" : "gray"
  //   // })`
  //   // button.style.border = borderStyling
  //   // button.style.outline = borderStyling
    
  // }


  // RenderData.args is the JSON dictionary of arguments sent from the
  // Python script.
  // let name = data.args["name"]
  let name = data.args["name"]

if (name=="signin") {
    googleButton.style.visibility = "visible";
    // token.addEventListener("change", function handleClick(event) {
    //   var token_id = (token as HTMLInputElement).value
    //   const {OAuth2Client} = require('google-auth-library');
    //   const client = new OAuth2Client();
    //   async function verify() {
    //     const ticket = await client.verifyIdToken({
    //         idToken: token_id,
    //         audience: CLIENT_ID,  // Specify the CLIENT_ID of the app that accesses the backend
    //         // Or, if multiple clients access the backend:
    //         //[CLIENT_ID_1, CLIENT_ID_2, CLIENT_ID_3]
    //     });
    //     const payload = ticket.getPayload();
    //     const userid = payload['sub'];
    //     Streamlit.setComponentValue(userid);
    //     // If request specified a G Suite domain:
    //     // const domain = payload['hd'];
    //   }
    //   verify().catch(console.error);
    // });
    // function onSignIn(googleUser) {
    //   var profile = googleUser.getBasicProfile();
    //   var id_token = googleUser.getAuthResponse().id_token;
    //   // console.log('ID: ' + profile.getId()); // Do not send to your backend! Use an ID token instead.
    //   // console.log('Name: ' + profile.getName());
    //   // console.log('Image URL: ' + profile.getImageUrl());
    //   // console.log('Email: ' + profile.getEmail()); // This is null if the 'email' scope is not present.
    //   Streamlit.setComponentValue(id_token);
    // };
  }
  else if (name=="signout") {
    document.getElementById("google")!.style.visibility = "invisible";
    // function signOut() {
    //   var auth2 = gapi.auth2.getAuthInstance();
    //   auth2.signOut().then(function () {
    //     console.log('User signed out.');
    //   });
    // }
  }

    // We tell Streamlit to update our frameHeight after each render event, in
  // case it has changed. (This isn't strictly necessary for the example
  // because our height stays fixed, but this is a low-cost function, so
  // there's no harm in doing it redundantly.)
  Streamlit.setFrameHeight()
}

// Attach our `onRender` handler to Streamlit's render event.
Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender)

// Tell Streamlit we're ready to start receiving data. We won't get our
// first RENDER_EVENT until we call this function.
Streamlit.setComponentReady()

// Finally, tell Streamlit to update our initial height. We omit the
// `height` parameter here to have it default to our scrollHeight.
Streamlit.setFrameHeight()
