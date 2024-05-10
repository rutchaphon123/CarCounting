import cv2
from ultralytics import YOLO

from datetime import timedelta
from ultralytics import RTDETR
import supervision as sv
import tracker, csv, datetime, os


# Load the  model
# model = YOLO("yolov8s.pt")
model = YOLO('vehicle_detection.pt')
# model = NAS('yolo_nas_s.pt')
class RectPointsHandler:
  def __init__(self):
    self.rect_points = []

  def add_rect_point(self, point):
    self.rect_points.append(point)

class VideoHandler:
  def __init__(self):
    self.video_path = None
    self.video_writer_path = None

  def set_video_path(self, video_path):
    self.video_path = video_path
    print(f"Video path original video at {video_path} .")
  def save_video_path(self, video_writer_path):
    self.video_writer_path = video_writer_path
    print(f"Video path save video at {video_writer_path} .")


class csvHandler:
    def __init__(self):
        self.csv_writer_path = None
    def export_to_csv(self, data, filename):
        output_dir = "./output/csv/"
        os.makedirs(output_dir, exist_ok=True)  # Create the directory if it doesn't exist
        
        current_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        csv_filename = f"{filename}_{current_datetime}.csv"
        csv_filepath = os.path.join(output_dir, csv_filename)

        with open(csv_filepath, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Track ID', 'Class', 'Speed (km/hr)', 'Time'])

            for track_id, track_data in data.items():
                class_name = track_data["class_name"]
                speed = track_data["speed"]
                time_data = track_data["time_data"]
                writer.writerow([track_id, class_name, speed, time_data])

        print(f"CSV file '{csv_filepath}' written successfully.")

def get_video_info(video_path):
  # Extracting information about the video
  video_info = sv.VideoInfo.from_video_path(video_path)
  width, height, fps, total_frames = video_info.width, video_info.height, video_info.fps, video_info.total_frames
  
  # Calculating the length of the video by dividing the total number of frames by the frame rate and rounding to the nearest second
  video_length = timedelta(seconds=round(total_frames / fps))
  
  # Print out the video resolution, fps, and length
  print(f"\033[1mVideo Resolution:\033[0m ({width}, {height})")
  print(f"\033[1mFPS:\033[0m {fps}")
  print(f"\033[1mLength:\033[0m {video_length}")


def get_time_info(cap):
  current_time = int(cap.get(cv2.CAP_PROP_POS_MSEC))
  hours = str(int(current_time / 3600000)).zfill(2)
  minutes = str(int(current_time / 60000)).zfill(2)
  seconds = str(int((current_time % 60000) / 1000)).zfill(2)
  time_info = [hours, minutes, seconds]
  return time_info

def start_car_counting(video_path, video_writer_path, rect_points, speed_estimation_btn):
  print(f"Start counting cars path at {video_path}")
  while not video_path:
    pass

  get_video_info(video_path)
  cap = cv2.VideoCapture(video_path)

  assert cap.isOpened(), "Error reading video file" 
  
  region_points = [(rect_points[i], rect_points[i+1]) for i in range(0, len(rect_points), 2)]
  print(region_points)
  
  window_width = 1280
  window_height = 720
  
  video_writer = cv2.VideoWriter(video_writer_path,
              cv2.VideoWriter_fourcc(*'mp4v'),
              10,
              (window_width, window_height))
  #add counter
  counter = tracker.ObjectCounter()
  counter.set_args(view_img=True,
          reg_pts=region_points,
          classes_names=model.names,
          draw_tracks=False,
          speed_estimation=speed_estimation_btn,)
  
  all_data = counter.object_info
  
  
  while cap.isOpened():
    success, frame = cap.read()
    
    (h, w) = frame.shape[:2]
    
    if success:
      
      # Resize frame based on desired output width or maintain aspect ratio
      if window_width:
        r = window_width / float(w)  # Use desired width for resizing
      else:
          # Maintain aspect ratio for resizing
          max_dim = 1024  # Adjust as needed to limit maximum dimension
          if max(h, w) > max_dim:
            r = max_dim / float(max(h, w))
          else:
            r = 1  # No resizing needed if both dimensions are within limit
            
      dim = (int(w * r), int(h * r))
      resized_frame = cv2.resize(frame, dim, interpolation=cv2.INTER_AREA)
      results = model.track(resized_frame, persist=True, conf=0.4, classes=[0, 1, 2, 3, 5, 6, 7])  # Adjust confidence/iou thresholds
      annotated_frame = results[0].plot(labels=False)

      time_info = get_time_info(cap)
      time_text = f"{time_info[0]}:{time_info[1]}:{time_info[2]}"
      cv2.putText(annotated_frame, time_text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
      
      frame = counter.start_counting(annotated_frame, results, time_info)
      video_writer.write(frame)

      if cv2.waitKey(1) & 0xFF == ord("q") or cv2.getWindowProperty("Vehicle counting", cv2.WND_PROP_VISIBLE) < 1:  #break when hit "q" button
        break
    else:
      # Break the loop if the end of the video is reached
      break

  cap.release()
  cv2.destroyAllWindows()
  
  csv_writer = csvHandler()
  csv_writer.export_to_csv(all_data,"output_csv")