import cv2
import os, sys
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, QWidget, QFileDialog, 
QDialog, QMessageBox, QGridLayout, QVBoxLayout, QHBoxLayout,QCheckBox ,QRadioButton, QMenuBar, QMenu, QSplashScreen)
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, Qt, QAction, QFont, QIcon
from PySide6.QtCore import QPoint, QSize
from carCount import RectPointsHandler, VideoHandler, start_car_counting

default_selected_vehicles = [1, 2, 3, 4]  # Default selections
selected_vehicles = default_selected_vehicles.copy()

class VehicleSelectionWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.vehicle_types = {
            "bicycle": 0,
            "bus": 1,
            "car": 2,
            "motorcycle": 3,
            "pedestrian": 4,
            "tricycle": 5,
            "truck": 6,
            "van": 7,
        }
        self.checkboxes = {}
        self.create_checkboxes()

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.get_selected_vehicles)

        # Set a fixed size for the window (adjust width and height as needed)
        self.setFixedSize(300, 300)

        layout = QVBoxLayout(self)
        for checkbox in self.checkboxes.values():
            layout.addWidget(checkbox)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.ok_button)
        layout.addLayout(button_layout)
        
        self.setWindowTitle("Vehicle Selection")
        print(selected_vehicles)

    def create_checkboxes(self):
        for vehicle_name, vehicle_id in self.vehicle_types.items():
            checkbox = QCheckBox(vehicle_name)
            # Set checkbox state based on current selected_vehicles
            checkbox.setChecked(vehicle_id in selected_vehicles)
            checkbox.toggled.connect(lambda state, name=vehicle_name: self.update_selection(state, name))
            self.checkboxes[vehicle_name] = checkbox

    def update_selection(self, state, vehicle_name):
        vehicle_id = self.vehicle_types[vehicle_name]
        if state:
            if vehicle_id not in selected_vehicles:
                selected_vehicles.append(vehicle_id)
        else:
            selected_vehicles.remove(vehicle_id)

    def get_selected_vehicles(self):
        print(f"Selected vehicles: {selected_vehicles}")
        self.accept()

        
        
