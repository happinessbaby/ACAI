// Establish WebSocket connection
const port = 'ws://localhost:8765'
export function init_audioReceiver() {
  const socket = new WebSocket(port);

  // WebSocket event handlers
  socket.onopen = () => {
    console.log(`WebSocket connection established for port: ${port}`);
  };

  socket.onmessage = (event) => {
    const receivedMessage = event.data;
    console.log('Received AI response from server:', receivedMessage);

    // Update HTML element with the received message
    updateSpeechContent(receivedMessage, "Luke")
  };

  socket.onclose = (event) => {
    // console.log('WebSocket connection closed');
    if (event.wasClean) {
      console.log(`WebSocket connection closed cleanly, code=${event.code}, reason=${event.reason}`);
    } else {
      console.error(`Connection abruptly closed for port: ${port}`);
    }
  };
}

// Define an event that will be triggered when content is updated
const speechContentUpdatedEvent = new Event('speechContentUpdated');

function updateSpeechContent(newContent, name) {
    // Get the <speak> element by its ID
    const speechElement = document.getElementsByClassName(`textEntry ${name}`)[0];
    // if (!speechElement) {
    //     console.error('Element with ID "textEntry ${name}" not found.');
    //     return;
    //   }
    // Update the innerHTML of the <speak> element with the new content
    speechElement.value = `<amazon:domain name="conversational">${newContent}</amazon:domain>`;
    // Dispatch the event when content is updated
    speechElement.dispatchEvent(speechContentUpdatedEvent);
    console.log("Dispatched textentry updating event");
  }


  // Make the updateSpeechContent function available globally
// window.updateSpeechContent = updateSpeechContent;


  
