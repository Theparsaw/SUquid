import tkinter as tk
import socket
import threading
import time
import os  # Added for safe process termination

# Default question and options shown before the game starts
default_question = "What does CPU stand for?"
default_option_a = "Central Processing Unit"
default_option_b = "Core Parallel Unit"
default_option_c = "Central Program Utility"

# Widget references that need to be accessed across functions
scoreboard_names = None
scoreboard_scores = None
option_a_entry = None
option_b_entry = None
option_c_entry = None


def build_ui(root):
    global server_entry, port_entry, log_box, username_entry
    global question_box, selected_choice, scoreboard_names, scoreboard_scores
    global option_a_entry, option_b_entry, option_c_entry, response_box

    # Main window setup
    root.title("SUquid Quiz Games | Client")
    root.geometry("1000x800")  # Adjusted size for better default view

    # Grid layout configuration
    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)
    root.grid_columnconfigure(2, weight=1)
    root.grid_columnconfigure(3, weight=3)
    root.grid_columnconfigure(4, weight=1)
    root.grid_rowconfigure(8, weight=1)

    # Server connection inputs
    tk.Label(root, text="Server IP").grid(row=0, column=0, sticky="w", padx=20, pady=3)
    server_entry = tk.Entry(root, width=30)
    server_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=3)
    server_entry.insert(0, "127.0.0.1")

    tk.Label(root, text="Server Port").grid(row=1, column=0, sticky="w", padx=20, pady=3)
    port_entry = tk.Entry(root, width=30)
    port_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=3)
    port_entry.insert(0, "5004")

    tk.Label(root, text="Username").grid(row=2, column=0, sticky="w", padx=20, pady=3)
    username_entry = tk.Entry(root, width=30)
    username_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=3)

    # Connect button
    tk.Button(root, text="Connect to Server", command=connect).grid(
        row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=10
    )

    # Disconnect button
    tk.Button(root, text="Disconnect from Server", command=disconnect).grid(
        row=4, column=0, columnspan=2, sticky="ew", padx=20, pady=10
    )

    # Box used to show result feedback for the last answer
    response_box = tk.Text(root, height=5)
    tk.Label(root, text="Response").grid(
        row=5, column=0, columnspan=2, padx=20, pady=(10, 0)
    )
    response_box.grid(row=6, column=0, columnspan=2, sticky="nsew", padx=20)
    response_box.config(state=tk.DISABLED)

    # Log box used for general messages and server events
    tk.Label(root, text="LOG").grid(
        row=7, column=0, columnspan=6, sticky="ews", padx=20
    )
    log_box = tk.Text(root, width=46)
    log_box.grid(row=8, column=0, columnspan=6, sticky="nsew", padx=20)
    log_box.config(state=tk.DISABLED)

    # Question display area
    tk.Label(root, text="Question").grid(row=0, column=3, sticky="w", padx=20, pady=10)
    question_box = tk.Text(root, height=3, width=50, wrap=tk.WORD)
    question_box.insert(tk.END, default_question)
    question_box.grid(row=1, column=3, sticky="ew", padx=20, pady=10)
    question_box.config(state=tk.DISABLED)

    # Answer selection
    tk.Label(root, text="Select Your Answer:").grid(
        row=2, column=3, sticky="w", padx=20, pady=(10, 5)
    )

    # Tracks which option the user selected
    selected_choice = tk.StringVar(value="A")

    # Option A
    tk.Radiobutton(root, variable=selected_choice, value="A").grid(
        row=3, column=3, sticky="w", padx=20, pady=5
    )
    option_a_entry = tk.Entry(root, width=50)
    option_a_entry.insert(0, default_option_a)
    option_a_entry.grid(row=3, column=3, sticky="ew", padx=60, pady=5)
    option_a_entry.config(state="readonly")

    # Option B
    tk.Radiobutton(root, variable=selected_choice, value="B").grid(
        row=4, column=3, sticky="w", padx=20, pady=5
    )
    option_b_entry = tk.Entry(root, width=50)
    option_b_entry.insert(0, default_option_b)
    option_b_entry.grid(row=4, column=3, sticky="ew", padx=60, pady=5)
    option_b_entry.config(state="readonly")

    # Option C
    tk.Radiobutton(root, variable=selected_choice, value="C").grid(
        row=5, column=3, sticky="w", padx=20, pady=5
    )
    option_c_entry = tk.Entry(root, width=50)
    option_c_entry.insert(0, default_option_c)
    option_c_entry.grid(row=5, column=3, sticky="ew", padx=60, pady=5)
    option_c_entry.config(state="readonly")

    # Submit answer button
    tk.Button(root, text="Submit Answer", command=send_answer, height=2).grid(
        row=6, column=3, sticky="ew", padx=20, pady=15
    )

    # Scoreboard UI
    tk.Label(root, text="Scoreboard").grid(
        row=0, column=4, columnspan=2, sticky="ew", padx=20, pady=10
    )

    tk.Label(root, text="Username").grid(row=1, column=4, padx=(20, 5), pady=5)
    scoreboard_names = tk.Text(root, height=20, width=20)
    scoreboard_names.grid(row=2, column=4, rowspan=5, sticky="nsew", padx=(20, 5))
    scoreboard_names.config(state=tk.DISABLED)

    tk.Label(root, text="Score").grid(row=1, column=5, padx=(5, 20), pady=5)
    scoreboard_scores = tk.Text(root, height=20, width=10)
    scoreboard_scores.grid(row=2, column=5, rowspan=5, sticky="nsew", padx=(5, 20))
    scoreboard_scores.config(state=tk.DISABLED)


