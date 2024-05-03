// Establish WebSocket connection
const port = 'ws://localhost:8765'
export function init_audioReceiver() {
  const socket = new WebSocket(port);

  // WebSocket event handlers
  socket.onopen = () => {
    console.log(`WebSocket connection established for port: ${port}`);
  };

  socket.onmessage = (event) => {
      
    const receivedMessage = JSON.parse(event.data);
    console.log('Received AI response from server:', receivedMessage);

    // Update HTML element with the received message
    updateSpeechContent(receivedMessage)
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

export function updateSpeechContent(newContent) {
    // Get the <speak> element by its ID
    const interviewerSpeechElement = document.getElementsByClassName('textEntry Interviewer')[0];
    const graderSpeechElement = document.getElementsByClassName('textEntry Grader')[0];
    // Update the innerHTML of the <speak> element with the new content
    // speechElement.value = `<amazon:domain name="conversational">${newContent}</amazon:domain>`;
    interviewerSpeechElement.value = newContent.interviewer;
    graderSpeechElement.value = newContent.grader;
    // Dispatch the event when content is updated
    interviewerSpeechElement.dispatchEvent(speechContentUpdatedEvent);
    graderSpeechElement.dispatchEvent(speechContentUpdatedEvent);
    console.log("Dispatched textentry updating event");
  }




  
