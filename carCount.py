import cv2
from ultralytics import YOLO

from datetime import timedelta
# from ultralytics import RTDETR
import supervision as sv
import tracker


# Load the  model
model = YOLO("yolov8n.pt")
# model = RTDETR('rtdetr-l.pt')
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

  current_time = 0
  
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
  class_counts = counter.class_counts
 
  
  
  while cap.isOpened():
    success, frame = cap.read()
    
    if success:
      results = model.track(frame, persist=True, conf=0.4, classes=[2, 3, 5, 7])  # Adjust confidence/iou thresholds
      
      
      annotated_frame = results[0].plot(labels=False)

      (h, w) = annotated_frame.shape[:2]
      r = window_width / float(w)
      dim = (int(w * r), int(h * r))
      resized_frame = cv2.resize(annotated_frame, dim, interpolation=cv2.INTER_AREA)

      current_time = int(cap.get(cv2.CAP_PROP_POS_MSEC))
      minutes = str(int(current_time / 60000)).zfill(2)
      seconds = str(int((current_time % 60000) / 1000)).zfill(2)
      time_text = f"{minutes}:{seconds}"
      cv2.putText(resized_frame, time_text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

      frame = counter.start_counting(resized_frame, results)
      video_writer.write(frame)

      if cv2.waitKey(1) & 0xFF == ord("q") or cv2.getWindowProperty('Ultralytics YOLOv8 Object Counter', cv2.WND_PROP_VISIBLE) < 1:  #break when hit "q" button
        break
    else:
      # Break the loop if the end of the video is reached
      break

  cap.release()
  cv2.destroyAllWindows()
