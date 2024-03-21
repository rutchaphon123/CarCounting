from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QFileDialog, QMessageBox
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, Qt
from PySide6.QtCore import QPoint, Qt, QCoreApplication

import cv2
from carCount import RectPointsHandler, VideoHandler, startCarCounting

class CarCountingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Car Counting")
        self.rect_points = RectPointsHandler()  # Instantiate RectPointsHandler
        self.video_handler = VideoHandler()  # Instantiate VideoHandler
        self.rect_points_toCounting = []
        self.cap = None  # Video capture object
        self.video_label = QLabel()

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        

        layout.addWidget(self.video_label)
        
        self.label = QLabel("Please select video:")
        layout.addWidget(self.label)

        self.select_video_button = QPushButton("Choose Video")
        self.select_video_button.setStyleSheet("QPushButton { font-size: 14px; padding: 5px 10px; }")
        self.select_video_button.clicked.connect(self.select_video)
        layout.addWidget(self.select_video_button)

        self.reset_button = QPushButton("Reset")
        self.reset_button.setStyleSheet("QPushButton { font-size: 14px; padding: 5px 10px; }")
        self.reset_button.clicked.connect(self.reset_drawing)
        layout.addWidget(self.reset_button)

        self.start_counting_button = QPushButton("Start Car Counting")
        self.start_counting_button.setStyleSheet("QPushButton { font-size: 14px; padding: 5px 10px; }")
        self.start_counting_button.clicked.connect(self.start_car_counting)
        layout.addWidget(self.start_counting_button)

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
        height, width, channel = frame_rgb.shape
        bytes_per_line = 3 * width
        q_img = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        self.video_label.setPixmap(pixmap)
        self.video_label.adjustSize()
        self.rect_points_toCounting = []

        # Handle mouse clicks on the video label
        self.video_label.mousePressEvent = self.on_mouse_click

    def on_mouse_click(self, event):
        # Get the position of the click relative to the video label
        position = event.position()
        x = int(position.x())
        y = int(position.y())  # Adjust y-coordinate
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
            painter.setPen(QPen(Qt.blue))  # Change color and style as desired
            painter.drawLine(QPoint(start_x, start_y), QPoint(end_x, end_y))
            if len(self.rect_points.rect_points) == 8:
                painter.drawLine(QPoint(self.rect_points.rect_points[-2], self.rect_points.rect_points[-1]),
                                 QPoint(self.rect_points.rect_points[0], self.rect_points.rect_points[1]))
                self.rect_points.rect_points = []   
                
                
                
        
        painter.end()  # End the painting operation
        self.video_label.setPixmap(pixmap)  # Update the label pixmap
        


    def reset_drawing(self):
        self.rect_points.rect_points = []
        self.rect_points_toCounting = []
          # Defer clearing the drawn lines and dots from the GUI to the next event loop iteration
        QCoreApplication.processEvents()

        # Clear the drawn lines and dots from the GUI
        pixmap = self.video_label.pixmap().copy()  # Create a copy of the pixmap
        painter = QPainter(pixmap)
        painter.eraseRect(self.video_label.rect())  # Clear the pixmap
        self.video_label.setPixmap(pixmap)  # Update the label with the cleared pixmap

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
