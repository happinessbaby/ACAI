// Create a new WebSocket server
console.log("STARTED MESSAGE RECEIVER")
var WebSocketServer = require('websocket').server;
var http = require('http');


var server = http.createServer(function(request, response) {
    // Not important for this example
});

server.listen(8765, function() {
    console.log('Server is listening on port 8765');
});

// Create a new WebSocket server
var wsServer = new WebSocketServer({
    httpServer: server
});

// Store all connected clients
const clients = [];

// Handle WebSocket connections
wsServer.on('request', function(request) {
    var connection = request.accept(null, request.origin);

    // Send a greeting to the client
    // connection.sendUTF('Greetings to the client!');

      // Add the connection to the list of clients
    clients.push(connection);

    // Listen for messages from the client
    connection.on('message', function(message) {
      
        console.log('Received message from client: ' + message.utf8Data);

        // Send a response to the client
        // connection.sendUTF('Echo: ' + message.utf8Data);
          // Broadcast the message to all connected clients
        broadcast(message.utf8Data);
    });

   // Handle connection close
   connection.on('close', function(reasonCode, description) {
    console.log('Client has disconnected');
    
    // Remove the connection from the list of clients
    const index = clients.indexOf(connection);
    if (index !== -1) {
      clients.splice(index, 1);
    }
  });

});


// Function to broadcast a message to all connected clients
function broadcast(message) {
    clients.forEach(function(client) {
      client.sendUTF(message);
    });
  }