import serial
import time
import threading
from collections import defaultdict
from tkinter import *
from tkinter import messagebox, filedialog, ttk
import json
import serial.tools.list_ports

# Function to list available COM ports
def list_com_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

# Function to initialize the serial connection
def init_serial(port, baud_rate):
    try:
        ser = serial.Serial(port, baud_rate, timeout=1)
        return ser
    except serial.SerialException as e:
        messagebox.showerror("Serial Port Error", f"Error opening serial port {port}: {e}")
        return None

# Initialize global variables
ser = None
can_message_stats = defaultdict(lambda: {'last_time': None, 'count': 0, 'period': 0, 'data': []})
recording = False
recorded_data = []
lock = threading.Lock()
stop_event = threading.Event()
sending_event = threading.Event()  # To ensure send_all_frames can only be called once at a time
periodic_event = threading.Event()  # To control the periodic sending of frames
dirty = threading.Event()

def process_can_frame(frame):
    frame = frame.strip()
    if not frame:
        return
    if frame[0] == 'T':
        try:
            can_id = int(frame[1:4], 16)
            dlc = int(frame[4], 16)
            data = [int(frame[i:i+2], 16) for i in range(5, 5 + dlc * 2, 2)]

            current_time = time.time()
            with lock:
                if can_message_stats[can_id]['last_time'] is not None:
                    period = (current_time - can_message_stats[can_id]['last_time']) * 1000  # Convert to milliseconds
                    can_message_stats[can_id]['period'] = period

                can_message_stats[can_id]['last_time'] = current_time
                can_message_stats[can_id]['count'] += 1
                can_message_stats[can_id]['data'] = data

                if recording:
                    recorded_data.append({'id': can_id, 'time': current_time, 'data': data})
                dirty.set()

        except Exception as e:
            print(f"Error processing frame: {e}")

def read_serial():
    buffer = ""
    while not stop_event.is_set():
        try:
            if ser.in_waiting > 0:
                buffer += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                while '\n' in buffer:
                    frame, buffer = buffer.split('\n', 1)
                    process_can_frame(frame)
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            time.sleep(0.02)  # Wait a bit before retrying
        except Exception as e:
            print(f"Unexpected error: {e}")

def display_can_data():
    while not stop_event.is_set():
        if dirty.is_set():
            with lock:
                max_data_len = max((len(stats['data']) for stats in can_message_stats.values()), default=0)
                max_period_len = max((len(f"{stats['period']:.2f}") for stats in can_message_stats.values()), default=0)
                max_count_len = max((len(f"{stats['count']}") for stats in can_message_stats.values()), default=0)

                output = "Reading CAN frames. Press 'q' to exit, 'r' to reset stats.\n"

                for can_id, stats in can_message_stats.items():
                    data_str = ' '.join(f'0x{byte:02X}' for byte in stats['data'])
                    output += (f"ID: 0x{can_id:03X} DLC: {len(stats['data']):1d} "
                               f"Data: {data_str:<{max_data_len * 5}} | "
                               f"PERIOD: {stats['period']:>{max_period_len}.2f} ms || "
                               f"COUNT: {stats['count']:>{max_count_len}d}\n")

                text_output.delete('1.0', END)
                text_output.insert(END, output)
            dirty.clear()
        time.sleep(0.5)  # Adjusted the sleep to 0.5 seconds to balance update frequency

def reset_stats():
    global can_message_stats
    with lock:
        for can_id in can_message_stats:
            can_message_stats[can_id]['last_time'] = None
            can_message_stats[can_id]['count'] = 0
            can_message_stats[can_id]['period'] = 0
            can_message_stats[can_id]['data'] = []
        dirty.set()

def start_recording():
    global recording, recorded_data
    recording = True
    recorded_data = []
    messagebox.showinfo("Recording", "Started recording CAN messages.")

def stop_recording():
    global recording
    recording = False
    messagebox.showinfo("Recording", "Stopped recording CAN messages.")

def save_recording():
    global recorded_data
    file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
    if file_path:
        with open(file_path, 'w') as file:
            json.dump(recorded_data, file)
        messagebox.showinfo("Save Recording", "Recording saved successfully.")

def play_recording():
    global ser, stop_event
    stop_event.set()  # Stop the serial read and display threads
    resume_btn.pack(side=LEFT, padx=5, pady=5)  # Show the resume button
    file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
    if file_path:
        with open(file_path, 'r') as file:
            data = json.load(file)
        display_edit_window(data)

