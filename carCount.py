import cv2
from ultralytics import YOLO
from ultralytics.solutions import object_counter
import supervision as sv
from datetime import timedelta

# Load the YOLOv8 model
model = YOLO('yolov8n.pt')

class RectPointsHandler:
    def __init__(self):
        self.rect_points = []

    def add_rect_point(self, point):
        self.rect_points.append(point)

class VideoHandler:
    def __init__(self):
        self.video_path = None

    def set_video_path(self, video_path):
        self.video_path = video_path

def get_video_info(video_path):
    
    # Extracting information about the video
    video_info = sv.VideoInfo.from_video_path(video_path)
    width, height, fps, total_frames = video_info.width, video_info.height, video_info.fps, video_info.total_frames
    
    # Calculating the length of the video by dividing the total number of frames by the frame rate and rounding to the nearest second
    video_length = timedelta(seconds = round(total_frames / fps))
    
    # Print out the video resolution, fps, and length u
    print(f"\033[1mVideo Resolution:\033[0m ({width}, {height})")
    print(f"\033[1mFPS:\033[0m {fps}")
    print(f"\033[1mLength:\033[0m {video_length}")

def startCarCounting(video_path,rect_points):

    print(f"start counting cars path at {video_path}")
    while not video_path:
        pass


    get_video_info(video_path)
    cap = cv2.VideoCapture(video_path)

    assert cap.isOpened(), "Error reading video file" 
    fps = cv2.CAP_PROP_FPS

    # Define region points
    region_points = [(rect_points[0], rect_points[1]), 
                    (rect_points[2], rect_points[3]), 
                    (rect_points[4], rect_points[5]), 
                    (rect_points[6], rect_points[7])]


    # Define desired window size (width, height)
    window_width = 1280
    window_height = 720

    # Variable to store current frame position (in milliseconds)
    current_time = 0

    # Video writer
    video_writer = cv2.VideoWriter("object_counting_output_new1.avi",
                          cv2.VideoWriter_fourcc(*'mp4v'),
                          fps,
                          (window_width, window_height))



    # Init Object Counter
    counter = object_counter.ObjectCounter()
    counter.set_args(view_img=True,
                    reg_pts=region_points,
                    classes_names=model.names,
                    draw_tracks=True)

    # Loop through the video frames
    while cap.isOpened():
      # Read a frame from the video
      success, frame = cap.read()

      if success:
        # Run YOLOv8 tracking on the frame, persisting tracks between frames
        results = model.track(frame, persist=True, conf=0.6, iou=0.5)  # Adjust confidence/iou thresholds

        # Visualize the results on the frame
        annotated_frame = results[0].plot()
        
        
        
        # Resize frame to fit within the window while maintaining aspect ratio
        (h, w) = annotated_frame.shape[:2]
        r = window_width / float(w)
        dim = (int(w * r), int(h * r))
        resized_frame = cv2.resize(annotated_frame, dim, interpolation=cv2.INTER_AREA)
        # Update region points based on the new resized frame dimensions
        

        # Get current video time in milliseconds
        current_time = int(cap.get(cv2.CAP_PROP_POS_MSEC))

        # Convert milliseconds to minutes:seconds format (add leading zeros for seconds)
        minutes = str(int(current_time / 60000)).zfill(2)
        seconds = str(int((current_time % 60000) / 1000)).zfill(2)
        time_text = f"{minutes}:{seconds}"
        # Add time text to the top left corner of the frame
        cv2.putText(resized_frame, time_text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        frame = counter.start_counting(resized_frame, results)
        video_writer.write(frame)


        # Handle keyboard controls for seeking (without waiting for a key press)
        if cv2.waitKey(1) == ord('a'):  # Left arrow - rewind 5 seconds
          current_time = max(0, current_time - 5000)
          cap.set(cv2.CAP_PROP_POS_MSEC, current_time)
        elif cv2.waitKey(1) == ord('d'):  # Right arrow - fast-forward 5 seconds
          current_time += 5000
          cap.set(cv2.CAP_PROP_POS_MSEC, current_time)
        elif cv2.waitKey(1) == ord('q'):  # Quit
          break

      else:
        # Break the loop if the end of the video is reached
        break

    # Release the video capture object and close the display window
    cap.release()
    cv2.destroyAllWindows()

