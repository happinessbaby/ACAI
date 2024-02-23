// let audioRecorder = {
//     audioBlobs: [],
//     mediaRecorder: null,
//     streamBeingCaptured: null,
//     start: null,  // Declare the start function, will be assigned later
//     stop: null,
//     resetStream: null,
//     resetRecordingProperties: null,
//     handleSucess: null,
// };

// Create a promise that resolves when the start function is assigned
// const startFunctionPromise = new Promise((resolve) => {
//     audioRecorder.startResolver = resolve;
// });

// const stopFunctionPromise = new Promise((resolve) => {
//     audioRecorder.stopResolver = resolve;
// });


// require(['./@google-cloud/speech'], async (speech) => {
    // var speech = require('@google-cloud/speech'); 
//   var app = express()
    // });
// const speech = require('@google-cloud/speech');
const sampleRate = 16000;
  // initialize stt parameters
  // need a 16-bit, 16KHz raw PCM audio 
// const encoding = 'LINEAR16';
// const sampleRateHertz = 16000;
// const languageCode = 'en-US';
// const request = {
// config: {
//     encoding: encoding,
//     sampleRateHertz: sampleRateHertz,
//     languageCode: languageCode,
// },
// interimResults: false // If you want interim results, set this to true
// };
// // init SpeechClient
// const client = new speech.v1p1beta1.SpeechClient();
// await client.initialize();
// const stt_stream = await client.streamingRecognize(request);
const getMediaStream = () =>
  navigator.mediaDevices.getUserMedia({
    audio: {
      deviceId: "default",
      sampleRate: sampleRate,
      sampleSize: 16,
      channelCount: 1
    },
    video: false
  });

const loadPCMWorker = (audioContext) =>
  audioContext.audioWorklet.addModule('/pcmWorker.js')