def update_response_box(text):
    # Shows feedback for the most recent answer
    response_box.config(state=tk.NORMAL)
    response_box.delete(1.0, tk.END)
    response_box.insert(tk.END, text + "\n")
    response_box.config(state=tk.DISABLED)


def connect():
    # Run connection logic in a background daemon thread
    t = threading.Thread(target=connect_worker)
    t.daemon = True
    t.start()


def connect_worker():
    global s, is_connected

    try:
        # Prevent double connections
        if is_connected:
            log_box.config(state=tk.NORMAL)
            log_box.insert("end", "Already connected! Please disconnect first.\n")
            log_box.config(state=tk.DISABLED)
            return

        IP = server_entry.get()
        Port = port_entry.get()

        log_box.config(state=tk.NORMAL)
        log_box.insert("end", "Connecting to the server ...\n")
        log_box.config(state=tk.DISABLED)

        # Create socket and connect
        s = socket.socket()
        s.settimeout(1.0)
        s.connect((IP, int(Port)))

        # Send username to server
        Username = username_entry.get()
        s.send((Username if Username else " ").encode())

        log_box.config(state=tk.NORMAL)
        log_box.insert("end", "Username sent to the server.\n")
        log_box.config(state=tk.DISABLED)

        # Mark as connected and start listening
        is_connected = True
        start_listen()

    except Exception as e:
        log_box.config(state=tk.NORMAL)
        log_box.insert("end", "Error encountered: " + str(e) + "\n")
        log_box.config(state=tk.DISABLED)


def send_answer():
    # Run sending logic in a background daemon thread
    t = threading.Thread(target=send_answer_worker)
    t.daemon = True
    t.start()


def send_answer_worker():
    global s, selected_choice, game_active

    try:
        if not is_connected:
            log_box.config(state=tk.NORMAL)
            log_box.insert("end", "Not connected to the server.\n")
            log_box.config(state=tk.DISABLED)
            return

        # Prevent sending answers before a question is active
        if not game_active:
            log_box.config(state=tk.NORMAL)
            log_box.insert("end", "Game not started yet. Answer not sent.\n")
            log_box.config(state=tk.DISABLED)
            return

        answer = selected_choice.get()
        s.send(f"ANSWER:{answer}".encode())

        log_box.config(state=tk.NORMAL)
        log_box.insert("end", "Answer sent: " + answer + "\n")
        log_box.config(state=tk.DISABLED)

    except Exception as e:
        log_box.config(state=tk.NORMAL)
        log_box.insert("end", "Error sending answer: " + str(e) + "\n")
        log_box.config(state=tk.DISABLED)