def display_edit_window(data):
    def update_frame_list():
        tree.delete(*tree.get_children())  # Clear the current items in the treeview
        for i, frame in enumerate(data):
            frame_id_str = f"0x{frame['id']:03X}"
            tree.insert('', 'end', values=["", frame_id_str, len(frame['data'])] + [f"0x{byte:02X}" for byte in frame['data']])

    def send_frame(frame_str):
        frame_str = frame_str + "\nEND\n"
        print(f"Sending frame: {frame_str.strip()}")
        ser.write(frame_str.encode('utf-8'))
        ser.flush()
        time.sleep(0.01)

    def send_selected_frames():
        sent_frames = []
        for child in tree.get_children():
            if "checked" in tree.item(child, "tags"):
                frame_values = tree.item(child, 'values')
                frame_id = frame_values[1]
                dlc = frame_values[2]
                frame_data = [frame_values[i] for i in range(3, 3 + int(dlc))]
                frame_str = f"T{frame_id[2:]}{dlc}{''.join(byte[2:] for byte in frame_data)}"
                send_frame(frame_str)
                sent_frames.append(frame_str)
                print(f"Sent frame: {frame_str.strip()}")

    def apply_filter():
        filter_text = filter_entry.get().strip().upper()  # Convert filter to uppercase for consistent matching

        # Clear the current displayed items
        tree.delete(*tree.get_children())

        # Apply the filter
        for frame in data:
            frame_id_str = f"0x{frame['id']:03X}".upper()  # Ensure the ID is in uppercase to match the filter
            if filter_text in frame_id_str:
                # If the filter matches, insert the frame into the treeview
                tree.insert('', 'end', values=["", frame_id_str, len(frame['data'])] + [f"0x{byte:02X}" for byte in frame['data']])

        # If no filter is applied (empty string), show all data
        if filter_text == "":
            update_frame_list()

    def send_all_frames():
        if not sending_event.is_set():
            stop_event.clear()
            sending_event.set()
            chunk_size = 10
            threading.Thread(target=send_all_frames_thread, args=(chunk_size,)).start()
        else:
            messagebox.showinfo("Sending in Progress", "Frames are already being sent. Please wait until completion or stop the sending process.")

    def send_all_frames_thread(chunk_size):
        all_children = list(tree.get_children())
        total_frames = len(all_children)
        for i in range(0, total_frames, chunk_size):
            if stop_event.is_set():
                break
            chunk = all_children[i:i + chunk_size]
            for child in chunk:
                frame_values = tree.item(child, 'values')
                frame_id = frame_values[1]
                dlc = frame_values[2]
                frame_data = [frame_values[j] for j in range(3, 3 + int(dlc))]
                frame_str = f"T{frame_id[2:]}{dlc}{''.join(byte[2:] for byte in frame_data)}"
                send_frame(frame_str)
                print(f"Sent frame: {frame_str.strip()}")
            time.sleep(0.01)

        if stop_event.is_set():
            print("Sending Stopped", "Stopped sending frames.")
        else:
            print("Sending Complete", "All frames sent.")
        sending_event.clear()

    def delete_selected_frames():
        for child in tree.get_children():
            if "checked" in tree.item(child, "tags"):
                tree.delete(child)

    def stop_sending_frames():
        stop_event.set()
        sending_event.clear()

    def on_double_click(event):
        item = tree.selection()[0]
        column = tree.identify_column(event.x)
        if column == "#1":
            return
        column_index = int(column.replace('#', '')) - 1
        x, y, width, height = tree.bbox(item, column)
        entry = Entry(tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, tree.item(item, 'values')[column_index])
        entry.focus_set()
        entry.select_range(0, END)

        def update_value(event=None):
            new_value = entry.get()
            tree.set(item, column_index, new_value)
            entry.destroy()

        entry.bind('<Return>', update_value)
        entry.bind('<FocusOut>', update_value)

    def on_click(event):
        region = tree.identify("region", event.x, event.y)
        if region == "cell":
            column = tree.identify_column(event.x)
            if column == "#1":
                item = tree.identify_row(event.y)
                if item:
                    current_tags = tree.item(item, "tags")
                    if "checked" in current_tags:
                        tree.item(item, tags=[])
                    else:
                        tree.item(item, tags=["checked"])

    def on_close_edit_window():
        stop_event.clear()
        edit_window.destroy()

    edit_window = Toplevel(root)
    edit_window.title("Edit and Send Frames")
    edit_window.geometry("800x600")
    edit_window.protocol("WM_DELETE_WINDOW", on_close_edit_window)

    filter_frame = Frame(edit_window)
    filter_frame.pack(fill=X)

    filter_label = Label(filter_frame, text="Filter by ID (e.g., 0x123):")
    filter_label.pack(side=LEFT, padx=5, pady=5)

    filter_entry = Entry(filter_frame)
    filter_entry.pack(side=LEFT, padx=5, pady=5)

    apply_filter_btn = Button(filter_frame, text="Apply Filter", command=apply_filter)
    apply_filter_btn.pack(side=LEFT, padx=5, pady=5)

    tree = ttk.Treeview(edit_window, columns=("check", "ID", "DLC") + tuple(f"Byte{i}" for i in range(8)), show='headings')
    tree.heading("check", text="", anchor=CENTER)
    tree.heading("ID", text="ID", anchor=CENTER)
    tree.heading("DLC", text="DLC", anchor=CENTER)
    for i in range(8):
        tree.heading(f"Byte{i}", text=f"Byte{i}", anchor=CENTER)
    tree.column("check", width=30, anchor=CENTER)
    tree.column("ID", width=50, anchor=CENTER)
    tree.column("DLC", width=50, anchor=CENTER)
    for i in range(8):
        tree.column(f"Byte{i}", width=50, anchor=CENTER)
    tree.pack(fill=BOTH, expand=True)

    tree.tag_configure('checked', background='lightgreen')

    tree.bind("<Double-1>", on_double_click)
    tree.bind("<Button-1>", on_click)

    update_frame_list()

    send_btn = Button(edit_window, text="Send Selected Frames", command=send_selected_frames)
    send_btn.pack(side=LEFT, padx=5, pady=5)
    send_all_btn = Button(edit_window, text="Send All Frames", command=send_all_frames)
    send_all_btn.pack(side=LEFT, padx=5, pady=5)
    delete_btn = Button(edit_window, text="Delete Selected Frames", command=delete_selected_frames)
    delete_btn.pack(side=LEFT, padx=5, pady=5)
    stop_btn = Button(edit_window, text="Stop Sending Frames", command=stop_sending_frames)
    stop_btn.pack(side=LEFT, padx=5, pady=5)


