import sys
import platform
import can
import tkinter as tk
from tkinter import messagebox

# --- Configuration ---
CHANNEL = 'Cummins_net_USB1'
BITRATE = 500000  # 500 kbit/s
# ---------------------

def get_bus():
    """Initializes and returns a CAN bus instance based on the operating system."""
    os_type = platform.system()
    if os_type == 'Windows':
        # Use python-can's PCAN interface
        return can.interface.Bus(channel=CHANNEL, bustype='pcan', bitrate=BITRATE)
    elif os_type == 'Linux':
        # Use python-can's socketcan interface
        # Note: The channel for socketcan is typically a virtual CAN interface name like 'vcan0' or a physical one like 'can0'.
        # The user provided a PCAN channel name, which might need adjustment for socketcan.
        # For this script, we'll assume the user knows to adapt the channel if running on Linux.
        return can.interface.Bus(channel=CHANNEL, bustype='socketcan', bitrate=BITRATE)
    else:
        raise NotImplementedError(f"CAN tool not supported on {os_type}")

def send_message(bus, arbitration_id):
    """Sends a standard CAN message with an 8-byte zero payload."""
    try:
        message = can.Message(
            arbitration_id=arbitration_id,
            data=[0, 0, 0, 0, 0, 0, 0, 0],
            is_extended_id=False
        )
        bus.send(message)
        print(f"Message sent on {bus.channel_info}")
        print(f"ID: {hex(arbitration_id)}, Data: {message.data.hex()}")
    except can.CanError as e:
        print(f"Error sending message: {e}")

def main():
    """Main function to parse arguments and execute commands."""
    if len(sys.argv) < 3 or sys.argv[1] != 'send':
        print("Usage: python can_tool.py send <id>")
        print("  <id>: The arbitration ID in hexadecimal (e.g., 0x123) or decimal.")
        return

    try:
        # Parse arbitration ID, allowing for hex (0x...) or decimal input
        arbitration_id = int(sys.argv[2], 0)
    except ValueError:
        print("Error: Invalid arbitration ID. Please provide a valid hex or decimal number.")
        return

    bus = None
    try:
        bus = get_bus()
        send_message(bus, arbitration_id)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if bus:
            bus.shutdown()

def gui_send():
    """Handler for GUI send button."""
    arb_id_str = arb_id_entry.get()
    try:
        arbitration_id = int(arb_id_str, 0)
    except ValueError:
        messagebox.showerror("Invalid ID", "Please enter a valid hex (0x...) or decimal arbitration ID.")
        return

    bus = None
    try:
        bus = get_bus()
        send_message(bus, arbitration_id)
        messagebox.showinfo("Success", f"Message sent with ID: {hex(arbitration_id)}")
    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        if bus:
            bus.shutdown()

def launch_gui():
    global arb_id_entry
    root = tk.Tk()
    root.title("CAN Tool GUI")

    tk.Label(root, text="Arbitration ID (hex or dec):").grid(row=0, column=0, padx=10, pady=10)
    arb_id_entry = tk.Entry(root)
    arb_id_entry.grid(row=0, column=1, padx=10, pady=10)

    send_btn = tk.Button(root, text="Send", command=gui_send)
    send_btn.grid(row=1, column=0, columnspan=2, pady=10)

    root.mainloop()

if __name__ == "__main__":
    # Launch GUI by default if no arguments or if 'gui' is specified
    if len(sys.argv) == 1 or (len(sys.argv) > 1 and sys.argv[1] == "gui"):
        launch_gui()
    else:
        main()
