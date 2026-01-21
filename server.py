# Required Libraries
import socket
import threading
import tkinter as tk
import queue
import time

# Shared state used across threads and UI callbacks
global username, players, player_scores, game_running, game_roster, game_ending
global server_sock, shutdown_flag, questions, round_scores

# Lock used to protect shared data structures accessed by multiple threads
lock = threading.Lock()

# Flags tracking game and server state
game_running = False
game_ending = False

# Set of players who were present when the game started
game_roster = set()

# Server socket reference so it can be closed cleanly on shutdown
server_sock = None

# Event used to signal threads to stop
shutdown_flag = threading.Event()

# Loaded questions from file
questions = []

# Player-related state
username = ""
players = {}                 # username -> socket
player_scores = {}           # username -> total score
round_scores = {}            # username -> score for current question
answers_by_player = {}       # username -> list of answers
answers_count = 0
answered_players = []        # usernames who already answered current question
correct_players = []         # usernames who answered correctly

# Queue used to safely update the UI from background threads
ui_queue = queue.Queue()


def build_ui(root):
    global ip, port, ip_entry, port_entry, question_count_entry
    global file_path_entry, log_box, scoreboard_scores, scoreboard_names

    # Basic window configuration
    root.title("SUquid Quiz Games | Server")

    root.grid_columnconfigure(0, weight=0)
    root.grid_columnconfigure(1, weight=1)
    root.grid_columnconfigure(2, weight=3)
    root.grid_rowconfigure(5, weight=1)

    # Number of questions input
    question_count_label = tk.Label(root, text="Number of Questions")
    question_count_label.grid(row=0, column=0, sticky="w", padx=10, pady=10)
    question_count_entry = tk.Entry(root, width=30)
    question_count_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=10)

    # Question file path input
    file_path_label = tk.Label(root, text="Question File Path")
    file_path_label.grid(row=1, column=0, sticky="w", padx=10, pady=10)
    file_path_entry = tk.Entry(root, width=30)
    file_path_entry.insert(0, "quiz_qa.txt")
    file_path_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=10)

    # Port input
    port_label = tk.Label(root, text="Port Number")
    port_label.grid(row=2, column=0, sticky="w", padx=10, pady=10)
    port_entry = tk.Entry(root, width=30)
    port_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=10)
    port_entry.insert(0, "5004")

    # IP input
    ip_label = tk.Label(root, text="IP")
    ip_label.grid(row=3, column=0, sticky="w", padx=10, pady=10)
    ip_entry = tk.Entry(root, width=30)
    ip_entry.grid(row=3, column=1, sticky="ew", padx=10, pady=10)
    ip_entry.insert(0, "127.0.0.1")

    # Buttons for server and game control
    button_frame = tk.Frame(root)
    button_frame.grid(row=4, column=0, columnspan=2, pady=20)

    start_listening_button = tk.Button(
        button_frame, text="Start Listening", command=start_server, width=15
    )
    start_listening_button.pack(side=tk.LEFT, padx=5)

    start_game_button = tk.Button(
        button_frame, text="Start Game", command=start_game, width=15
    )
    start_game_button.pack(side=tk.LEFT, padx=5)

    filepath_button = tk.Button(
        button_frame, text="Open File", command=load_questions, width=15
    )
    filepath_button.pack(side=tk.RIGHT, padx=5)

    # Log box showing server events
    log_box = tk.Text(root, height=15)
    log_box.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
    log_box.insert(tk.END, "Event Log\n")
    log_box.config(state=tk.DISABLED)

    # Scoreboard UI
    tk.Label(root, text="Username").grid(row=1, column=4, sticky="ew", padx=20, pady=5)
    scoreboard_names = tk.Text(root, height=30, width=20)
    scoreboard_names.grid(row=2, column=4, rowspan=4, sticky="nsew", padx=20, pady=10)
    scoreboard_names.config(state=tk.DISABLED)

    tk.Label(root, text="Score").grid(row=1, column=5, sticky="ew", padx=20, pady=5)
    scoreboard_scores = tk.Text(root, height=30, width=15)
    scoreboard_scores.grid(row=2, column=5, rowspan=4, sticky="nsew", padx=20, pady=10)
    scoreboard_scores.config(state=tk.DISABLED)

    # Background thread that pulls messages from the queue and updates the UI
    queue_thread = threading.Thread(target=ui_queue_worker, daemon=True)
    queue_thread.start()

    # Clean shutdown when window is closed
    root.protocol("WM_DELETE_WINDOW", handle_close)
    root.mainloop()