def update_scoreboard(message):
    global scoreboard_names, scoreboard_scores

    try:
        # Expected format:
        # SCOREBOARD:ranked_usernames_csv:score_csv
        parts = message.split(":")
        if len(parts) < 3:
            return

        usernames = parts[1].split(",") if parts[1] else []
        scores = parts[2].split(",") if parts[2] else []

        scoreboard_names.config(state=tk.NORMAL)
        scoreboard_scores.config(state=tk.NORMAL)
        scoreboard_names.delete(1.0, tk.END)
        scoreboard_scores.delete(1.0, tk.END)

        for i in range(min(len(usernames), len(scores))):
            scoreboard_names.insert(tk.END, usernames[i] + "\n")
            scoreboard_scores.insert(tk.END, scores[i] + "\n")

        scoreboard_names.config(state=tk.DISABLED)
        scoreboard_scores.config(state=tk.DISABLED)

    except Exception as e:
        log_box.config(state=tk.NORMAL)
        log_box.insert("end", "Error updating scoreboard: " + str(e) + "\n")
        log_box.config(state=tk.DISABLED)


def update_question(message):
    global question_box, option_a_entry, option_b_entry, option_c_entry

    try:
        # Expected format:
        # QUESTION:question_text:optionA:optionB:optionC
        parts = message.split(":")
        if len(parts) < 5:
            return

        question_box.config(state=tk.NORMAL)
        question_box.delete(1.0, tk.END)
        question_box.insert(tk.END, parts[1])
        question_box.config(state=tk.DISABLED)

        option_a_entry.config(state=tk.NORMAL)
        option_a_entry.delete(0, tk.END)
        option_a_entry.insert(0, parts[2])
        option_a_entry.config(state="readonly")

        option_b_entry.config(state=tk.NORMAL)
        option_b_entry.delete(0, tk.END)
        option_b_entry.insert(0, parts[3])
        option_b_entry.config(state="readonly")

        option_c_entry.config(state=tk.NORMAL)
        option_c_entry.delete(0, tk.END)
        option_c_entry.insert(0, parts[4])
        option_c_entry.config(state="readonly")

    except Exception as e:
        log_box.config(state=tk.NORMAL)
        log_box.insert("end", "Error updating question: " + str(e) + "\n")
        log_box.config(state=tk.DISABLED)


def start_listen():
    # Start socket listener in a background daemon thread
    t = threading.Thread(target=listen_worker)
    t.daemon = True
    t.start()


