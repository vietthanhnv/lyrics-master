#!/bin/bash

echo "Starting Karaoke Server with Image+Audio Support..."
echo ""
echo "Server will be available at:"
echo "- Main App: http://localhost:3000"
echo "- Server API: http://localhost:3001"
echo "- WebSocket: ws://localhost:3005"
echo ""
echo "Test page available at:"
echo "- http://localhost:3000/test_image_audio.html"
echo ""

# Start the server in background
cd server
npm start &
SERVER_PID=$!

# Wait for server to start
sleep 3

# Start the client server in background
cd ..
node serve_client.js &
CLIENT_PID=$!

echo ""
echo "Both servers started!"
echo "Server PID: $SERVER_PID"
echo "Client PID: $CLIENT_PID"
echo ""

# Open the application (works on macOS and some Linux distributions)
if command -v open > /dev/null; then
    open http://localhost:3000
    open http://localhost:3000/test_image_audio.html
elif command -v xdg-open > /dev/null; then
    xdg-open http://localhost:3000
    xdg-open http://localhost:3000/test_image_audio.html
else
    echo "Please open http://localhost:3000 in your browser"
    echo "And test the new feature at http://localhost:3000/test_image_audio.html"
fi

echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for interrupt
trap "kill $SERVER_PID $CLIENT_PID; exit" INT
wait