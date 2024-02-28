// Establish WebSocket connection
export function init_audioReceiver() {
  const socket = new WebSocket('ws://localhost:8765');

  // WebSocket event handlers
  socket.onopen = () => {
    console.log('WebSocket connection established');
  };

  socket.onmessage = (event) => {
  console.log("tsrdyfugiogygcfgjh");
    const receivedMessage = event.data;
    console.log('Received message from server:', receivedMessage);

    // Update HTML element with the received message
    updateSpeechContent(receivedMessage, "Luke")
  };

  socket.onclose = (event) => {
    // console.log('WebSocket connection closed');
    if (event.wasClean) {
      console.log(`WebSocket connection closed cleanly, code=${event.code}, reason=${event.reason}`);
    } else {
      console.error('Connection abruptly closed');
    }
  };
}

// Define an event that will be triggered when content is updated
const speechContentUpdatedEvent = new Event('speechContentUpdated');

function updateSpeechContent(newContent, name) {
    // Get the <speak> element by its ID
    const speechElement = document.getElementsByClassName(`textEntry ${name}`)[0];
    if (!speechElement) {
        console.error('Element with ID "textEntry ${name}" not found.');
        return;
      }
    console.log("update speech")
    
    // Update the innerHTML of the <speak> element with the new content
    speechElement.value = `<amazon:domain name="conversational">${newContent}</amazon:domain>`;
    // Dispatch the event when content is updated
    speechElement.dispatchEvent(speechContentUpdatedEvent);
    console.log("Dispatched updated speech event");
  }


  // Make the updateSpeechContent function available globally
// window.updateSpeechContent = updateSpeechContent;


  
