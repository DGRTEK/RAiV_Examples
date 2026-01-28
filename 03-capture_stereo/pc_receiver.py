import tkinter as tk
from tkinter import Canvas, Label
import socket
import json
import base64
from PIL import Image, ImageTk
import threading
import struct
import io  # Needed for BytesIO

# Configuration
HOST = '192.168.10.2'
PORT = 12345
IMAGE_WIDTH = 1600
IMAGE_HEIGHT = 1300

CANVAS_SCALE = 0.5
CANVAS_WIDTH = int(IMAGE_WIDTH*CANVAS_SCALE*2);
CANVAS_HEIGHT = int(IMAGE_HEIGHT*CANVAS_SCALE);

class StereoImageViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Stereo Image Viewer")
        #self.root.geometry(f"{IMAGE_WIDTH + 20}x{IMAGE_HEIGHT + 60}")
        self.root.geometry(f"{int(CANVAS_WIDTH + 10)}x{int(CANVAS_HEIGHT + 30)}")

        self.image_label = Label(root, text="Waiting for image...")
        self.image_label.pack()

        self.canvas = Canvas(root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg='black')
        self.canvas.pack()

        self.right_image_tk = None  # Keep reference to avoid garbage collection
        self.left_image_tk = None

    def draw_image(self, image_bmp_b64_right, image_bmp_b64_left):
        # Decode base64 BMP
        bmp_data_right = base64.b64decode(image_bmp_b64_right)
        bmp_data_left = base64.b64decode(image_bmp_b64_left)

        # Convert BMP bytes to PIL Image
        # Note: Tkinter doesn't support BMP directly in all environments; PIL handles it well.
        try:
            pil_image_right = Image.open(io.BytesIO(bmp_data_right))
            # Ensure it's in RGB mode (BMP may be BGR in some cases, but assuming RGB from sender)
            if pil_image_right.mode != 'RGB':
                pil_image_right = pil_image_right.convert('RGB')
        except Exception as e:
            print(f"Error loading image: {e}")
            return

        # Resize if needed (optional safety)
        if pil_image_right.size != (CANVAS_WIDTH, CANVAS_HEIGHT):
            pil_image_right = pil_image_right.resize((int(IMAGE_WIDTH*CANVAS_SCALE), int(IMAGE_HEIGHT*CANVAS_SCALE)), Image.LANCZOS)

        # Convert to PhotoImage for Tkinter
        self.right_image_tk = ImageTk.PhotoImage(pil_image_right)



        try:
            pil_image_left = Image.open(io.BytesIO(bmp_data_left))
            # Ensure it's in RGB mode (BMP may be BGR in some cases, but assuming RGB from sender)
            if pil_image_left.mode != 'RGB':
                pil_image_left = pil_image_left.convert('RGB')
        except Exception as e:
            print(f"Error loading image: {e}")
            return

        # Resize if needed (optional safety)
        if pil_image_left.size != (CANVAS_WIDTH, CANVAS_HEIGHT):
            pil_image_left = pil_image_left.resize((int(IMAGE_WIDTH*CANVAS_SCALE), int(IMAGE_HEIGHT*CANVAS_SCALE)), Image.LANCZOS)

        # Convert to PhotoImage for Tkinter
        self.left_image_tk = ImageTk.PhotoImage(pil_image_left)

        # Clear canvas and draw image
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.right_image_tk)
        self.canvas.create_image(int(IMAGE_WIDTH*CANVAS_SCALE+5), 0, anchor=tk.NW, image=self.left_image_tk)

    def start_listening(self):
        threading.Thread(target=self._listen_for_data, daemon=True).start()

    def _listen_for_data(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            s.bind((HOST, PORT))
            s.listen(1)
            print(f"Listening on {HOST}:{PORT}...")
            while True:
                conn, addr = s.accept()
                print(f"Connection from {addr}")
                try:
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

                    payload = json.loads(data.decode('utf-8'))
                    self.root.after(0, self.draw_image,
                                    payload['bmp_b64_right'],
                                    payload['bmp_b64_left'])
                except Exception as e:
                    print(f"Error receiving data: {e}")
                finally:
                    conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = StereoImageViewer(root)
    app.start_listening()
    root.mainloop()
