import {
  Streamlit,
  StreamlitComponentBase,
  withStreamlitConnection,
} from "streamlit-component-lib"
import React, { PropsWithChildren, ReactNode } from "react"
import { useState, useEffect, useRef, useCallback } from 'react';
import Carousel, { Modal, ModalGateway, ViewType } from 'react-images'
import {functionalTemplates, chronologicalTemplates} from "./Templates" ;
import DisplaySession from "./DisplaySession";
import Welcome from "./Welcome"
import GoogleAuth from "./GoogleAuth";
import DisplayTemplate from "./DisplayTemplate" 



interface State {
  // numClicks: number
  // isFocused: boolean
  // modalIsOpen: boolean
  // imgSelected: number
  // datetimes: string
  thumbnails: {
    index: any;
    src: any;
    sizes: string[];
    width: number;
    height: number;
  }[]
  templates: ViewType[]
}

// interface LightboxProps {
//   thumbnails?: any
//   templates: ViewType[]
  
// }

// interface SessionProps {  
//   datetimes: string
// }


function Templates(props: State) {
  const streamlitCallback = (args: any) => { 
    Streamlit.setComponentValue(args)
  }
  return <DisplayTemplate lightboxCallback = {streamlitCallback} thumbnails={props.thumbnails} templates={props.templates}/>
}

// function Sessions(props: State) {
//   const onSelection = (args:number) => {
//     console.log(args)
//     Streamlit.setComponentValue(args);
//   }
//   const datetimes = props.datetimes.split(",")
//   const [pastSessions] = useState(datetimes)
//   return < DisplaySession msgs={pastSessions} onSelection={onSelection}/>
// }

function Signin() {
  const streamlitCallback = (token: any, data:any) => {
    var email = data.email 
    var name = data.name
    console.log(token, email)
    Streamlit.setComponentValue(`${name},${email},${token}`)
  }
  return < GoogleAuth.GoogleSignin signinCallback = {streamlitCallback}/>
}





const mappingFunction = (img:any, index:any) => ({index, src: img.source, sizes: ["(min-width: 480px) 20vw,(min-width: 1024px) 25vw,25vw"], width: 4, height: 3});

// var AWS = require('aws-sdk'); 

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
  // componentDidMount() {
  //   const name = this.props.args["name"];

  //   if (name != "welcome") {
  //     // Call the JavaScript function to update the text
  //     updateGreeting(name);
  //   }
  // }



  componentDidMount() {
    // Trigger updateGreeting automatically after the component is mounted

    try {
      const obj = JSON.parse(this.props.args["name"]);
      const greetingData = {
        name: obj.name,
        greeting: obj.greeting,    
      }
      localStorage.setItem('greetingData', JSON.stringify(greetingData));   
      console.log("set greeting data", JSON.stringify(greetingData))
    }
    catch(err) {
      console.log(err);
    }
  }
  
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
    if (name=="welcome") {
        return (<Welcome />)
    }
    else if (name=="functional") { 
      const funcThumbnails = functionalTemplates.map(mappingFunction);
      return (<Templates thumbnails={funcThumbnails} templates={functionalTemplates}/>)

    }
    else if (name=="chronological") {
      const chronoThumbnails = chronologicalTemplates.map(mappingFunction);
      return (<Templates thumbnails={chronoThumbnails} templates={chronologicalTemplates}/>)
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
      return < Signin/>
    }
    else if (name =="signout") { 
      console.log("asgasfjds")
      return <GoogleAuth.GoogleLogout />
      // googleLogout(); // what does this do??
    }
    else {
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
     
      return <div></div>
      // return (
      //   <div>
      //     Use the ref to access the div element
      //     <div id="greeting" ref={this.greetingRef}></div>
      //     <div id="greeting2" data-my-ref="myGreetingRef2"></div>
      //   </div>
      // );
    }

  }

}

// "withStreamlitConnection" is a wrapper function. It bootstraps the
// connection between your component and the Streamlit app, and handles
// passing arguments from Python -> Component.
//
// You don't need to edit withStreamlitConnection (but you're welcome to!).

export default withStreamlitConnection(MyComponent)
