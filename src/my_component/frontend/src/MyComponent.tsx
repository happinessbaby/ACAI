import {
  Streamlit,
  StreamlitComponentBase,
  withStreamlitConnection,
} from "streamlit-component-lib"
import React, { ReactNode } from "react"
import Lightbox from "yet-another-react-lightbox";
import "yet-another-react-lightbox/styles.css";
import { GoogleLogin } from '@react-oauth/google';
import Gallery from 'react-photo-gallery'
import axios from 'axios';
import { useState, useEffect, useCallback } from 'react';
import { googleLogout, useGoogleLogin } from '@react-oauth/google';
import ReactFancyBox from 'react-fancybox'
import 'react-fancybox/lib/fancybox.css'
import Fancybox from './Fancybox'
import Carousel, { Modal, ModalGateway } from 'react-images'
import {functional_templates} from "./functional_templates" ;

interface State {
  // numClicks: number
  // isFocused: boolean
  modalIsOpen: boolean
  imgSelected: number
}




const mappingFunction = (img:any, index:any) => ({index, src: img.source, sizes: ["(min-width: 480px) 20vw,(min-width: 1024px) 25vw,25vw"], width: 4, height: 3});

/**
 * This is a React-based component template. The `render()` function is called
 * automatically when your component should be re-rendered.
*/

class MyComponent extends StreamlitComponentBase<State> {
  // public state = { numClicks: 0, isFocused: false }
  public state= {imgSelected:0, modalIsOpen:false}

  // closeLightbox = () => {
  //   this.setState(img_state => ({ modalIsOpen: !img_state.modalIsOpen}))
  // };

  // openLightbox= (e:any, { index }) => this.setState({ imgSelected: index, modalIsOpen:true})
  
