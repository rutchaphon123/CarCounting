# Ultralytics YOLO 🚀, AGPL-3.0 license

from collections import defaultdict

import cv2, time
from ultralytics.utils.checks import check_imshow, check_requirements
from ultralytics.utils.plotting import Annotator, colors

check_requirements("shapely>=2.0.0")

from shapely.geometry import LineString, Point, Polygon


class ObjectCounter:
    """A class to manage the counting of objects in a real-time video stream based on their tracks."""

    def __init__(self):
        """Initializes the Counter with default values for various tracking and counting parameters."""

        # Mouse events
        self.is_drawing = False
        self.selected_point = None
        self.class_counts = defaultdict(int)  # Initialize counts for each class
        # Region & Line Information
        self.reg_pts = [(20, 400), (1260, 400)]
        self.line_dist_thresh = 15
        self.counting_region = None
        self.region_color = (255, 0, 255)
        self.region_thickness = 5

        # Image and annotation Information
        self.im0 = None
        self.tf = None
        self.view_img = False
        self.view_in_counts = True
        self.view_out_counts = True

        self.names = None  # Classes names
        self.annotator = None  # Annotator
        self.window_name = "Vehicle counting"
        
        #All object information
        self.object_info = {}

        # Object counting Information
        self.in_counts = 0
        self.out_counts = 0
        self.counting_dict = {}
        self.track_timestamps = {}
        self.count_txt_thickness = 0
        self.count_txt_color = (0, 0, 0)
        self.count_bg_color = (255, 255, 255)
        
        # Speed estimator information
        self.current_time = 0
        self.dist_data = {}
        self.trk_idslist = []
        self.spdl_dist_thresh = 10
        self.trk_previous_times = {}
        self.trk_previous_points = {}
        self.trk_previous_times = {}



        # Tracks info
        self.track_history = defaultdict(list)
        self.track_thickness = 2
        self.draw_tracks = False
        self.track_color = (0, 255, 0)

        # Check if environment support imshow
        self.env_check = check_imshow(warn=True)

    def set_args(
        self,
        classes_names,
        reg_pts,
        count_reg_color=(255, 0, 255),
        line_thickness=2,
        track_thickness=2,
        view_img=False,
        view_in_counts=True,
        view_out_counts=True,
        draw_tracks=False,
        speed_estimation=False,
        count_txt_thickness=2,
        count_txt_color=(0, 0, 0),
        count_color=(255, 255, 255),
        track_color=(0, 255, 0),
        region_thickness=5,
        line_dist_thresh=15,
    ):
        """
        Configures the Counter's image, bounding box line thickness, and counting region points.

        Args:
            line_thickness (int): Line thickness for bounding boxes.
            view_img (bool): Flag to control whether to display the video stream.
            view_in_counts (bool): Flag to control whether to display the incounts on video stream.
            view_out_counts (bool): Flag to control whether to display the outcounts on video stream.
            reg_pts (list): Initial list of points defining the counting region.
            classes_names (dict): Classes names
            track_thickness (int): Track thickness
            draw_tracks (Bool): draw tracks
            count_txt_thickness (int): Text thickness for object counting display
            count_txt_color (RGB color): count text color value
            count_color (RGB color): count text background color value
            count_reg_color (RGB color): Color of object counting region
            track_color (RGB color): color for tracks
            region_thickness (int): Object counting Region thickness
            line_dist_thresh (int): Euclidean Distance threshold for line counter
        """
        self.tf = line_thickness
        self.view_img = view_img
        self.view_in_counts = view_in_counts
        self.view_out_counts = view_out_counts
        self.track_thickness = track_thickness
        self.draw_tracks = draw_tracks
        self.speed_estimation = speed_estimation
        # Region and line selection
        if len(reg_pts) == 2:
            print("Line Counter Initiated.")
            self.reg_pts = reg_pts
            self.counting_region = LineString(self.reg_pts)
        elif len(reg_pts) >= 3:
            print("Region Counter Initiated.")
            self.reg_pts = reg_pts
            self.counting_region = Polygon(self.reg_pts)
        else:
            print("Invalid Region points provided, region_points must be 2 for lines or >= 3 for polygons.")
            print("Using Line Counter Now")
            self.counting_region = LineString(self.reg_pts)

        self.names = classes_names
        self.track_color = track_color
        self.count_txt_thickness = count_txt_thickness
        self.count_txt_color = count_txt_color
        self.count_color = count_color
        self.region_color = count_reg_color
        self.region_thickness = region_thickness
        self.line_dist_thresh = line_dist_thresh

    def mouse_event_for_region(self, event, x, y, flags, params):
        """
        This function is designed to move region with mouse events in a real-time video stream.

        Args:
            event (int): The type of mouse event (e.g., cv2.EVENT_MOUSEMOVE, cv2.EVENT_LBUTTONDOWN, etc.).
            x (int): The x-coordinate of the mouse pointer.
            y (int): The y-coordinate of the mouse pointer.
            flags (int): Any flags associated with the event (e.g., cv2.EVENT_FLAG_CTRLKEY,
                cv2.EVENT_FLAG_SHIFTKEY, etc.).
            params (dict): Additional parameters you may want to pass to the function.
        """
        if event == cv2.EVENT_LBUTTONDOWN:
            for i, point in enumerate(self.reg_pts):
                if (
                    isinstance(point, (tuple, list))
                    and len(point) >= 2
                    and (abs(x - point[0]) < 10 and abs(y - point[1]) < 10)
                ):
                    self.selected_point = i
                    self.is_drawing = True
                    break

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.is_drawing and self.selected_point is not None:
                self.reg_pts[self.selected_point] = (x, y)
                self.counting_region = Polygon(self.reg_pts)

        elif event == cv2.EVENT_LBUTTONUP:
            self.is_drawing = False
            self.selected_point = None
    

    
    def extract_and_process_tracks(self, tracks, time_info):
        """Extracts and processes tracks for object counting in a video stream."""

        # Annotator Init and region drawing
        self.annotator = Annotator(self.im0, self.tf, self.names)

        if tracks[0].boxes.id is not None:
            boxes = tracks[0].boxes.xyxy.cpu()
            classes = tracks[0].boxes.cls.cpu().tolist()
            track_ids = tracks[0].boxes.id.int().cpu().tolist()
            # Extract tracks
            for box, track_id, cls in zip(boxes, track_ids, classes):
                class_name = self.names[cls]
               

                # Draw bounding box
                if track_id not in self.trk_previous_times:
                    self.trk_previous_times[track_id] = time.time_ns()
                    centroid = Point((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)  # Calculate centroid
                    self.trk_previous_points[track_id] = centroid
                else:
                    current_time = time.time_ns()
                    delta_time = (current_time - self.trk_previous_times[track_id]) / 1e9  # คำนวณ delta_time
                    centroid = Point((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)  # Calculate centroid
                    dist_diff = centroid.distance(self.trk_previous_points[track_id])
                    speed = (dist_diff / delta_time) * 3.6  # Convert speed to km/hr
                    self.dist_data[track_id] = speed
                    self.trk_previous_times[track_id] = current_time
                    self.trk_previous_points[track_id] = centroid
                    # Add speed to box label
                    if self.speed_estimation:
                        self.annotator.box_label(box, label=f"{track_id}:{class_name}:{speed:.2f} km/hr", color=colors(int(cls), True))
                    else:
                        self.annotator.box_label(box, label=f"{track_id}:{class_name}", color=colors(int(cls), True))

                # Draw Tracks
                track_line = self.track_history[track_id]
                track_line.append((float((box[0] + box[2]) / 2), float((box[1] + box[3]) / 2)))
                if len(track_line) > 30:
                    track_line.pop(0)

                # Draw track trails
                if self.draw_tracks:
                    self.annotator.draw_centroid_and_tracks(
                        track_line, color=self.track_color, track_thickness=self.track_thickness
                    )
                prev_position = self.track_history[track_id][-2] if len(self.track_history[track_id]) > 1 else None
                centroid = Point((box[:2] + box[2:]) / 2)
                if len(self.reg_pts) >= 3:  # any polygon
                    is_inside = self.counting_region.contains(centroid)
                    current_position = "in" if is_inside else "out"
                    if prev_position is not None:
                        if self.counting_dict[track_id] != current_position and is_inside:
                            self.in_counts += 1
                            self.counting_dict[track_id] = "in"
                            self.class_counts[class_name] += 1
                            self.track_timestamps[track_id] = f"{time_info[0]}:{time_info[1]}:{time_info[2]}"
                            #add speed and time to object
                            speed = self.dist_data.get(track_id, 0) if self.speed_estimation else None
                            time_data = self.track_timestamps.get(track_id,0)
                            
                            self.object_info.setdefault(track_id, {"class_name":class_name, "speed": speed, "time_data":time_data})
                            
                            print(f"all data: {self.object_info}")
                        elif self.counting_dict[track_id] != current_position and not is_inside:
                            self.out_counts += 1
                            self.counting_dict[track_id] = "out"
                            
                        else:
                            self.counting_dict[track_id] = current_position

                    else:
                        self.counting_dict[track_id] = current_position
                        
                   

                elif len(self.reg_pts) == 2:
                    if prev_position is not None:
                        is_inside = (box[0] - prev_position[0]) * (
                            self.counting_region.centroid.x - prev_position[0]
                        ) > 0
                        current_position = "in" if is_inside else "out"

                        if self.counting_dict[track_id] != current_position and is_inside:
                            self.in_counts += 1
                            self.counting_dict[track_id] = "in"
                            self.class_counts[class_name] += 1
                            self.track_timestamps[track_id] = f"{time_info[0]}:{time_info[1]}:{time_info[2]}:"
                        elif self.counting_dict[track_id] != current_position and not is_inside:
                            self.out_counts += 1
                            self.counting_dict[track_id] = "out"
                        else:
                            self.counting_dict[track_id] = current_position
                    else:
                        self.counting_dict[track_id] = None


        count_with_class = {class_name: count for class_name, count in self.class_counts.items()}
       
        # Display counts
        if count_with_class:
           # Adjust position and font size as needed
            self.annotator.display_analytics(im0 = self.im0, 
                                             text = count_with_class, 
                                             txt_color= self.count_txt_color, 
                                             bg_color= self.count_bg_color, 
                                             margin=10)
    def display_frames(self):
        """Display frame."""
        if self.env_check:
            self.annotator.draw_region(reg_pts=self.reg_pts, color=self.region_color, thickness=self.region_thickness)
            cv2.namedWindow(self.window_name)
            if len(self.reg_pts) == 4:  # only add mouse event If user drawn region
                cv2.setMouseCallback(self.window_name, self.mouse_event_for_region, {"region_points": self.reg_pts})
            cv2.imshow(self.window_name, self.im0)
            # Break Window
            if (cv2.waitKey(1) & 0xFF == ord("q")) or (cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1):
                return

    def start_counting(self, im0, tracks, time_info):
        """
        Main function to start the object counting process.

        Args:
            im0 (ndarray): Current frame from the video stream.
            tracks (list): List of tracks obtained from the object tracking process.
        """
        self.im0 = im0  # store image
        self.extract_and_process_tracks(tracks, time_info)  # draw region even if no objects

        if self.view_img:
            self.display_frames()
        return self.im0


if __name__ == "__main__":
    ObjectCounter()
