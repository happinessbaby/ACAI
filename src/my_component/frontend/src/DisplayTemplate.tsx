
import SelectedImage from "./SelectedImage";
import Gallery from 'react-photo-gallery'
import { useState, useEffect, useRef, useCallback } from 'react';
import Carousel, { Modal, ModalGateway, ViewType } from 'react-images'
import React from "react"



function DisplayTemplate(props: any) {
    const [currentImage, setCurrentImage] = useState(0);
    const [viewIsOpen, setViewerIsOpen] = useState(false);
    const [select, setSelect] = useState(false);

    const toggleSelect = () => {
      setSelect(!select);
    };
  
    const imageRenderer = useCallback(
      ({ index, left, top, key, photo }) => (
        <SelectedImage
          direction = "column"
          selected={select ? true : false}
          key={key}
          margin={"2px"}
          index={index}
          photo={photo}
          left={left}
          top={top}
        />
      ),
      [select]
    );
  
    const openLightbox = useCallback((event, { photo, index }) => {
      setCurrentImage(index);
      setViewerIsOpen(true);
    }, []);
    
    const closeLightbox = () => {
      setCurrentImage(0);
      setViewerIsOpen(false);
    };
    // const handleSubmit = () => {
    //   Streamlit.setComponentValue(currentImage);
    // };
    
    return (
      <div>
        <Gallery photos={props.thumbnails} renderImage={imageRenderer} onClick={openLightbox}/>
        <ModalGateway>
          {viewIsOpen ? (
            <Modal onClose={closeLightbox}>
              <Carousel
                currentIndex={currentImage}
                views = {props.templates}
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

}

export default DisplayTemplate