def display_single_shot_window():
    def update_frame_list():
        for child in tree.get_children():
            tree.delete(child)
        for i, frame in enumerate(single_shot_data):
            tree.insert('', 'end', values=["", f"0x{frame['id']:03X}", len(frame['data']), frame['period']] + [f"0x{byte:02X}" for byte in frame['data']])

    def add_frame():
        new_frame = {'id': 0, 'data': [0]*8, 'period': 1000}
        single_shot_data.append(new_frame)
        update_frame_list()

    def send_frame(frame_str):
        frame_str = frame_str + "\nEND\n"  # Dodanie separatora
        print(f"Sending frame: {frame_str.strip()}")  # Log the frame being sent
        ser.write(frame_str.encode('utf-8'))
        ser.flush()  # Ensure the buffer is sent immediately
        time.sleep(0.01)

    def send_selected_frames():
        sent_frames = []
        for child in tree.get_children():
            if "checked" in tree.item(child, "tags"):
                frame_values = tree.item(child, 'values')
                frame_id = frame_values[1]
                dlc = frame_values[2]
                frame_data = [frame_values[i] for i in range(4, 4 + int(dlc))]
                frame_str = f"T{frame_id[2:]}{dlc}{''.join(byte[2:] for byte in frame_data)}"
                send_frame(frame_str)
                sent_frames.append(frame_str)
                print(f"Sent frame: {frame_str.strip()}")  # Print each frame individually

    def delete_selected_frames():
        global single_shot_data
        for child in tree.get_children():
            if "checked" in tree.item(child, "tags"):
                index = tree.index(child)
                tree.delete(child)
                single_shot_data.pop(index)

    def start_periodic_send():
        periodic_event.clear()
        for frame in single_shot_data:
            threading.Thread(target=send_frame_periodically, args=(frame,), daemon=True).start()
             
    def send_frame_periodically(frame):
        while not periodic_event.is_set():
            frame_str = f"T{frame['id']:03X}{len(frame['data'])}{''.join(f'{byte:02X}' for byte in frame['data'])}\nEND\n"
            send_frame(frame_str)
            print(f"Sent periodic frame: {frame_str.strip()}")
            time.sleep(frame['period'] / 1000.0)  # Convert milliseconds to seconds
            
    def stop_periodic_send():
        periodic_event.set()

    def periodic_send_thread():
        while not periodic_event.is_set():
            for frame in single_shot_data:
                frame_str = f"T{frame['id']:03X}{len(frame['data'])}{''.join(f'{byte:02X}' for byte in frame['data'])}\nEND\n"
                send_frame(frame_str)
                print(f"Sent periodic frame: {frame_str.strip()}")
                time.sleep(frame['period'] / 1000.0)  # Convert milliseconds to seconds
                if periodic_event.is_set():
                    break

    def on_double_click(event):
        item = tree.selection()[0]
        column = tree.identify_column(event.x)
        if column == "#1":  # Disable editing in checkbox column
            return
        column_index = int(column.replace('#', '')) - 1
        x, y, width, height = tree.bbox(item, column)
        entry = Entry(tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, tree.item(item, 'values')[column_index])
        entry.focus_set()  # Set focus to the entry widget
        entry.select_range(0, END)  # Select the entire text in the entry widget
        
        def update_value():
            new_value = entry.get()
            tree.set(item, column_index, new_value)
            frame_index = tree.index(item)
            if column_index == 1:
                single_shot_data[frame_index]['id'] = int(new_value, 16)
            elif column_index == 3:
                single_shot_data[frame_index]['period'] = int(new_value)
            elif column_index >= 4:
                byte_index = column_index - 4
                single_shot_data[frame_index]['data'][byte_index] = int(new_value, 16)
            entry.destroy()
            root.unbind("<Button-1>")  # Unbind the click outside event after entry is destroyed

        entry.bind('<Return>', lambda e: update_value())
        entry.bind('<FocusOut>', lambda e: update_value())  # Treat FocusOut as Enter

    def on_click(event):
        region = tree.identify("region", event.x, event.y)
        if region == "cell":
            column = tree.identify_column(event.x)
            if column == "#1":  # First column for checkboxes
                item = tree.identify_row(event.y)
                if item:
                    current_tags = tree.item(item, "tags")
                    if "checked" in current_tags:
                        tree.item(item, tags=[])
                    else:
                        tree.item(item, tags=["checked"])

    single_shot_window = Toplevel(root)
    single_shot_window.title("CAN Single Shot")
    single_shot_window.geometry("800x600")  # Set user-friendly resolution

    tree = ttk.Treeview(single_shot_window, columns=("check", "ID", "DLC", "Period") + tuple(f"Byte{i}" for i in range(8)), show='headings')
    tree.heading("check", text="", anchor=CENTER)
    tree.heading("ID", text="ID", anchor=CENTER)
    tree.heading("DLC", text="DLC", anchor=CENTER)
    tree.heading("Period", text="Period (ms)", anchor=CENTER)
    for i in range(8):
        tree.heading(f"Byte{i}", text=f"Byte{i}", anchor=CENTER)
    tree.column("check", width=30, anchor=CENTER)
    tree.column("ID", width=50, anchor=CENTER)
    tree.column("DLC", width=50, anchor=CENTER)
    tree.column("Period", width=100, anchor=CENTER)
    for i in range(8):
        tree.column(f"Byte{i}", width=50, anchor=CENTER)
    tree.pack(fill=BOTH, expand=True)

    tree.tag_configure('checked', background='lightgreen')

    tree.bind("<Double-1>", on_double_click)
    tree.bind("<Button-1>", on_click)

    add_btn = Button(single_shot_window, text="Add Frame", command=add_frame)
    add_btn.pack(side=LEFT, padx=5, pady=5)
    send_btn = Button(single_shot_window, text="Send Selected Frames", command=send_selected_frames)
    send_btn.pack(side=LEFT, padx=5, pady=5)
    delete_btn = Button(single_shot_window, text="Delete Selected Frames", command=delete_selected_frames)
    delete_btn.pack(side=LEFT, padx=5, pady=5)
    start_btn = Button(single_shot_window, text="Start Periodic Send", command=start_periodic_send)
    start_btn.pack(side=LEFT, padx=5, pady=5)
    stop_btn = Button(single_shot_window, text="Stop Periodic Send", command=stop_periodic_send)
    stop_btn.pack(side=LEFT, padx=5, pady=5)

    update_frame_list()

