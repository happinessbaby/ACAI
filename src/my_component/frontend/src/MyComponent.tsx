import {
  Streamlit,
  StreamlitComponentBase,
  withStreamlitConnection,
} from "streamlit-component-lib"
import React, { PropsWithChildren, ReactNode } from "react"
import Lightbox from "yet-another-react-lightbox";
import "yet-another-react-lightbox/styles.css";
import { GoogleLogin } from '@react-oauth/google';
import Gallery from 'react-photo-gallery'
import axios from 'axios';
import { useState, useEffect, useRef, useCallback } from 'react';
import { googleLogout, useGoogleLogin } from '@react-oauth/google';
import ReactFancyBox from 'react-fancybox'
import 'react-fancybox/lib/fancybox.css'
import Fancybox from './Fancybox'
import Carousel, { Modal, ModalGateway, ViewType } from 'react-images'
import Popup from 'reactjs-popup';
import 'reactjs-popup/dist/index.css';
import {functionalTemplates, chronologicalTemplates} from "./Templates" ;
import DisplaySession from "./DisplaySession";
import Welcome from "./Welcome"
import GoogleSignin from "./GoogleSignin";
import DisplayTemplate from "./DisplayTemplate"


interface State {
  // numClicks: number
  // isFocused: boolean
  // modalIsOpen: boolean
  // imgSelected: number
}

interface LightboxProps {
  thumbnails?: any
  templates: ViewType[]
  
}

interface SessionProps {  
  datetimes: string
}



function Templates(props: LightboxProps) {
  const streamlitCallback = (args: any) => { 
    Streamlit.setComponentValue(args)
  }
  return <DisplayTemplate lightboxCallback = {streamlitCallback} thumbnails={props.thumbnails} templates={props.templates}/>
}

function Sessions(props: SessionProps) {
  const onSelection = (args:number) => {
    console.log(args)
    Streamlit.setComponentValue(args);
  }
  const datetimes = props.datetimes.split(",")
  const [pastSessions] = useState(datetimes)
  return < DisplaySession msgs={pastSessions} onSelection={onSelection}/>
}

function Signin() {
  const streamlitCallback = (token: any, data:any) => {
    var email = data.email 
    console.log(token, email)
    Streamlit.setComponentValue(token + "###" + email)
  }
  return < GoogleSignin signinCallback = {streamlitCallback}/>
}

var aiSpeechOutput = document.getElementById("speech Alien")




const mappingFunction = (img:any, index:any) => ({index, src: img.source, sizes: ["(min-width: 480px) 20vw,(min-width: 1024px) 25vw,25vw"], width: 4, height: 3});

// var AWS = require('aws-sdk'); 

// var HOST = require('@amazon-sumerian-hosts/core')
// var BABYLON= require('babylonjs')
// var HOST = require('@amazon-sumerian-hosts/babylon')

// Initialize AWS and create Polly service objects
// AWS.config.region = 'us-east-1';
// AWS.config.credentials = new AWS.CognitoIdentityCredentials({
//   IdentityPoolId: 'us-east-1:1af97f5a-3988-4abc-bb7d-19fc2005de7a',
// });

// const polly = new AWS.Polly();
// const presigner = new AWS.Polly.Presigner();
// const speechInit = HOST.TextToSpeechFeature.initializeService(
//   polly,
//   presigner,
//   AWS.VERSION
// );


// const canvas = document.getElementById("renderCanvas") as HTMLCanvasElement;

// const engine = new Engine(canvas, true);
// // Create our first scene.
// var scene = new Scene(engine);


// const characterId = 'Maya';
// const characterConfig = HostObject.getCharacterConfig(
//   './character-assets',
//   characterId
//   );
// const pollyConfig = {pollyVoice: 'Joanna', pollyEngine: 'standard'};
// const host = await HostObject.createHost(scene, characterConfig, pollyConfig);  
// host.PointOfInterestFeature.setTarget(scene.activeCamera);


/**
 * This is a React-based component template. The `render()` function is called
 * automatically when your component should be re-rendered.
*/

class MyComponent extends StreamlitComponentBase<State> {
  // public state = { numClicks: 0, isFocused: false }
  // public state= {imgSelected:0, modalIsOpen:false, datetimes:""}

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
  //   document.getElementById('speakButton')!.onclick = () => {
  //   const speech = (document.getElementById('speechText')!as HTMLInputElement).value;
  //   host.TextToSpeechFeature.play(speech);
  // }
    // const closeLightbox = this.closeLightbox
    // const openLightbox =this.openLightbox
    if (name=="welcome") {
        return (<Welcome />)
    }
    else if (name=="functional") { 
      const funcThumbnails = functionalTemplates.map(mappingFunction);
      return (<Popup><Templates thumbnails={funcThumbnails} templates={functionalTemplates}/></Popup>)

    }
    else if (name=="chronological") {
      const chronoThumbnails = chronologicalTemplates.map(mappingFunction);
      return (<Popup><Templates thumbnails={chronoThumbnails} templates={chronologicalTemplates}/></Popup>)
    }
  //       return (
  //         <div>
  //           <Gallery photos={photosForGallery} onClick={(e, { index }) => this.setState({ imgSelected: index, modalIsOpen: true },   () => Streamlit.setComponentValue(index))} 
  //  />
  //           <ModalGateway>
  //             {this.state.modalIsOpen ? (
  //               <Modal onClose={() => {
  //                 this.setState(img_state => ({ modalIsOpen: !img_state.modalIsOpen}))}}>
  //                 <Carousel
  //                   currentIndex={this.state.imgSelected}
  //                   views = {functional_templates}
  //                   // views={functional_templates.map(x => ({
  //                   //   ...x,
  //                   //   srcset: x.srcSet,
  //                   //   caption: x.title
  //                   // }))}
  //                 />
  //               </Modal>
  //             ) : null}
  //           </ModalGateway>
  //         </div>
  //       );

      

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
      return < Signin/>
    }
    else if (name =="signout") { 
      localStorage.removeItem("accessTokenKey");
      return <div></div>
      // googleLogout(); // what does this do??
    }

    // else if (name=="stream") {
    //   s.push(name)
    // }
    // else {
    //   return (< Sessions datetimes={name} />)
    // }
    else {
      aiSpeechOutput = name
      return null
    
    }

  }

}

// "withStreamlitConnection" is a wrapper function. It bootstraps the
// connection between your component and the Streamlit app, and handles
// passing arguments from Python -> Component.
//
// You don't need to edit withStreamlitConnection (but you're welcome to!).

export default withStreamlitConnection(MyComponent)
