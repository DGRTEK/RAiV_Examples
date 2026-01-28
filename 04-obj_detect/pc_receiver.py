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
CANVAS_WIDTH = int(IMAGE_WIDTH*CANVAS_SCALE);
CANVAS_HEIGHT = int(IMAGE_HEIGHT*CANVAS_SCALE);

class ObjectDetectionViewer:
    def __init__(self, root):
        self.root = root

        # Get screen dimensions
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        # Calculate position
        x = (screen_width // 2) - (CANVAS_WIDTH // 2)
        y = (screen_height // 2) - (CANVAS_HEIGHT // 2)

        self.root.title("Object Detection Viewer")

        # Set initial window size and position
        #self.root.geometry(f"{IMAGE_WIDTH + 20}x{IMAGE_HEIGHT + 60}")
        self.root.geometry(f"{int(CANVAS_WIDTH + 10)}x{int(CANVAS_HEIGHT + 30)}+{x}+{y}")

        self.image_label = Label(root, text="Waiting for image...")
        self.image_label.pack()

        self.canvas = Canvas(root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg='black')
        self.canvas.pack()

        self.current_image_tk = None  # Keep reference to avoid garbage collection

    def draw_image_and_detections(self, image_bmp_b64, detected_objects):
        # Decode base64 BMP
        bmp_data = base64.b64decode(image_bmp_b64)

        # Convert BMP bytes to PIL Image
        # Note: Tkinter doesn't support BMP directly in all environments; PIL handles it well.
        try:
            pil_image = Image.open(io.BytesIO(bmp_data))
            # Ensure it's in RGB mode (BMP may be BGR in some cases, but assuming RGB from sender)
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
        except Exception as e:
            print(f"Error loading image: {e}")
            return

        # Resize if needed (optional safety)
        if pil_image.size != (CANVAS_WIDTH, CANVAS_HEIGHT):
            pil_image = pil_image.resize((CANVAS_WIDTH, CANVAS_HEIGHT), Image.LANCZOS)

        # Convert to PhotoImage for Tkinter
        self.current_image_tk = ImageTk.PhotoImage(pil_image)

        # Clear canvas and draw image
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.current_image_tk)

        # Draw bounding boxes and labels
        for obj in detected_objects:
            bbox = obj['bbox']  # [x1, y1, x2, y2] — ensure this format!
            class_name = obj['class_name']
            confidence = obj['confidence']

            bbox[0] = int(bbox[0]*CANVAS_SCALE);
            bbox[1] = int(bbox[1]*CANVAS_SCALE);
            bbox[2] = int(bbox[2]*CANVAS_SCALE);
            bbox[3] = int(bbox[3]*CANVAS_SCALE); 

            # Draw rectangle
            self.canvas.create_rectangle(
                bbox[0], bbox[1], bbox[0]+bbox[2], bbox[1]+bbox[3],
                outline='green', width=2
            )

            # Draw label below the box
            label_text = f"{class_name}: {confidence:.2f}"
            self.canvas.create_text(
                bbox[0], bbox[1]+bbox[3] + 5,
                text=label_text,
                fill='green',
                font=('Arial', 10, 'bold'),
                anchor=tk.NW
            )

        self.image_label.config(text="Image with detections")

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
                    self.root.after(0, self.draw_image_and_detections,
                                    payload['image_bmp_b64'],
                                    payload['detected_objects'])
                except Exception as e:
                    print(f"Error receiving data: {e}")
                finally:
                    conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = ObjectDetectionViewer(root)
    app.start_listening()
    root.mainloop()
