import socket
import json
import base64
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from threading import Thread
import struct

# Configuration
HOST = '192.168.10.2'  # Interface to bind to (use '' for all interfaces)
PORT = 12345           # Port to listen on

class DepthMapViewer:
    def __init__(self, root):
        self.root = root


        # Get screen dimensions
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        # Calculate position
        x = (screen_width // 2) - (800 // 2)
        y = (screen_height // 2) - (600 // 2)

        self.root.title("Depth Map Viewer")
        self.root.geometry(f"800x600+{x}+{y}")

        # Label to display image
        self.image_label = tk.Label(root)
        self.image_label.pack(expand=True, fill=tk.BOTH)

        # Status bar
        self.status = tk.Label(root, text="Waiting for connection...", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        # Start listener in background thread
        self.listener_thread = Thread(target=self.start_server, daemon=True)
        self.listener_thread.start()

    def start_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((HOST, PORT))
                s.listen()
                self.update_status(f"Listening on {HOST}:{PORT}...")
                while True:
                    conn, addr = s.accept()
                    self.update_status(f"Connected by {addr}")
                    try:
                        self.handle_client(conn)
                    except Exception as e:
                        self.update_status(f"Error handling client: {e}")
                    finally:
                        conn.close()

            except Exception as e:
                self.update_status(f"Server error: {e}")

    def handle_client(self, conn):
        # Receive all data (simple: assume one JSON object, reasonably sized < few MB)
        buffer = b""
        while True:
            
            # Simple protocol: send 4-byte length prefix + JSON payload
            raw_len = conn.recv(4)
            if len(raw_len) != 4:
                continue
            msg_len = struct.unpack('>I', raw_len)[0]
            data = b''
            while len(data) < msg_len:
                chunk = conn.recv(msg_len - len(data))
                if not chunk:
                    break
                data += chunk
            if len(data) != msg_len:
                continue

            # Try to decode JSON; if incomplete, keep receiving
            try:
                data = json.loads(data.decode('utf-8'))
                break
            except json.JSONDecodeError:
                continue  # Incomplete JSON, wait for more

        # Extract payload
        width = data["width"]
        height = data["height"]
        depth_b64 = data["depth"]

        # Decode base64 to bytes
        img_bytes = base64.b64decode(depth_b64)

        # Convert to numpy array
        # ⚠️ ASSUMPTION: coloredDepthMap is 3-channel uint8 (H, W, 3)
        # Total bytes should be height * width * 3
        expected_bytes = height * width * 3
        if len(img_bytes) != expected_bytes:
            self.update_status(f"Warning: Expected {expected_bytes} bytes, got {len(img_bytes)}")

        # Reshape to (H, W, 3)
        try:
            img_array = np.frombuffer(img_bytes, dtype=np.uint8).reshape((height, width, 3))
        except ValueError as e:
            self.update_status(f"Reshape error: {e}")
            return

        # Convert to PIL Image (OpenCV uses BGR; if so, convert to RGB)
        # If your colormap uses RGB already (e.g., matplotlib), skip conversion
        # For OpenCV-style colormaps (jet, etc.), it's usually BGR → convert to RGB
        img_pil = Image.fromarray(img_array, mode='RGB')
        # Uncomment below if image looks wrong (e.g., blue/red swapped):
        # img_pil = Image.fromarray(img_array[:, :, ::-1], mode='RGB')  # BGR → RGB

        # Resize for display if too large
        max_w, max_h = 760, 500
        img_pil.thumbnail((max_w, max_h), Image.LANCZOS)

        # Convert to PhotoImage
        self.photo = ImageTk.PhotoImage(img_pil)  # Keep reference!

        # Update UI (must be in main thread — use after)
        self.root.after(0, self.update_image, self.photo)

    def update_image(self, photo):
        self.image_label.config(image=photo)
        self.image_label.image = photo  # Prevent garbage collection
        self.update_status("Depth map displayed.")

    def update_status(self, msg):
        print(msg)
        self.root.after(0, lambda: self.status.config(text=msg))

def main():
    root = tk.Tk()
    app = DepthMapViewer(root)
    root.mainloop()

if __name__ == "__main__":
    main()