# ---- Added Reverse Engineering Window ----
def display_reverse_engineering_window():
    previous_data = {}  # To store previous data for comparison

    def update_frame_list():
        nonlocal previous_data

        for child in reverse_tree.get_children():
            reverse_tree.delete(child)

        for can_id, stats in can_message_stats.items():
            # Convert CAN ID to string and prepare data for display
            id_str = f"0x{can_id:03X}"
            dlc_str = f"{len(stats['data'])}"
            period_str = f"{stats['period']:.2f}"
            byte_values = []
            tag_list = []

            # Check if data has changed and mark the changes
            if can_id in previous_data:
                previous_bytes = previous_data[can_id]['data']
                for i, byte in enumerate(stats['data']):
                    if byte != previous_bytes[i]:
                        change_count = previous_data[can_id]['change_count'][i] + 1
                        previous_data[can_id]['change_count'][i] = change_count
                        color_tag = f"changed_byte{i}_{change_count % 3}"
                        byte_values.append(f"{byte} •")  # Add bullet point to indicate change
                        tag_list.append(color_tag)
                    else:
                        byte_values.append(f"{byte}")
                        tag_list.append("default")
            else:
                previous_data[can_id] = {'data': stats['data'], 'change_count': [0]*8}
                byte_values = [f"{byte}" for byte in stats['data']]
                tag_list = ["default"] * 8

            reverse_tree.insert('', 'end', values=[id_str, dlc_str, period_str] + byte_values, tags=tag_list)

            # Update the stored previous data
            previous_data[can_id]['data'] = stats['data'][:]

    def refresh():
        update_frame_list()
        root.after(10, refresh)  # Refresh every second

    reverse_window = Toplevel(root)
    reverse_window.title("Reverse Engineering")
    reverse_window.geometry("800x600")

    reverse_tree = ttk.Treeview(reverse_window, columns=("ID", "DLC", "Period (ms)") + tuple(f"Byte{i}" for i in range(8)), show='headings')
    reverse_tree.heading("ID", text="ID", anchor=CENTER)
    reverse_tree.heading("DLC", text="DLC", anchor=CENTER)
    reverse_tree.heading("Period (ms)", text="Period (ms)", anchor=CENTER)
    for i in range(8):
        reverse_tree.heading(f"Byte{i}", text=f"Byte{i}", anchor=CENTER)
    reverse_tree.column("ID", width=50, anchor=CENTER)
    reverse_tree.column("DLC", width=50, anchor=CENTER)
    reverse_tree.column("Period (ms)", width=100, anchor=CENTER)
    for i in range(8):
        reverse_tree.column(f"Byte{i}", width=50, anchor=CENTER)
    reverse_tree.pack(fill=BOTH, expand=True)

    # Define tag styles for changed bytes with different colors
    for i in range(8):
        reverse_tree.tag_configure(f"changed_byte{i}_0", background="lightcoral")  # First change
        reverse_tree.tag_configure(f"changed_byte{i}_1", background="lightgreen")  # Second change
        reverse_tree.tag_configure(f"changed_byte{i}_2", background="lightblue")   # Third change
    reverse_tree.tag_configure("default", background="white")

    refresh()

    reverse_window.mainloop()

