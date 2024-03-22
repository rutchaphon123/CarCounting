from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QWidget, QFileDialog, QMessageBox, QGridLayout,QRadioButton, QSizePolicy
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, Qt
from PySide6.QtCore import QPoint, Qt, QCoreApplication

import cv2
from carCount import RectPointsHandler, VideoHandler, startCarCounting

class CarCountingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Car Counting")
        self.resize(1280, 720)  # Set window size to 1280x720
        self.rect_points = RectPointsHandler()  # Instantiate RectPointsHandler
        self.video_handler = VideoHandler()  # Instantiate VideoHandler
        self.rect_points_toCounting = []
        self.cap = None  # Video capture object
        self.video_label = QLabel()
        self.video_scale_factor = 1.0  # Initial scale factor
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QGridLayout(central_widget)
        layout.setColumnStretch(0,1)
        layout.setRowStretch(0,1)
        self.video_label.setStyleSheet("border: 3px solid black")
        layout.addWidget(self.video_label,0,0,4,1)
        
        
        self.select_mode = QLabel("Select mode line/rectangle")

        self.select_mode.setAlignment(Qt.AlignCenter)  # Align text to the center
        layout.addWidget(self.select_mode,0,1)
        self.b1 = QRadioButton("rectangle")
        self.b1.setChecked(True)
        self.b1.toggled.connect(lambda:self.btnstate(self.b1))

        layout.addWidget(self.b1,1,1)
        
        self.b2 = QRadioButton("line")
        self.b2.toggled.connect(lambda:self.btnstate(self.b2))

        layout.addWidget(self.b2,2,1)
        
        

      
        self.reset_button = QPushButton("Reset")
        self.reset_button.setStyleSheet("QPushButton { font-size: 14px; padding: 5px 10px; }")
        self.reset_button.clicked.connect(self.reset_drawing)

        layout.addWidget(self.reset_button,3,1)


        
        self.label = QLabel("Please select video:")
        self.label.setAlignment(Qt.AlignCenter)  # Align text to the center
        
        layout.addWidget(self.label,4,0,1,2)
        
        
        self.select_video_button = QPushButton("Choose Video")
        self.select_video_button.setStyleSheet("QPushButton { font-size: 14px; padding: 5px 10px; }")
        self.select_video_button.clicked.connect(self.select_video)
        layout.addWidget(self.select_video_button,5,0,1,2)

        
        self.start_counting_button = QPushButton("Start Car Counting")
        self.start_counting_button.setStyleSheet("QPushButton { font-size: 14px; padding: 5px 10px; }")
        self.start_counting_button.clicked.connect(self.start_car_counting)
        layout.addWidget(self.start_counting_button,6,0,1,2)
        
    def btnstate(self,b):
        
        if b.text() == "rectangle":
            if b.isChecked() == True:
                print(b.text()+ " is selected")
            else:
                print(b.text()+ " is selected")
                    
        if b.text() == "line":
            if b.isChecked() == True:
                print(b.text()+ " is selected")
            else:
                print(b.text()+ " is selected")
                
    def select_video(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Video Files (*.mp4 *.avi)")
        if filename:
            self.video_handler.set_video_path(filename)
            self.cap = cv2.VideoCapture(filename)
            self.update_frame()

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            print("Video stopped.")
            self.cap.release()
            return

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Resize the frame to fit within a 1280x720 window
        target_width, target_height = 1280, 720
        frame_resized = cv2.resize(frame_rgb, (target_width, target_height))

        q_img = QImage(frame_resized.data, target_width, target_height, target_width * 3, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        self.video_label.setPixmap(pixmap)

        self.rect_points_toCounting = []

        # Handle mouse clicks on the video label
        self.video_label.mousePressEvent = self.on_mouse_click


    def on_mouse_click(self, event):
        # Get the position of the click relative to the video label
        position = event.position()
        x = int(position.x())
        y = int(position.y())  
        print(f"x: {x} y: {y}")
        # Get the size of the video frame
        frame_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        frame_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

        # Calculate the scale factors for converting label coordinates to frame coordinates
        label_width = self.video_label.width()
        label_height = self.video_label.height()
        scale_x = frame_width / label_width
        scale_y = frame_height / label_height

        # Convert label click position to video frame coordinates
        frame_x = int(x * scale_x)
        frame_y = int(y * scale_y)

        # Add the frame coordinates to the list of points for drawing the rectangle
        self.rect_points_toCounting.append(frame_x)
        self.rect_points_toCounting.append(frame_y)

        self.rect_points.add_rect_point(x)
        self.rect_points.add_rect_point(y)
        print(self.rect_points.rect_points)
        # Draw a circle at the clicked point on the video label
        circle_radius = 3
        pixmap = self.video_label.pixmap().copy()  # Create a copy of the pixmap to draw on
        painter = QPainter(pixmap)
        painter.setPen(QPen(Qt.red))
        painter.drawEllipse(QPoint(x, y), circle_radius, circle_radius)
        
        if len(self.rect_points.rect_points) >= 4:
            start_x, start_y = self.rect_points.rect_points[-4], self.rect_points.rect_points[-3]  # Unpack start point coordinates
            end_x, end_y = self.rect_points.rect_points[-2], self.rect_points.rect_points[-1]  # Unpack end point coordinates
            painter.setPen(QPen(Qt.green))  # Change color and style as desired
            painter.drawLine(QPoint(start_x, start_y), QPoint(end_x, end_y))
            if len(self.rect_points.rect_points) == 8:
                painter.drawLine(QPoint(self.rect_points.rect_points[-2], self.rect_points.rect_points[-1]),
                                 QPoint(self.rect_points.rect_points[0], self.rect_points.rect_points[1]))
                self.rect_points.rect_points = []   
                # Reset the mousePressEvent to enable clicking again
                self.video_label.mousePressEvent = None
                
                
                
        
        painter.end()  # End the painting operation
        self.video_label.setPixmap(pixmap)  # Update the label pixmap
        


    def reset_drawing(self):
        # Clear the rectangle points
        self.rect_points.rect_points = []
        self.rect_points_toCounting = []

        # Clear the drawn rectangle and video label
        pixmap = self.video_label.pixmap()  # Get the current pixmap
        painter = QPainter(pixmap)

        # Clear the video label by filling it with a transparent color
        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        painter.fillRect(self.video_label.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        # End painting
        painter.end()

        # Draw the cleared pixmap on the video label
        self.video_label.setPixmap(pixmap)



    def start_car_counting(self):
        if self.video_handler.video_path:
            if len(self.rect_points_toCounting) < 4:
                self.show_message_box("Incomplete Rectangle", "Please select at least four points to define a rectangle.")
                return
            startCarCounting(self.video_handler.video_path, self.rect_points_toCounting)
        else:
            print("Please select a video first.")

    def show_message_box(self, title, message):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec()

if __name__ == "__main__":
    app = QApplication([])
    car_counting_app = CarCountingApp()
    car_counting_app.show()
    app.exec()
