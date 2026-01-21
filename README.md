# Squid Quiz Games 🦑🎮  
CS408 – Computer Networks Course Project

Squid Quiz Games is a TCP-based multiplayer quiz game with graphical user interfaces for both the server and the clients. Multiple players connect to a central server, answer multiple-choice questions in real time, earn points based on correctness and speed, and compete on a live scoreboard.

---

## Features

### Server
- TCP socket–based server supporting multiple simultaneous clients
- GUI for configuring IP, port, question file, and number of questions
- Real-time event logging
- Live scoreboard with ranking and tie handling
- Automatic winner announcement at game end
- Graceful handling of client disconnections and server shutdown

### Client
- GUI-based client application
- Connects to server using IP, port, and username
- Displays current question, answer options, and live scoreboard
- Personalized feedback for each submitted answer
- Server and game event logging
- Safe connect and disconnect functionality

---

## How to Run

### Requirements
- Python 3.x
- Uses only Python standard libraries (no external dependencies)

---

### Start the Server

Run the server file:

python m.talebibarmi_Talebibarmi_Mohammadparsa_server.py

Steps:
1. Enter server IP and port
2. Select a valid question file
3. Set the number of questions
4. Click Start Listening
5. Wait for at least 2 clients
6. Click Start Game

---

### Start a Client

Run the client file:

python m.talebibarmi_Talebibarmi_Mohammadparsa_client.py

Steps:
1. Enter server IP and port
2. Choose a unique username
3. Connect and wait for the game to start

---

## Question File Format

Each question must consist of 5 consecutive lines:

Question text  
Option A  
Option B  
Option C  
Answer: A  

Rules:
- No blank lines between questions
- The server cycles through questions if the requested count exceeds the file size

---

## Technical Details

- TCP socket communication with newline-delimited messages
- Multi-threaded server for handling multiple clients
- Thread-safe shared state using locks and queues
- GUI updates safely handled from background threads
- Robust error handling for invalid actions and disconnections

---

## Author

Mohammadparsa Talebibarmi

---

## License

MIT License

Copyright (c) 2025 Borhan 

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