def display_com_logger():
    def read_com_data():
        while not com_stop_event.is_set():
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                com_text_output.insert(END, data)
                com_text_output.see(END)
            time.sleep(0.1)

    def send_com_data():
        message = com_entry.get()
        if message:
            ser.write((message + '\n').encode('utf-8'))
            com_entry.delete(0, END)

    com_logger_window = Toplevel(root)
    com_logger_window.title("COM Logger")
    com_logger_window.geometry("800x600")  # Set user-friendly resolution

    com_text_output = Text(com_logger_window, wrap=WORD, height=20, width=80, bg='black', fg='white')
    com_text_output.pack(fill=BOTH, expand=True)

    com_entry_frame = Frame(com_logger_window, bg='black')
    com_entry_frame.pack(fill=X, padx=5, pady=5)

    com_entry = Entry(com_entry_frame, bg='black', fg='white')
    com_entry.pack(side=LEFT, fill=X, expand=True, padx=5, pady=5)

    send_com_btn = Button(com_entry_frame, text="Send", command=send_com_data, bg='black', fg='white')
    send_com_btn.pack(side=LEFT, padx=5, pady=5)

    com_stop_event.clear()
    threading.Thread(target=read_com_data, daemon=True).start()

def resume_monitoring():
    resume_btn.pack_forget()  # Hide the resume button
    stop_event.clear()  # Clear stop_event to restart reading
    threading.Thread(target=read_serial, daemon=True).start()
    threading.Thread(target=display_can_data, daemon=True).start()