var audioRecorder = {
    /** Stores the recorded audio as Blob objects of audio data as the recording continues*/
    // audioBlobs: [], /*of type Blob[]*/
    /** Stores the reference of the MediaRecorder instance that handles the MediaStream when recording starts*/
    // mediaRecorder: null, /*of type MediaRecorder*/
    /** Stores the reference to the stream currently capturing the audio*/
    streamBeingCaptured: null, /*of type MediaStream*/

    connection: null, 

    audioContext: null,
    /** Start recording the audio
      * @returns {Promise} - returns a promise that resolves if audio recording successfully started
      */
    startRecording: function () {
         //Feature Detection
        //  if (!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)) {
        //     //Feature is not supported in browser
        //     //return a custom error
        //     return Promise.reject(new Error('mediaDevices API or getUserMedia method is not supported in this browser.'));
        // }
        audioRecorder.connect();

        //Feature is supported in browser         
        //create an audio stream
        audioRecorder.audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: sampleRate });
        // audioRecorder.createAudioContext();
        // audioRecorder.audioContext = audioContext;
        return Promise.all([loadPCMWorker(audioRecorder.audioContext), getMediaStream(), ])
            .then(([_, stream, ]) => audioRecorder.handleSuccess(audioRecorder.audioContext, stream, data => audioRecorder.connection.send(data)))
            .catch(error=> {    console.error("Error in Promise.all:", error);})
            ;
                //returns a promise that resolves to the audio stream
                // .then(stream /*of type MediaStream*/ => {
              
                    // //create a media recorder instance by passing that stream into the MediaRecorder constructor
                    // audioRecorder.mediaRecorder = new MediaRecorder(stream); /*the MediaRecorder interface of the MediaStream Recording
                    // API provides functionality to easily record media*/

                    // //clear previously saved audio Blobs, if any
                    // audioRecorder.audioBlobs = [];

                    // //add a dataavailable event listener in order to store the audio data Blobs when recording
                    // audioRecorder.mediaRecorder.addEventListener("dataavailable", event => {
                    //     //store audio Blob object
                    //     audioRecorder.audioBlobs.push(event.data);
                    // });

                    // //start the recording by calling the start method on the media recorder
                    // audioRecorder.mediaRecorder.start();
            // });


    //...
    },
    /** Stop the started audio recording
      * @returns {Promise} - returns a promise that resolves to the audio as a blob file
      */
    stopRecording: function () {
        // return new Promise(resolve => {
        //     stt_stream.on('data', data => {
        //         const result = data.results[0];
        //         console.log(`SR results, final: ${result.isFinal}, text: ${result.alternatives[0].transcript}`);
        //       });
        //     resolve(result)
            //save audio type to pass to set the Blob type
            // let mimeType = audioRecorder.mediaRecorder.mimeType;
 
            // //listen to the stop event in order to create & return a single Blob object
            // audioRecorder.mediaRecorder.addEventListener("stop", () => {
            //     //create a single blob object, as we might have gathered a few Blob objects that needs to be joined as one
            //     let audioBlob = new Blob(audioRecorder.audioBlobs, { type: mimeType });
 
            //     //resolve promise with the single audio blob representing the recorded audio
            //     resolve(audioBlob);
            // });
 
        //stop the recording feature
        // audioRecorder.mediaRecorder.stop();
        // audioRecorder.disconnect();
 
        //stop all the tracks on the active stream in order to stop the stream
        audioRecorder.stopStream();
 
        //reset API properties for next recording
        audioRecorder.resetRecordingProperties();

        // })

        // audioRecorder.stopResolver();
        
    //...
    },
        /** Stop all the tracks on the active stream in order to stop the stream and remove
     * the red flashing dot showing in the tab
     */

    connect: function() {
            // audioRecorder.connection?.close();
            if (audioRecorder.connection == null) {
              // Check if the connection is closed or if it is null
              audioRecorder.connection = new WebSocket("ws://localhost:8000");
              // connection.onmessage = event => speechRecognized(JSON.parse(event.data));
              audioRecorder.connection.onopen = event => {
                  // Send a JSON message to the server with specific parameters
                  // audioRecorder.connection.send(JSON.stringify({
                  //     "rate": 16000,
                  //     "format": 'LINEAR16',
                  //     "language": 'en-US',
                  // }));
                  this.send(JSON.stringify({
                      "rate": 16000,
                      "format": 'LINEAR16',
                      "language": 'en-US',
                  }));
              console.log("WebSocket connection state after sending message:", audioRecorder.connection.readyState);           
              }; 
              audioRecorder.connection.onerror = event => {
                  console.error("WebSocket error:", event.error);
              };
              audioRecorder.connection.onmessage = event => {
                  console.log("websocket received msg", event.data);
              }
            }
            else {
              console.log("webscoket already established", audioRecorder.connection.readyState)
            }
            // audioRecorder.connection = connection;

            console.log("connected to websocket")
          },
    // disconnect: function() {
    //     console.log("disconnecting:", audioRecorder.connection.readyState)
    //     audioRecorder.connection?.close();
    //     audioRecorder.connection = null;
    // },

    send: function (message, callback) {
        this.waitForConnection(function () {
            audioRecorder.connection.send(message);
            if (typeof callback !== 'undefined') {
              callback();
            }
        }, 1000);
    },
    
    waitForConnection: function (callback, interval) {
        if (audioRecorder.connection.readyState === 1) {
            callback();
        } else {
            var that = this;
            // optional: implement backoff for interval here
            setTimeout(function () {
                that.waitForConnection(callback, interval);
            }, interval);
        }
    },
        
    stopStream: function() {
            //stopping the capturing request by stopping all the tracks on the active stream
            if (audioRecorder.streamBeingCaptured != null) {
            audioRecorder.streamBeingCaptured.getTracks() //get all tracks from the stream
                    .forEach(track /*of type MediaStreamTrack*/ => track.stop()); //stop each one
            }
            if (audioRecorder.audioContext != null) {
                audioRecorder.audioContext.close();
            }
        },
        /** Reset all the recording properties including the media recorder and stream being captured*/
    resetRecordingProperties: function () {
            // audioRecorder.audioContext = null;
            audioRecorder.streamBeingCaptured = null;
     
            /*No need to remove event listeners attached to mediaRecorder as
            If a DOM element which is removed is reference-free (no references pointing to it), the element itself is picked
            up by the garbage collector as well as any event handlers/listeners associated with it.
            getEventListeners(audioRecorder.mediaRecorder) will return an empty array of events.*/
    },

    createAudioContext: function () {
      if (audioRecorder.audioContext==null) {
        audioRecorder.audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: sampleRate });
      }
    },

    sendConfig: function() {
        return new Promise((resolve, reject) => {
          if (audioRecorder.connection.readyState === WebSocket.OPEN) {
            // resolve(true);
            this.send(JSON.stringify({
              "rate": 16000,
              "format": 'LINEAR16',
              "language": 'en-US',
            }), (error) => {
              if (error) {
                reject(error);
              } else {
                resolve('JSON config sent successfully');
              }
            });
          // } else if (
          //   audioRecorder.connection.readyState === WebSocket.CONNECTING ||
          //   audioRecorder.connection.readyState === WebSocket.CLOSING
          // ) {
          //   // If the WebSocket is still connecting or closing, wait for it to be open
          //   // websocket.addEventListener('open', () => {
          //   //   resolve(true);
          //   // });
      
          //   // If the WebSocket encounters an error, reject the promise
          //   // audioRecorder.connection.addEventListener('error', (error) => {
          //   //   reject(error);
          //   // });
          } else {
            // resolve(false);
            reject('WebSocket connection is not open.');
          }
        });
      },
    
    handleSuccess: function(audioContext, stream, output) {
        // //save the reference of the stream to be able to stop it when necessary
        console.log("successfully initiated audio contect, pcmMaker, and stream")
        audioRecorder.streamBeingCaptured = stream;
        
        // var audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: sampleRate });
        // audioRecorder.audioContext = audioContext;
        var source = audioContext.createMediaStreamSource(stream);     
        // audioContext.audioWorklet.addModule('./pcmWorker.js')
            // .then(() => {
                var pcmWorker = new AudioWorkletNode(audioContext, 'pcm-worker', {
                    outputChannelCount: [1]
                });
    
                source.connect(pcmWorker);
                // pcmWorker.port.onmessage = (event) => conn.send(event.data);
                // pcmWorker.port.onmessage = (event) => output(event.data)       
                pcmWorker.port.onmessage = (event) => output(event.data)
                // pcmWorker.port.onmessage = (event) => stt_stream.write(event.data)
                pcmWorker.port.start();
                console.log("ALL SUCCESSFUL")

            // })
            // .catch(error => console.error("Error loading pcmWorker module:", error));

    },
    // /** Cancel audio recording*/
    // cancel: function () {
    // //...
    // }
}

// });

export function init_audioRecorder() {
    return audioRecorder
}


