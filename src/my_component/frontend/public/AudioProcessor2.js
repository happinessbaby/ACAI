const sampleRate = 16000;

export default function sendAudio(stream) {
    var audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: sampleRate });
    var source = audioContext.createMediaStreamSource(stream);
    
    audioContext.audioWorklet.addModule('./pcmWorker.js')
        .then(() => {
            var pcmWorker = new AudioWorkletNode(audioContext, 'pcm-worker', {
                outputChannelCount: [1]
            });

            source.connect(pcmWorker);
            var conn = new WebSocket("ws://localhost:8080/ws/stt");

            pcmWorker.port.onmessage = (event) => conn.send(event.data);
            pcmWorker.port.start();
        })
        .catch(error => console.error("Error loading pcmWorker module:", error));
}