def main():
    # Initialize GUI
    global root, text_output, stop_event, resume_btn, single_shot_data, com_stop_event
    single_shot_data = []  # Initialize single_shot_data as an empty list
    com_stop_event = threading.Event()  # Event to stop COM Logger thread
    root = Tk()
    root.title("CAN Bus Monitor")
    root.configure(bg='black')

    def connect():
        global ser, stop_event
        stop_event.clear()  # Ensure stop event is clear
        selected_port = port_var.get()
        selected_baud = baud_var.get()
        if not selected_port:
            messagebox.showerror("Connection Error", "Please select a COM port.")
            return
        try:
            baud_rate = int(selected_baud)
        except ValueError:
            messagebox.showerror("Connection Error", "Please select a valid baud rate.")
            return
        ser = init_serial(selected_port, baud_rate)
        if ser:
            messagebox.showinfo("Connection Successful", f"Connected to {selected_port} at {baud_rate} baud.")
            # Start the serial reading thread
            threading.Thread(target=read_serial, daemon=True).start()
            threading.Thread(target=display_can_data, daemon=True).start()

    port_frame = Frame(root, bg='black')
    port_frame.pack(fill=X, padx=5, pady=5)

    port_label = Label(port_frame, text="Select COM Port:", bg='black', fg='white')
    port_label.pack(side=LEFT, padx=5)

    port_var = StringVar()
    ports = list_com_ports()
    port_menu = OptionMenu(port_frame, port_var, *ports)
    port_menu.config(bg='black', fg='white')
    port_menu.pack(side=LEFT, padx=5)

    baud_label = Label(port_frame, text="Select Baud Rate:", bg='black', fg='white')
    baud_label.pack(side=LEFT, padx=5)

    baud_var = StringVar(value="115200")
    baud_menu = OptionMenu(port_frame, baud_var, "9600", "19200", "38400", "57600", "115200", "230400")
    baud_menu.config(bg='black', fg='white')
    baud_menu.pack(side=LEFT, padx=5)

    connect_btn = Button(port_frame, text="Connect", command=connect, bg='black', fg='white')
    connect_btn.pack(side=LEFT, padx=5)

    global text_output
    text_output = Text(root, wrap=WORD, height=20, width=80, bg='black', fg='white')
    text_output.pack(fill=BOTH, expand=True)

    btn_frame = Frame(root, bg='black')
    btn_frame.pack(fill=X)

    start_rec_btn = Button(btn_frame, text="Start Recording", command=start_recording, bg='black', fg='white')
    start_rec_btn.pack(side=LEFT, padx=5, pady=5)

    stop_rec_btn = Button(btn_frame, text="Stop Recording", command=stop_recording, bg='black', fg='white')
    stop_rec_btn.pack(side=LEFT, padx=5, pady=5)

    save_rec_btn = Button(btn_frame, text="Save Recording", command=save_recording, bg='black', fg='white')
    save_rec_btn.pack(side=LEFT, padx=5, pady=5)

    play_rec_btn = Button(btn_frame, text="Play Recording", command=play_recording, bg='black', fg='white')
    play_rec_btn.pack(side=LEFT, padx=5, pady=5)

    single_shot_btn = Button(btn_frame, text="CAN Single Shot", command=display_single_shot_window, bg='black', fg='white')
    single_shot_btn.pack(side=LEFT, padx=5, pady=5)

    reverse_eng_btn = Button(btn_frame, text="Reverse Engineering", command=display_reverse_engineering_window, bg='black', fg='white')
    reverse_eng_btn.pack(side=LEFT, padx=5, pady=5)

    com_logger_btn = Button(btn_frame, text="COM Logger", command=display_com_logger, bg='black', fg='white')
    com_logger_btn.pack(side=LEFT, padx=5, pady=5)

    resume_btn = Button(btn_frame, text="Resume Monitoring", command=resume_monitoring, bg='black', fg='white')
    resume_btn.pack_forget()  # Hide the resume button initially

    reset_btn = Button(btn_frame, text="Reset Stats", command=reset_stats, bg='black', fg='white')
    reset_btn.pack(side=LEFT, padx=5, pady=5)

    root.mainloop()

if __name__ == "__main__":
    main()
