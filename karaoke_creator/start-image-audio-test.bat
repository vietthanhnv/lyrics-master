@echo off
echo Starting Karaoke Server with Image+Audio Support...
echo.
echo Server will be available at:
echo - Main App: http://localhost:3000
echo - Server API: http://localhost:3001
echo - WebSocket: ws://localhost:3005
echo.
echo Test page available at:
echo - http://localhost:3000/test_image_audio.html
echo.

REM Start the server
cd server
start "Karaoke Server" cmd /k "npm start"

REM Wait a moment for server to start
timeout /t 3 /nobreak > nul

REM Start the client server
cd ..
start "Client Server" cmd /k "node serve_client.js"

echo.
echo Both servers started!
echo Press any key to open the application in your browser...
pause > nul

REM Open the application
start http://localhost:3000
start http://localhost:3000/test_image_audio.html

echo.
echo Application opened in browser.
echo Close this window when you're done testing.
pause