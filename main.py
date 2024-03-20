from tkinter import *
from tkinter import filedialog
from PIL import Image, ImageTk
from carCount import RectPointsHandler, VideoHandler,startCarCounting
import cv2


class App(Tk):
    def __init__(self):
        super().__init__()
        self.title("Car Counting")
        self.geometry("1280x720")  # Adjust window size as needed
        self.cap = None  # Video capture object
        self.canvas = None  # Canvas for video display
        self.rect_points = RectPointsHandler()  # Instantiate RectPointsHandler
        self.video_handler = VideoHandler()  # Instantiate VideoHandler
        self.rect_points_toCounting = []
        self.init_ui()

    def init_ui(self):
        # Label for video selection
        self.label = Label(self, text="Please select video:")
        self.label.pack(pady=10)

        # Button for video selection
        self.select_video_button = Button(
            self, text="Choose Video", foreground="green", command=self.select_video
        )
        self.select_video_button.pack(pady=10)

        # Create a canvas for video display
        self.canvas = Canvas(self, width=self.winfo_screenwidth() // 2, height=self.winfo_screenheight() // 2)
        self.canvas.pack()  # Adjust positioning and size as needed
        
        # Button to reset drawing
        self.reset_button = Button(self, text="Reset", foreground="red", command=self.reset_drawing)
        self.reset_button.pack(pady=10)
        
        # Button to start car counting
        self.start_counting_button = Button(self, text="Start Car Counting", foreground="blue", command=self.start_car_counting)
        self.start_counting_button.pack(pady=10)
        
        


    def select_video(self):
        """
        Opens file dialog, opens video, and schedules frame updates.
        """
        global filename
        filename = filedialog.askopenfilename(title="Select Video File", filetypes=[("Video files", "*.mp4 *.avi")])
        if filename == "":
            return
        
        self.video_handler.set_video_path(filename)  # Set video path in VideoHandler
        
        self.cap = cv2.VideoCapture(filename)
        if not self.cap.isOpened():
            print("Error opening video file.")
            return

        # Function to update video frame on the canvas
        def update_frame(frame_count = 0):
            ret, frame = self.cap.read()  # Capture the frame
            if not ret or frame_count >= 1:  # Stop after 1 frames (assuming 30 frames per second)
                print("Video stopped.")
                self.cap.release()
                return
            # Get the dimensions of the frame
            frame_height, frame_width, _ = frame.shape
            
            
            # Calculate the aspect ratio of the frame and the canvas
            frame_aspect_ratio = frame_width / frame_height
            canvas_aspect_ratio = self.canvas.winfo_width() / self.canvas.winfo_height()
    
            if frame_aspect_ratio > canvas_aspect_ratio:
                # Frame is wider than canvas
                # Resize frame to fit canvas width, maintaining aspect ratio
                resized_frame_width = self.canvas.winfo_width()
                resized_frame_height = int(resized_frame_width / frame_aspect_ratio)
            else:
                # Frame is taller than canvas or has equal aspect ratio
                # Resize frame to fit canvas height, maintaining aspect ratio
                resized_frame_height = self.canvas.winfo_height()
                resized_frame_width = int(resized_frame_height * frame_aspect_ratio)
                
            # Resize frame using linear interpolation
            frame = cv2.resize(frame, (resized_frame_width, resized_frame_height), interpolation=cv2.INTER_LINEAR)

            # Convert frame to RGB format
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Create a PhotoImage object from the frame
            frame_image = ImageTk.PhotoImage(Image.fromarray(frame))
            
            # Update the image on the canvas
            self.canvas.create_image(0, 0, anchor=NW, image=frame_image)
            
            self.canvas.image = frame_image  # Update image on canvas

            # Schedule the next frame update using after()
            self.after(30, lambda: update_frame(frame_count + 1))  # Adjust interval as needed
        
        update_frame()  # Start the frame update loop
         # Re-bind the mouse click event to the canvas
        self.canvas.bind("<Button-1>", self.on_canvas_click)

    def destroy(self):  # Override destroy method to release video capture
        super().destroy()
        if self.cap:
            self.cap.release()
    
    def on_canvas_click(self, event):
        self.cap = cv2.VideoCapture(filename)
        # Check if self.cap is initialized
        if self.cap is None or not self.cap.isOpened():
            print("Video capture is not initialized.")
            return
        
        # Get the size of the video frame
        frame_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        frame_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        
        # Calculate the scale factors for converting canvas coordinates to frame coordinates
        scale_x = frame_width / self.canvas.winfo_width()
        scale_y = frame_height / self.canvas.winfo_height()
        
        # Convert canvas click position to video frame coordinates
        frame_x = int(event.x * scale_x)
        frame_y = int(event.y * scale_y)
        
        self.rect_points_toCounting.append(frame_x)
        self.rect_points_toCounting.append(frame_y)
        
        print(f"rect point for counting {self.rect_points_toCounting}")
        
        
        # Store the clicked points
        self.rect_points.add_rect_point(event.x)
        self.rect_points.add_rect_point(event.y)
        
        # Draw a circle at the clicked point
        self.canvas.create_oval(event.x - 2, event.y - 2, event.x + 2, event.y + 2, fill="red")
        
        # If at least two points are clicked, draw lines between them
        if len(self.rect_points.rect_points) >= 4:
            # Draw lines between the last two clicked points
            x1, y1 = self.rect_points.rect_points[-4], self.rect_points.rect_points[-3]
            x2, y2 = self.rect_points.rect_points[-2], self.rect_points.rect_points[-1]
            self.canvas.create_line(x1, y1, x2, y2, fill="blue", width=2)
            print(self.rect_points.rect_points)
            # If the fourth point is clicked, connect it with the first point and stop drawing
            if len(self.rect_points.rect_points) == 8:
                self.canvas.create_line(self.rect_points.rect_points[-2], self.rect_points.rect_points[-1], 
                                        self.rect_points.rect_points[0], self.rect_points.rect_points[1], fill="blue", width=2)
                # self.rect_points = []  # Reset the list to stop further drawing
                # Disable the click event
                self.canvas.unbind("<Button-1>")

    def reset_drawing(self):
        # Clear canvas and reset points list
        self.canvas.delete("all")
        self.rect_points.rect_points = []
        self.rect_points_toCounting = []
        
    def start_car_counting(self):
        if self.video_handler.video_path:
            startCarCounting(self.video_handler.video_path,self.rect_points_toCounting)
        else:
            print("Please select a video first.")



# Run the app
run_app = App()
run_app.mainloop()
