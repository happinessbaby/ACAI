import fs from 'fs';
import path from "path";
import url from 'url'; 
import util from "util";
import timers from 'timers/promises';
import speech from '@google-cloud/speech';

export {}

// need a 16-bit, 16KHz raw PCM audio 
const filename = path.join(path.dirname(url.fileURLToPath(import.meta.url)), "sample.raw");
const encoding = 'LINEAR16';
const sampleRateHertz = 16000;
const languageCode = 'en-US';

const request = {
  config: {
    encoding: encoding,
    sampleRateHertz: sampleRateHertz,
    languageCode: languageCode,
  },
  interimResults: false // If you want interim results, set this to true
};

// init SpeechClient
const client = new speech.v1p1beta1.SpeechClient();
await client.initialize();

// Stream the audio to the Google Cloud Speech API
const stream = client.streamingRecognize(request);

// log all data
stream.on('data', data => {
  const result = data.results[0];
  console.log(`SR results, final: ${result.isFinal}, text: ${result.alternatives[0].transcript}`);
});

// log all errors
stream.on('error', error => {
  console.warn(`SR error: ${error.message}`);
});

// observe data event
const dataPromise = new Promise(resolve => stream.once('data', resolve));

// observe error event
const errorPromise = new Promise((resolve, reject) => stream.once('error', reject));

// observe finish event
const finishPromise = new Promise(resolve => stream.once('finish', resolve));

// observe close event
const closePromise = new Promise(resolve => stream.once('close', resolve));

// we could just pipe it: 
// fs.createReadStream(filename).pipe(stream);
// but we want to simulate the web socket data

// read RAW audio as Buffer
const data = await fs.promises.readFile(filename, null);

// simulate multiple audio chunks
console.log("Writting...");
const chunkSize = 4096;
for (let i = 0; i < data.length; i += chunkSize) {
  stream.write(data.slice(i, i + chunkSize));
  await timers.setTimeout(50);
}
console.log("Done writing.");

console.log("Before ending...");
await util.promisify(c => stream.end(c))();
console.log("After ending.");

// race for events
await Promise.race([
  errorPromise.catch(() => console.log("error")), 
  dataPromise.then(() => console.log("data")),
  closePromise.then(() => console.log("close")),
  finishPromise.then(() => console.log("finish"))
]);

console.log("Destroying...");
stream.destroy();
console.log("Final timeout...");
await timers.setTimeout(1000);
console.log("Exiting.");