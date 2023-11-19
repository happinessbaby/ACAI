import { Streamlit, RenderData } from "streamlit-component-lib"

// Add text and a button to the DOM. (You could also add these directly
// to index.html.)
// const span = document.body.appendChild(document.createElement("span"))
// const textNode = span.appendChild(document.createTextNode(""))
// const button = span.appendChild(document.createElement("button"))
// button.textContent = "Click Me!"
// const imgNode = document.body.appendChild(document.createElement("img"))
// const div = document.body.appendChild(document.createElement("div"))
// const imgNode = document.getElementById("MyImg")!;
const imgs = document.getElementById("images")!;
const imgNode0 = document.getElementsByTagName("a")[0];
const imgNode1 = document.getElementsByTagName("a")[1];
const imgNode2 = document.getElementsByTagName("a")[2];
const imgThumb0 = document.getElementsByTagName("img")[0];
const imgThumb1 = document.getElementsByTagName("img")[1];
const imgThumb2 = document.getElementsByTagName("img")[2];
 // Get the modal
// var modal = document.getElementById("myModal")!;
// const modalImg = modal.appendChild(document.createElement("img"))
// modalImg.classList.add("modal_content")
// const modalImg = document.getElementById("img0")!;

// Get the <span> element that closes the modal
let close: HTMLElement = document.getElementsByClassName("close")[0] as HTMLElement;

// When the user clicks on <span> (x), close the modal
// close.onclick = function() {
//   modal.style.display = "none";
// }

// Add a click handler to our button. It will send data back to Streamlit.
// let numClicks = 0
// let isFocused = false
// button.onclick = function(): void {
//   // Increment numClicks, and pass the new value back to
//   // Streamlit via `Streamlit.setComponentValue`.
//   numClicks += 1
//   Streamlit.setComponentValue(numClicks)
// }

// button.onfocus = function(): void {
//   isFocused = true
// }

// button.onblur = function(): void {
//   isFocused = false
// }

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

  // // Disable our button if necessary.
  // button.disabled = data.disabled  

  // RenderData.args is the JSON dictionary of arguments sent from the
  // Python script.
  // let name = data.args["name"]
  let dir_name = data.args["name"]
  if (dir_name=="functional") {
    const img0 =  "/resume_templates/functional/functional0.png";
    const img1 = "/resume_templates/functional/functional1.png";
    const img2 = "/resume_templates/functional/functional2.png";
    const img0_thmb = "/resume_templates/functional/functional0_thmb.png";
    const img1_thmb = "/resume_templates/functional/functional1_thmb.png";
    const img2_thmb = "/resume_templates/functional/functional2_thmb.png";
    imgNode0.href = img0;
    imgNode1.href = img1;
    imgNode2.href = img2;
    imgThumb0.src = img0_thmb;
    imgThumb1.src = img1_thmb;
    imgThumb2.src = img2_thmb;
  }
  if (dir_name=="chronological") {
    const img0 =  "/resume_templates/chronological/chronological0.png";
    const img1 = "/resume_templates/chronological/chronological1.png";
    const img2 = "/resume_templates/functional/chronological2.png";
    const img0_thmb = "/resume_templates/chronological/chronological0_thmb.png";
    const img1_thmb = "/resume_templates/chronological/chronological1_thmb.png";
    const img2_thmb = "/resume_templates/chronological/chronological2_thmb.png";
    imgNode0.href = img0;
    imgNode1.href = img1;
    imgNode2.href = img2;
    imgThumb0.src = img0_thmb;
    imgThumb1.src = img1_thmb;
    imgThumb2.src = img2_thmb;

  }

  var cN = "active";
  var prev = 0;
  let imgs = document.querySelectorAll<HTMLImageElement>(".thumbnail");
  for (var i = 0; i < imgs.length; i += 1) {
    (function(i) {
      imgs[i].addEventListener("click", function() {
        imgs[prev].className="thumbnail";
        this.className === "thumbnail" ? this.className = cN : this.className = "thumbnail"; // Toggle class name
        prev = i;
        Streamlit.setComponentValue(i);
      });
    })(i);
    // Swap img.alt with li.innerHTML
    // var temp = list.innerHTML;
    // list.children[i].innerHTML = this.alt;
    // this.alt = temp;
  }
  
  // Show "Hello, name!" with a non-breaking space afterwards.
  // textNode.textContent = `Hello, ${img0}! ` + String.fromCharCode(160)
  // imgNode.setAttribute( 'src', `${img0}` );

  // imgNode.onclick = function(): void {
  //   modal.style.display = "block";
  //   modalImg.src = `${img0}`;
  //   // captionText.innerHTML = this.alt;
  //   Streamlit.setComponentValue(`${img0}`);
  // }


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