def handle_message(message):
    global is_connected, s, game_active

    # Scoreboard updates go straight to the UI
    if message.startswith("SCOREBOARD:"):
        update_scoreboard(message)
        return

    # New question message
    if message.startswith("QUESTION:"):
        update_question(message)
        game_active = True
        log_box.config(state=tk.NORMAL)
        log_box.insert("end", "New question received.\n")
        log_box.config(state=tk.DISABLED)
        return

    # Result feedback for the user's answer
    if message.startswith("RESULT:"):
        parts = message.split(":", 2)
        if len(parts) == 3:
            update_response_box(parts[2])
        return

    # Game already started rejection
    if message == "GAME_ALREADY_STARTED":
        log_box.config(state=tk.NORMAL)
        log_box.insert("end", "Connection rejected: game already started.\n")
        log_box.config(state=tk.DISABLED)
        is_connected = False
        s.close()
        return

    # Game end notification
    if message == "GAMEOVER":
        log_box.config(state=tk.NORMAL)
        log_box.insert("end", "Game over.\n")
        log_box.config(state=tk.DISABLED)
        game_active = False
        return

    # Player left notification
    if message.startswith("USER_LEFT:"):
        name = message.split(":", 1)[1]
        log_box.config(state=tk.NORMAL)
        log_box.insert("end", f"{name} left the game.\n")
        log_box.config(state=tk.DISABLED)
        return

    # Successful connection message
    if message.startswith("Welcome,"):
        log_box.config(state=tk.NORMAL)
        log_box.insert("end", "Connected successfully!\n")
        log_box.config(state=tk.DISABLED)
        return

    # Username validation errors
    if message in [
        "The name cannot be empty!",
        f"The name {username_entry.get().strip().lower()} already exists!",
    ]:
        log_box.config(state=tk.NORMAL)
        log_box.insert("end", message + "\n")
        log_box.config(state=tk.DISABLED)
        is_connected = False
        s.close()
        return

    # Answer timing errors
    if message == "ERROR:GAME_NOT_STARTED":
        log_box.config(state=tk.NORMAL)
        log_box.insert("end", "You tried to answer before the game started.\n")
        log_box.config(state=tk.DISABLED)
        return

    if message == "ERROR:NO_ACTIVE_QUESTION":
        log_box.config(state=tk.NORMAL)
        log_box.insert("end", "You tried to answer with no active question.\n")
        log_box.config(state=tk.DISABLED)
        return

    # Server disconnect or socket error
    if message.startswith("Connection error") or message == "Server closed the connection.":
        log_box.config(state=tk.NORMAL)
        log_box.insert("end", message + "\n")
        log_box.config(state=tk.DISABLED)
        is_connected = False
        try:
            s.close()
        except:
            pass
        return

    # Fallback: log anything unexpected
    log_box.config(state=tk.NORMAL)
    log_box.insert("end", message + "\n")
    log_box.config(state=tk.DISABLED)


def listen_worker():
    global s, is_connected, recv_buf

    # Continuously read from the socket while connected
    while is_connected:
        try:
            chunk = s.recv(1024).decode()
            if not chunk:
                handle_message("Server closed the connection.")
                is_connected = False
                s.close()
                break

            recv_buf += chunk

            # Process full newline-delimited messages
            while "\n" in recv_buf:
                message, recv_buf = recv_buf.split("\n", 1)
                handle_message(message.strip())

        except socket.timeout:
            continue
        except Exception as e:
            if is_connected:
                handle_message(f"Connection error: {e}")
            is_connected = False
            try:
                s.close()
            except:
                pass
            break


def disconnect():
    # Run disconnect logic in background daemon thread
    t = threading.Thread(target=disconnect_worker)
    t.daemon = True
    t.start()


def disconnect_worker():
    global s, is_connected

    try:
        if not is_connected:
            log_box.config(state=tk.NORMAL)
            log_box.insert("end", "Not connected to the server.\n")
            log_box.config(state=tk.DISABLED)
            return

        # Stop listener and close socket
        is_connected = False
        time.sleep(0.1)
        s.close()

        # Clear scoreboard UI
        scoreboard_names.config(state=tk.NORMAL)
        scoreboard_names.delete(1.0, tk.END)
        scoreboard_names.config(state=tk.DISABLED)

        scoreboard_scores.config(state=tk.NORMAL)
        scoreboard_scores.delete(1.0, tk.END)
        scoreboard_scores.config(state=tk.DISABLED)

        log_box.config(state=tk.NORMAL)
        log_box.insert("end", "Disconnected from the server.\n")
        log_box.config(state=tk.DISABLED)

    except Exception as e:
        log_box.config(state=tk.NORMAL)
        log_box.insert("end", "Error disconnecting: " + str(e) + "\n")
        log_box.config(state=tk.DISABLED)
        is_connected = False


def receive_scoreboard():
    # Intentionally unused
    pass

def on_closing():
    # Ensures all threads die when the window is closed
    global is_connected
    is_connected = False
    try:
        s.close()
    except:
        pass
    root.destroy()
    os._exit(0)  # Force exit to kill background threads


# Connection and game state flags
is_connected = False
game_active = False

# Buffer used to accumulate partial socket messages
recv_buf = ""

root = tk.Tk()
build_ui(root)
root.protocol("WM_DELETE_WINDOW", on_closing)  # Bind the close handler
root.mainloop()