def load_questions():
    global questions

    # Read number of questions requested
    try:
        question_count = int(question_count_entry.get())
    except ValueError:
        ui_queue.put("Enter a valid number of questions.")
        return []

    file_path = file_path_entry.get()
    if not file_path.strip():
        ui_queue.put("Enter a valid question file path.")
        return []

    try:
        # Read non-empty lines from file
        with open(file_path, encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            log_event(f"File {file_path} opened successfully.")

        questions = []
        total_questions_in_file = len(lines) // 5

        # Cycle through file if fewer questions than requested
        for q in range(question_count):
            index = (q % total_questions_in_file) * 5
            questions.append({
                "question": lines[index],
                "A": lines[index + 1],
                "B": lines[index + 2],
                "C": lines[index + 3],
                "Answer": lines[index + 4],
            })

        return questions

    except IOError:
        ui_queue.put(f"Could not read the file {file_path}")
        return []


def start_game():

    global game_running

    with lock:
        if game_running:
            ui_queue.put("A game is already in progress! Please wait for it to finish.")
            return
        
    try:
        question_count = int(question_count_entry.get().strip())
        if question_count <= 0:
            raise ValueError
    except ValueError:
        ui_queue.put("Enter a valid number of questions before starting.")
        return

    if not file_path_entry.get().strip():
        ui_queue.put("Enter a question file path before starting.")
        return

    refreshed_questions = load_questions()
    
    if not refreshed_questions:
        ui_queue.put("Failed to load questions. Check your file path and format.")
        return

    with lock:
        if len(players) < 2:
            ui_queue.put("Need at least 2 players to start the game.")
            return

    # Run the game loop in a separate thread
    threading.Thread(target=run_game).start()


def close_all_clients():
    # Close all client sockets safely
    for conn in players.values():
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except:
            pass
        try:
            conn.close()
        except:
            pass


def finish_game(reason=None):
    global game_running, game_ending, game_roster, round_scores

    # Prevent multiple finish calls
    if game_ending:
        return
    game_ending = True

    if reason:
        ui_queue.put(reason)

    #Explicit Winner Announcement 
    max_score = -1
    winners = []
    
    # Calculate max score
    for p in players:
        score = player_scores.get(p, 0)
        if score > max_score:
            max_score = score
            winners = [p]
        elif score == max_score:
            winners.append(p)
    
    # Create winner message
    if winners:
        winner_str = ", ".join(winners)
        announcement = f"The winner(s): {winner_str} with {max_score} points!"
    else:
        announcement = "No winners."
        
    ui_queue.put(announcement)

    # Notify clients that the game is over and who won
    for user, conn in list(players.items()):
        try:
            # Send winner announcement first so it appears in log
            conn.sendall(f"{announcement}\n".encode())
            conn.sendall("GAMEOVER\n".encode())
            # Ensure the socket is properly shutdown so client recv() returns/raises
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                conn.close()
            except:
                pass
        except Exception as e:
            ui_queue.put(f"Error notifying {user} of game end: {e}")

    refresh_scoreboard()
    broadcast_scoreboard()

    # Clean up all state
    close_all_clients()
    players.clear()
    player_scores.clear()
    round_scores.clear()
    answers_by_player.clear()
    game_roster = set()
    clear_scoreboard()

    game_running = False
    game_ending = False


def run_game():
    global answers_count, game_running, active_question_idx
    global answered_players, correct_players, pending_results, game_roster, round_scores

    # Reset per-game state
    answered_players = []
    correct_players = []
    pending_results = {}
    round_scores = {}
    answers_count = 0

    # Snapshot of players at game start
    with lock:
        game_roster = set(players.keys())
    game_running = True

    # Iterate through questions
    for question_index in range(len(questions)):
        if shutdown_flag.is_set():
            finish_game("Server shutting down.")
            return

        with lock:
            if len(players) < 2:
                finish_game("Player count is less than 2; Ending the game.")
                return

        active_question_idx = question_index

        # Reset round-specific tracking
        answered_players.clear()
        correct_players.clear()
        pending_results.clear()
        round_scores.clear()

        q = questions[question_index]
        message = f"QUESTION:{q['question']}:{q['A']}:{q['B']}:{q['C']}"

        # Send question to all players
        for username, conn in list(players.items()):
            try:
                conn.sendall((message + "\n").encode())
            except Exception as e:
                ui_queue.put(f"Error sending question to {username}: {e}")

        ui_queue.put("Waiting for answers to current question...")
        waiting_for_last_answer = False

        # Wait until all connected players answer
        while True:
            if shutdown_flag.is_set():
                finish_game("Server shutting down.")
                return

            with lock:
                remaining = set(players) - set(answered_players)
                current_player_count = len(players)

            if not remaining:
                break

            time.sleep(0.1)

            # Grace period if players leave mid-question
            if current_player_count < 2 and not waiting_for_last_answer:
                ui_queue.put("Waiting for last player's answer before ending.")
                waiting_for_last_answer = True

        # Send individual results
        for user, result_msg in pending_results.items():
            conn = players.get(user)
            if conn:
                try:
                    conn.sendall((result_msg + "\n").encode())
                except:
                    pass

        # Apply round scores to total scores
        with lock:
            for user, pts in round_scores.items():
                if user in player_scores:
                    player_scores[user] += pts

        refresh_scoreboard()
        broadcast_scoreboard()

        if not game_running:
            return

    finish_game("All questions have been sent and answered!")


def receive_answer(username, answer):
    global answered_players, correct_players, pending_results, round_scores

    # --- ADDED: Thread Locking ---
    with lock:
        # Reject answers if game is not active
        if not game_running:
            conn = players.get(username)
            ui_queue.put(f"{username} tried to answer before the game started.")
            if conn:
                conn.sendall("ERROR:GAME_NOT_STARTED\n".encode())
            return

        # Reject answers if there is no active question
        if active_question_idx is None or active_question_idx >= len(questions):
            conn = players.get(username)
            ui_queue.put(f"{username} tried to answer with no active question.")
            if conn:
                conn.sendall("ERROR:NO_ACTIVE_QUESTION\n".encode())
            return

        # Ignore duplicate answers
        if username in answered_players:
            return
        
        # Log specific answer choice 
        ui_queue.put(f"Player {username} submitted answer: {answer}")

        answered_players.append(username)

        correct_answer = questions[active_question_idx]["Answer"][-1].strip().upper()
        answer = answer.strip().upper()

        # Correct answer handling
        if answer == correct_answer:
            correct_players.append(username)
            n_players = len(players)
            position = len(correct_players)

            # First correct gets more points
            points_awarded = n_players if position == 1 else 1
            round_scores[username] = points_awarded

            if position <= 3:
                suffix = "st" if position == 1 else "nd" if position == 2 else "rd"
                msg = (
                    f"RESULT:CORRECT:Congratulations! "
                    f"You are the {position}{suffix} person to answer correctly. "
                    f"Points earned: {points_awarded}"
                )
                ui_queue.put(f"{username} answered correctly ({position}{suffix}) +{points_awarded} pts")
            else:
                msg = f"RESULT:CORRECT:Congratulations! Points earned: {points_awarded}"
                ui_queue.put(f"{username} answered correctly +{points_awarded} pts")

            pending_results[username] = msg

        else:
            # Wrong answer handling
            msg = f"RESULT:WRONG:Wrong Answer! Correct answer: {correct_answer}."
            pending_results[username] = msg
            ui_queue.put(f"{username} answered incorrectly.")

        # Log answer history
        answers_by_player[username].append({
            "question_index": active_question_idx,
            "answer": answer,
            "correct": answer == correct_answer,
        })


def handle_client(conn, addr):
    # Read username sent by client
    try:
        received_data = conn.recv(1024)
        username = received_data.decode().strip().lower()
    except:
        conn.close()
        return

    # Reject any join attempts once game has started (no reconnections allowed)
    if game_running:
        ui_queue.put(f"Connection attempt from {addr} rejected: game already started.")
        try:
            conn.sendall("GAME_ALREADY_STARTED\n".encode())
        except:
            pass
        conn.close()
        return

    # Validate username
    if not username:
        conn.sendall("The name cannot be empty!\n".encode())
        ui_queue.put("A user with an invalid username tried to connect.")
        conn.close()
        return

    if username in players:
        conn.sendall(f"The name {username} already exists!\n".encode())
        ui_queue.put(f"Duplicate username attempt: {username}")
        conn.close()
        return

    # Register player
    players[username] = conn
    answers_by_player.setdefault(username, [])
    player_scores.setdefault(username, 0)

    ui_queue.put(f"{username} has connected to the server.")
    # Update the full ranked scoreboard (avoid appending unranked lines)
    refresh_scoreboard()
    broadcast_scoreboard()

    conn.sendall(f"Welcome, {username}!\n".encode())

    # Send scoreboard and possibly active question
    if game_running:
        send_scoreboard_to_client(conn)
        if active_question_idx is not None:
            q = questions[active_question_idx]
            conn.sendall(f"QUESTION:{q['question']}:{q['A']}:{q['B']}:{q['C']}\n".encode())
    else:
        broadcast_scoreboard()

    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break

            message = data.decode().strip()
            if message.startswith("ANSWER:"):
                parts = message.split(":")
                if len(parts) == 2:
                    receive_answer(username, parts[1])
            else:
                conn.sendall(data)

    except Exception as e:
        # If the game is ending, the socket was closed intentionally. 
        # We suppress the error log to avoid "WinError 10038" spam.
        if not game_ending:
            ui_queue.put(f"{username} connection error: {e}")

    finally:
        # We only log disconnects if the game isn't ending, 
        # otherwise the log gets flooded when everyone is kicked at once.
        if not game_ending:
            ui_queue.put(f"{username} has disconnected from the server.")
            
        players.pop(username, None)
        if not game_running:
            player_scores.pop(username, None)

        # Notify remaining players
        for user, c in list(players.items()):
            try:
                c.sendall(f"USER_LEFT:{username}\n".encode())
            except:
                pass

        if not game_running:
            refresh_scoreboard()
            broadcast_scoreboard()


def server_loop():
    ui_queue.put("Server has started listening")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        global server_sock
        server_sock = s

        ip = ip_entry.get()
        port = int(port_entry.get())

        s.bind((ip, port))
        s.listen()
        s.settimeout(1.0)

        while not shutdown_flag.is_set():
            try:
                conn, addr = s.accept()
            except socket.timeout:
                continue
            except OSError as e:
                if not shutdown_flag.is_set():
                    ui_queue.put(f"Server socket error: {e}")
                    finish_game("Server disconnected.")
                break

            threading.Thread(target=handle_client, args=(conn, addr)).start()


def start_server():
    threading.Thread(target=server_loop).start()


def log_event(message):
    try:
        log_box.config(state=tk.NORMAL)
        log_box.insert(tk.END, message + "\n")
        log_box.config(state=tk.DISABLED)
        log_box.yview(tk.END)
    except tk.TclError:
        pass


def log_scoreboard_names(message):
    scoreboard_names.config(state=tk.NORMAL)
    scoreboard_names.insert(tk.END, message + "\n")
    scoreboard_names.config(state=tk.DISABLED)
    scoreboard_names.yview(tk.END)


def log_scoreboard_scores(message):
    scoreboard_scores.config(state=tk.NORMAL)
    scoreboard_scores.insert(tk.END, message + "\n")
    scoreboard_scores.config(state=tk.DISABLED)
    scoreboard_scores.yview(tk.END)


def broadcast_scoreboard():
    usernames_list = []
    scores_list = []

    # Sort players by score, highest first
    sorted_users = sorted(
        ((u, player_scores.get(u, 0)) for u in players),
        key=lambda item: item[1],
        reverse=True,
    )

    current_rank = 0
    prev_score = None
    for idx, (u, score) in enumerate(sorted_users, start=1):
        if prev_score is None or score < prev_score:
            current_rank = idx
            prev_score = score
        usernames_list.append(f"{current_rank}. {u}")
        scores_list.append(str(score))

    scoreboard_message = f"SCOREBOARD:{','.join(usernames_list)}:{','.join(scores_list)}"

    for u, conn in list(players.items()):
        try:
            conn.sendall((scoreboard_message + "\n").encode())
        except Exception as e:
            ui_queue.put(f"Error sending scoreboard to {u}: {e}")


def send_scoreboard_to_client(conn):
    usernames_list = []
    scores_list = []

    sorted_users = sorted(
        ((u, player_scores.get(u, 0)) for u in players),
        key=lambda item: item[1],
        reverse=True,
    )

    current_rank = 0
    prev_score = None
    for idx, (u, score) in enumerate(sorted_users, start=1):
        if prev_score is None or score < prev_score:
            current_rank = idx
            prev_score = score
        usernames_list.append(f"{current_rank}. {u}")
        scores_list.append(str(score))

    scoreboard_message = f"SCOREBOARD:{','.join(usernames_list)}:{','.join(scores_list)}"
    try:
        conn.sendall((scoreboard_message + "\n").encode())
    except:
        pass


def refresh_scoreboard():
    scoreboard_names.config(state=tk.NORMAL)
    scoreboard_names.delete(1.0, tk.END)
    scoreboard_scores.config(state=tk.NORMAL)
    scoreboard_scores.delete(1.0, tk.END)

    sorted_users = sorted(
        ((u, player_scores.get(u, 0)) for u in players),
        key=lambda item: item[1],
        reverse=True,
    )

    current_rank = 0
    prev_score = None
    for idx, (u, score) in enumerate(sorted_users, start=1):
        if prev_score is None or score < prev_score:
            current_rank = idx
            prev_score = score
        scoreboard_names.insert(tk.END, f"{current_rank}. {u}\n")
        scoreboard_scores.insert(tk.END, str(score) + "\n")

    scoreboard_names.config(state=tk.DISABLED)
    scoreboard_scores.config(state=tk.DISABLED)


def clear_scoreboard():
    scoreboard_names.config(state=tk.NORMAL)
    scoreboard_names.delete(1.0, tk.END)
    scoreboard_names.config(state=tk.DISABLED)

    scoreboard_scores.config(state=tk.NORMAL)
    scoreboard_scores.delete(1.0, tk.END)
    scoreboard_scores.config(state=tk.DISABLED)


def ui_queue_worker():
    # Continuously pull messages and log them in the UI
    while not shutdown_flag.is_set():
        msg = ui_queue.get()
        if msg is None:
            break
        log_event(msg)


def handle_close():
    shutdown_flag.set()
    finish_game("Server shutting down.")
    if server_sock:
        try:
            server_sock.close()
        except:
            pass
    ui_queue.put(None)
    root.destroy()


root = tk.Tk()
build_ui(root)