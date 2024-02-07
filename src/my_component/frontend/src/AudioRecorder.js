//API to handle audio recording
 
function startAudioRecording() {
    //start recording using the audio recording API
    audioRecorder.start()
        .then(() => { //on success
            console.log("Recording Audio...")    
        })    
        .catch(error => { //on error
            //No Browser Support Error
            if (error.message.includes("mediaDevices API or getUserMedia method is not supported in this browser.")) {       
                console.log("To record audio, use browsers like Chrome and Firefox.");
            }
        });
}
var audioRecorder = {
    /** Stores the recorded audio as Blob objects of audio data as the recording continues*/
    audioBlobs: [], /*of type Blob[]*/
    /** Stores the reference of the MediaRecorder instance that handles the MediaStream when recording starts*/
    mediaRecorder: null, /*of type MediaRecorder*/
    /** Stores the reference to the stream currently capturing the audio*/
    streamBeingCaptured: null, /*of type MediaStream*/
    /** Start recording the audio
      * @returns {Promise} - returns a promise that resolves if audio recording successfully started
      */
    start: function () {
         //Feature Detection
         if (!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)) {
            //Feature is not supported in browser
            //return a custom error
            return Promise.reject(new Error('mediaDevices API or getUserMedia method is not supported in this browser.'));
        }
        else {
            //Feature is supported in browser
             
            //create an audio stream
            return navigator.mediaDevices.getUserMedia({ audio: true }/*of type MediaStreamConstraints*/)
                //returns a promise that resolves to the audio stream
                .then(stream /*of type MediaStream*/ => {
                     
                    //save the reference of the stream to be able to stop it when necessary
                     audioRecorder.streamBeingCaptured = stream;

                    //create a media recorder instance by passing that stream into the MediaRecorder constructor
                    audioRecorder.mediaRecorder = new MediaRecorder(stream); /*the MediaRecorder interface of the MediaStream Recording
                    API provides functionality to easily record media*/

                    //clear previously saved audio Blobs, if any
                    audioRecorder.audioBlobs = [];

                    //add a dataavailable event listener in order to store the audio data Blobs when recording
                    audioRecorder.mediaRecorder.addEventListener("dataavailable", event => {
                        //store audio Blob object
                        audioRecorder.audioBlobs.push(event.data);
                    });

                    //start the recording by calling the start method on the media recorder
                    audioRecorder.mediaRecorder.start();
            });
        }

    //...
    },
    /** Stop the started audio recording
      * @returns {Promise} - returns a promise that resolves to the audio as a blob file
      */
    stop: function () {
    //...
    },
    /** Cancel audio recording*/
    cancel: function () {
    //...
    }
}