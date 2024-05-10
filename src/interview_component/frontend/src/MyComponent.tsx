import {
  Streamlit,
  StreamlitComponentBase,
  withStreamlitConnection,
} from "streamlit-component-lib"
import React, { PropsWithChildren, ReactNode } from "react"
import { useState, useEffect, useRef, useCallback } from 'react';
import Carousel, { Modal, ModalGateway, ViewType } from 'react-images'




interface State {

}






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


    // Arguments that are passed to the plugin in Python are accessible
    // via `this.props.args`. Here, we access the "name" arg.
    const name = this.props.args["name"];

      
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

// "withStreamlitConnection" is a wrapper function. It bootstraps the
// connection between your component and the Streamlit app, and handles
// passing arguments from Python -> Component.
//
// You don't need to edit withStreamlitConnection (but you're welcome to!).

export default withStreamlitConnection(MyComponent)