class CarCountingApp(QMainWindow):
    def __init__(self):
        super().__init__()

       
        self.setWindowTitle("Car Counting")
        self.resize(1280, 720)
        self.setWindowIcon(QIcon('./img/eye_icon.ico'))
        self.rect_points = RectPointsHandler()
        self.video_handler = VideoHandler()
        self.rect_points_to_counting = []
        self.coordinate_scale = []
        self.cap = None
        self.video_label = QLabel()
        self.video_scale_factor = 1.0
        self.speed_estimation = False
        self.update_frame()
        self.init_ui()
        self.setMouseTracking(True)  # Enable mouse tracking for the widget
        self.mouseMoveEvent = self.handle_mouse_move
        
    def init_ui(self):

        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QGridLayout(central_widget)

        menu_bar = QMenuBar()
        file_menu = QMenu("File", self)
        help_menu = QMenu("Help", self)
        menu_bar.addMenu(file_menu)
        menu_bar.addMenu(help_menu)
        self.setMenuBar(menu_bar)

        open_action = QAction("Open Video", self)
        open_action.triggered.connect(self.select_video)
        open_action.setShortcut("Ctrl+O")
        file_menu.addAction(open_action)
        
        save_action = QAction("Save Video As...", self)
        save_action.triggered.connect(self.select_save_video)
        save_action.setShortcut("Ctrl+S")
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        exit_action = QAction("&Exit", self)
        exit_action.triggered.connect(self.close_application)
        file_menu.addAction(exit_action)
        

        layout.setColumnStretch(0, 1)
        layout.setRowStretch(0, 1)        

        self.video_label.setStyleSheet("color: rgba(0, 0, 0, 0.6); border: 3px solid #3D3B40; ")
        layout.addWidget(self.video_label, 0, 0, 7, 1)
        self.video_label.setMaximumSize(QSize(1280, 720))
        self.video_label.setMinimumSize(QSize(1280, 720))
        
        self.select_mode = QLabel("")
        self.select_mode.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.select_mode, 0, 1)
        self.select_mode.setMaximumWidth(300)
        self.select_mode.setMaximumHeight(390)
        

        self.select_mode = QLabel("Select mode rectangle/line and speed")
        self.select_mode.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.select_mode, 1, 1)
        
        self.checkbox2 = QCheckBox("detect for speed")
        self.checkbox2.stateChanged.connect(self.checkbox_state)
        layout.addWidget(self.checkbox2, 2, 1)

        self.b1 = QRadioButton("rectangle")
        self.b1.setChecked(True)
        self.b1.toggled.connect(lambda: self.btnstate(self.b1))
        layout.addWidget(self.b1, 3, 1)

        self.b2 = QRadioButton("line")
        self.b2.toggled.connect(lambda: self.btnstate(self.b2))
        layout.addWidget(self.b2, 4, 1)
        
        self.select_class_button = QPushButton("Select class")
        self.select_class_button.clicked.connect(self.show_vehicle_selection_window)
        layout.addWidget(self.select_class_button, 5, 1)


        self.reset_button = QPushButton("Reset")
        self.reset_button.setStyleSheet("QPushButton { font-size: 14px; padding: 5px 10px; }")
        self.reset_button.clicked.connect(self.reset_drawing)
        layout.addWidget(self.reset_button, 6, 1)
        
        button_style = "{ font-size: 14px; padding: 5px 10px; border-radius: 10px; border: 1px solid black}"
        button_style_hover = "{ background-color: #CAF4FF; border: 1px solid #6AD4DD}"
        button_style_disable = "{ background-color: rgba(163, 245, 86, 0.4); border: 1px solid rgba(0, 0, 0, 0.6)}"
        
        button_style_start = "{ font-size: 14px; padding: 5px 10px; background-color: #41B06E; border-radius: 10px; border: 1px solid black}"
        button_style_start_hover = "{ background-color: #8DECB4; }"
       
        self.label = QLabel("Please select video:")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label, 7, 0, 1, 2)
        
        self.select_video_button = QPushButton("Choose Video")
        self.select_video_button.setStyleSheet(f"QPushButton {button_style} QPushButton:hover {button_style_hover}")
        self.select_video_button.clicked.connect(self.select_video)
        layout.addWidget(self.select_video_button, 8, 0, 1, 2)

        self.select_save_video_button = QPushButton("Save Video As...")
        self.select_save_video_button.setStyleSheet(f"QPushButton {button_style} QPushButton:hover {button_style_hover}")
        self.select_save_video_button.clicked.connect(self.select_save_video)
        layout.addWidget(self.select_save_video_button, 9, 0, 1, 2)
        
        self.start_counting_button = QPushButton("Start Car Counting")
        self.start_counting_button.setStyleSheet(f"QPushButton {button_style_start} QPushButton:hover {button_style_start_hover} QPushButton:disabled {button_style_disable}")
        self.start_counting_button.clicked.connect(self.start_car_counting)
        layout.addWidget(self.start_counting_button, 10, 0, 1, 2)

        self.start_counting_button.setEnabled(False)
        self.reset_button.setEnabled(False)

    def btnstate(self, b):
        if b.text() == "rectangle" and b.isChecked():
            self.video_label.mousePressEvent = self.draw_rectangle
            return "rectangle"
        elif b.text() == "line" and b.isChecked():
            self.video_label.mousePressEvent = self.draw_line
            return "line"
    
    def checkbox_state(self):
        if self.checkbox2.isChecked():
            self.speed_estimation = True    
        else:
            self.speed_estimation = False
            
    def show_vehicle_selection_window(self):
        vehicle_window = VehicleSelectionWindow(self)
        vehicle_window.exec()
            

    def select_video(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Video Files (*.mp4 *.avi)")
        if filename:
            self.video_handler.set_video_path(filename)
            self.cap = cv2.VideoCapture(filename)
            self.update_frame()
            self.label.setText(f"Video path: {self.video_handler.video_path}")
            self.start_counting_button.setEnabled(True)
            self.reset_button.setEnabled(True)
        elif self.video_handler.video_path == None:
            self.start_counting_button.setEnabled(False)
            self.reset_button.setEnabled(False)


    def select_save_video(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Video File", "", "Video Files (*.mp4 *.avi)")
        if filename:
            self.video_handler.save_video_path(filename)
            self.start_counting_button.setEnabled(True)
            self.reset_button.setEnabled(True)
        elif self.video_handler.video_path == None:
            self.start_counting_button.setEnabled(False)
            self.reset_button.setEnabled(False)
            
    def close_application(self):
        """Exits the program gracefully."""
        self.close()

    def update_frame(self):
        if not self.cap:
            self.video_label.setText("Please select video")
            self.video_label.setAlignment(Qt.AlignCenter)
            font = QFont()
            font.setPointSize(20)
            self.video_label.setFont(font)
            return

        ret, frame = self.cap.read()
        if not ret:
            print("Video stopped.")
            self.cap.release()
            return

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        target_width, target_height = 1280, 720
        frame_resized = cv2.resize(frame_rgb, (target_width, target_height))
        #make capture image
        q_img = QImage(frame_resized.data, target_width, target_height, target_width * 3, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        self.video_label.setPixmap(pixmap)
        
        #check current state
        if self.b1.text() == "rectangle" and self.b1.isChecked():
            self.btnstate(self.b1)
        else:
            self.btnstate(self.b2)

        self.rect_points_to_counting = []
  
    def handle_mouse_move(self, event):
        position = event.position()
       
        x = int(position.x())
        y = int(position.y())

        # Your logic to handle mouse move event
        print("Mouse position:", x, y)
        # Call any function or perform any action you want with x and y  
    
    def draw_rectangle(self, event):
        position = event.position()
        x = int(position.x())
        y = int(position.y())
        
        print(f"x:{x}, y:{y}")

        self.rect_points_to_counting.append(x)
        self.rect_points_to_counting.append(y)

        self.rect_points.add_rect_point(x)
        self.rect_points.add_rect_point(y)

        if len(self.rect_points.rect_points) == 2:
            self.b2.setEnabled(False)

        circle_radius = 3
        pixmap = self.video_label.pixmap().copy()
        painter = QPainter(pixmap)
        painter.setPen(QPen(Qt.red))
        painter.drawEllipse(QPoint(x, y), circle_radius, circle_radius)

        if len(self.rect_points.rect_points) >= 4:
            start_x, start_y = self.rect_points.rect_points[-4], self.rect_points.rect_points[-3]
            end_x, end_y = self.rect_points.rect_points[-2], self.rect_points.rect_points[-1]
            painter.setPen(QPen(Qt.green, 3))
            painter.drawLine(QPoint(start_x, start_y), QPoint(end_x, end_y))
            if len(self.rect_points.rect_points) == 8:
                painter.drawLine(QPoint(self.rect_points.rect_points[-2], self.rect_points.rect_points[-1]),
                                 QPoint(self.rect_points.rect_points[0], self.rect_points.rect_points[1]))
                self.rect_points.rect_points = []
                self.video_label.mousePressEvent = None

        painter.end()
        self.video_label.setPixmap(pixmap)

    def draw_line(self, event):
        position = event.position()
        x = int(position.x())
        y = int(position.y())

        self.rect_points_to_counting.append(x)
        self.rect_points_to_counting.append(y)

        self.rect_points.add_rect_point(x)
        self.rect_points.add_rect_point(y)

        if len(self.rect_points.rect_points) == 2:
            self.b1.setEnabled(False)

        circle_radius = 3
        pixmap = self.video_label.pixmap().copy()
        painter = QPainter(pixmap)
        painter.setPen(QPen(Qt.red))
        painter.drawEllipse(QPoint(x, y), circle_radius, circle_radius)

        if len(self.rect_points.rect_points) >= 4:
            start_x, start_y = self.rect_points.rect_points[-4], self.rect_points.rect_points[-3]
            end_x, end_y = self.rect_points.rect_points[-2], self.rect_points.rect_points[-1]
            painter.setPen(QPen(Qt.green, 3))
            painter.drawLine(QPoint(start_x, start_y), QPoint(end_x, end_y))
            self.rect_points.rect_points = []
            self.video_label.mousePressEvent = None

        painter.end()
        self.video_label.setPixmap(pixmap)

    def reset_drawing(self):
        self.cap = None
        self.video_handler.set_video_path(None)
        self.rect_points.rect_points = []
        self.rect_points_to_counting = []

        pixmap = self.video_label.pixmap()
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        painter.fillRect(self.video_label.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.end()

        self.video_label.setPixmap(pixmap)
        self.label.setText("Please select video")
        self.start_counting_button.setEnabled(False)
        self.b1.setEnabled(True)
        self.b2.setEnabled(True)

    def start_car_counting(self):
        if self.video_handler.video_path:
            if len(self.rect_points_to_counting) < 4:
                self.show_message_box("Incomplete Rectangle", "Please select at least four points to define a rectangle.")
                return
            if not self.video_handler.video_writer_path:
                default_dir = "./output/"
                os.makedirs(default_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"output_{timestamp}.avi"
                self.video_handler.video_writer_path = os.path.join(default_dir, filename)
            start_car_counting(self.video_handler.video_path,
                               self.video_handler.video_writer_path,
                               self.rect_points_to_counting,
                               self.speed_estimation,
                               selected_vehicles)
        else:
            self.show_message_box("Video not select", "Please select a video first.")

    def show_message_box(self, title, message):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec()

if __name__ == "__main__":
  app = QApplication([])

  # Create and display the splash screen (moved before CarCountingApp)
  splash_pix = QPixmap('./img/splashscreen.JPG')
  splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
  splash.setWindowFlags(Qt.WindowStaysOnTopHint)
  splash.setEnabled(False)
  splash.show()
  splash.showMessage("Loaded modules")
  app.processEvents()

  # Now create and show the CarCountingApp after splash screen
  car_counting_app = CarCountingApp()
  car_counting_app.show()
  splash.finish(car_counting_app)
  sys.exit(app.exec())