  public render = (): ReactNode => {
    // const [currentImage, setCurrentImage] = useState(0);
    // const [viewerIsOpen, setViewerIsOpen] = useState(false);
    // const openLightbox = useCallback((event, { photo, index }) => {
    //   setCurrentImage(index);
    //   setViewerIsOpen(true);
    //   Streamlit.setComponentValue(index);
    // }, []);
    
    // const closeLightbox = () => {
    //   setCurrentImage(0);
    //   setViewerIsOpen(false);
    // };
    // Arguments that are passed to the plugin in Python are accessible
    // via `this.props.args`. Here, we access the "name" arg.
    const name = this.props.args["name"];
    // const closeLightbox = this.closeLightbox
    // const openLightbox =this.openLightbox
    if (name=="functional") { 
      const photosForGallery = functional_templates.map(mappingFunction)
        return (
          <div>
            <Gallery photos={photosForGallery} onClick={(e, { index }) => this.setState({ imgSelected: index, modalIsOpen: true },   () => Streamlit.setComponentValue(index))} 
   />
            <ModalGateway>
              {this.state.modalIsOpen ? (
                <Modal onClose={() => {
                  this.setState(img_state => ({ modalIsOpen: !img_state.modalIsOpen}))}}>
                  <Carousel
                    currentIndex={this.state.imgSelected}
                    views = {functional_templates}
                    // views={functional_templates.map(x => ({
                    //   ...x,
                    //   srcset: x.srcSet,
                    //   caption: x.title
                    // }))}
                  />
                </Modal>
              ) : null}
            </ModalGateway>
          </div>
        );

      
      // return <Gallery
      // photos={functional_templates}
      // direction={"column"}
      // columns={4}
      // onClick={(e, { index }) => this.imageClick(index)} /> 
      // return (
      //   <div>
      //     <Fancybox
      //       options={{
      //         Carousel: {
      //           infinite: false,
      //         },
      //       }}
      //     >
      //       <a data-fancybox="gallery" href="/resume_templates/functional/functional0.png">
      //         <img
      //           alt=""
      //           src= "/resume_templates/functional/functional0_thmb.png"
      //           width="500"
      //           height="500"
      //           onClick={()=>this.imageClick}
      //         />
      //       </a>
      //       <a data-fancybox="gallery" href="/resume_templates/functional/functional1.png">
      //         <img
      //           alt=""
      //           src="/resume_templates/functional/functional1_thmb.png"
      //           width="500"
      //           height="500"
      //         />
      //       </a>
      //       <a data-fancybox="gallery" href="/resume_templates/functional/functional2.png">
      //         <img
      //           alt=""
      //           src="/resume_templates/functional/functional2_thmb.png"
      //           width="500"
      //           height="500"
      //           onClick={this.imageClick}
      //         />
      //       </a>
      //     </Fancybox>
      //   </div>
      // );

    }
    else if (name=="signin") {


    // Streamlit sends us a theme object via props that we can use to ensure
    // that our component has visuals that match the active theme in a
    // streamlit app.
    // const { theme } = this.props
    // const style: React.CSSProperties = {}

    // Maintain compatibility with older versions of Streamlit that don't send
    // a theme object.
    // if (theme) {
    //   // Use the theme object to style our button border. Alternatively, the
    //   // theme style is defined in CSS vars.
    //   const borderStyling = `1px solid ${
    //     this.state.isFocused ? theme.primaryColor : "gray"
    //   }`
    //   style.border = borderStyling
    //   style.outline = borderStyling
    // }
//     const [ user, setUser ] = useState(null);
//     const [ profile, setProfile ] = useState(null);
//     const login = useGoogleLogin({
//       onSuccess: (codeResponse) => setUser(codeResponse),
//       onError: (error) => console.log('Login Failed:', error)
//       });

//       useEffect(
//         () => {
//             if (user) {
//                 axios
//                     .get(`https://www.googleapis.com/oauth2/v1/userinfo?access_token=${user.access_token}`, {
//                         headers: {
//                             Authorization: `Bearer ${user.access_token}`,
//                             Accept: 'application/json'
//                         }
//                     })
//                     .then((res) => {
//                         setProfile(res.data);
//                     })
//                     .catch((err) => console.log(err));
//             }
//         },
//         [ user ]
//     );

//     const logOut = () => {
//       googleLogout();
//       setProfile(null);
//   };
//   return (
//     <div>
//         <h2>React Google Login</h2>
//         <br />
//         <br />
//         {profile ? (
//             <div>
//                 <img src={profile.picture} alt="user image" />
//                 <h3>User Logged in</h3>
//                 <p>Name: {profile.name}</p>
//                 <p>Email Address: {profile.email}</p>
//                 <br />
//                 <br />
//                 <button onClick={logOut}>Log out</button>
//             </div>
//         ) : (
//             <button onClick={() => login()}>Sign in with Google 🚀 </button>
//         )}
//     </div>
// );
    return (
    <GoogleLogin
        onSuccess={credentialResponse => {
          console.log(credentialResponse);
          Streamlit.setComponentValue(credentialResponse)
        }}
        onError={() => {
          console.log('Login Failed');
        }}
      />
      );
    }
    else if (name =="signout") {
      googleLogout();
    }




    // Show a button and some text.
    // When the button is clicked, we'll increment our "numClicks" state
    // variable, and send its new value back to Streamlit, where it'll
    // be available to the Python program.
    // return (
    //   <span>
    //     Hello, {name}! &nbsp;
    //     <button
    //       style={style}
    //       onClick={this.onClicked}
    //       disabled={this.props.disabled}
    //       onFocus={this._onFocus}
    //       onBlur={this._onBlur}
    //     >
    //       Click Me!
    //     </button>
    //   </span>
    // )
  }

  // /** Click handler for our "Click Me!" button. */
  // private onClicked = (): void => {
    // Increment state.numClicks, and pass the new value back to
    // Streamlit via `Streamlit.setComponentValue`.
  //   this.setState(
  //     prevState => ({ numClicks: prevState.numClicks + 1 }),
  //     () => Streamlit.setComponentValue(this.state.numClicks)
  //   )
  // }

  // /** Focus handler for our "Click Me!" button. */
  // private _onFocus = (): void => {
  //   this.setState({ isFocused: true })
  // }

  // /** Blur handler for our "Click Me!" button. */
  // private _onBlur = (): void => {
  //   this.setState({ isFocused: false })
  // }
}

// "withStreamlitConnection" is a wrapper function. It bootstraps the
// connection between your component and the Streamlit app, and handles
// passing arguments from Python -> Component.
//
// You don't need to edit withStreamlitConnection (but you're welcome to!).

export default withStreamlitConnection(MyComponent)
