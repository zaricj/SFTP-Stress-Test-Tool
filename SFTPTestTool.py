import json
import os
import random
import sys
import time
import paramiko
import qdarktheme
import faulthandler
import threading
import psutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from PySide6.QtCore import QSettings, QThread, Signal, Slot
from PySide6.QtGui import QAction, QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QStatusBar
)

# Debugging help on weird exit code:
#faulthandler.enable() # Shows more "detailed" information if an exit code appears that is not 0

# Initialize current working directory
CURRENT_WORKING_DIR = os.getcwd()

# Dotenv configuration
load_dotenv(dotenv_path=os.path.join(CURRENT_WORKING_DIR, "_internal", "env", ".env"))

# SFTP Configuration
SFTP_HOST = os.getenv("GEIS_HOST")
SFTP_PORT = 22
SFTP_DIRECTORY = 'to_Geis'
SFTP_USER = os.getenv("GEIS_USER")
SFTP_PASS = os.getenv("GEIS_PASSWORD")
TEST_FILE = r'dummy_files\dummy_1.txt'


class ConfigManager:
    def __init__(self, parent, filename):
        """Initializes the ConfigManager with a specific JSON configuration file."""
        self.parent = parent
        self.filename = filename
        self.data = self._load_config()

    def _load_config(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                QMessageBox.warning(self.parent, "Load config warning", f"Warning: {self.filename} contains invalid JSON. Resetting configuration file.")
        
        # Reset if file is missing or corrupted
        self.reset_config()
        return {}

    def save_config(self):
        """Saves the current configuration to the JSON file."""
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

    def set(self, key, value):
        """Sets a configuration value and saves immediately."""
        self.data[key] = value
        self.save_config()

    def get(self, key, default=None):
        """Gets a configuration value, returning a default if the key doesn't exist."""
        return self.data.get(key, default)

    def delete(self, key):
        """Deletes a key from the configuration and saves the file."""
        if key in self.data:
            del self.data[key]
            self.save_config()

    def reset_config(self):
        """Resets the configuration file to an empty dictionary."""
        self.data = {}
        self.save_config()

    def switch_config_file(self, new_filename):
        """Switches to a different JSON configuration file and loads its data."""
        self.filename = new_filename
        self.data = self._load_config()
    
    def get_all_keys(self):
        """Gets all keys of configuration file in a list and returns them as list."""
        dict_keys = self.data.keys()
        return list(dict_keys)
    
class CustomAutoFillAction(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window  # Store the MainWindow instance
        
        # Initialize current working directory and theme file
        
        # Check if configuration file exists, if not create it
        self.check_configuration_file_exists(os.path.join(CURRENT_WORKING_DIR, "_internal", "configuration"))
        
        # Initialize configuration file
        CONFIGURATION_CUSTOM_ACTION_FILE = os.path.join(CURRENT_WORKING_DIR, "_internal", "configuration", "custom_actions.json")

        self.custom_action_config = ConfigManager(self, CONFIGURATION_CUSTOM_ACTION_FILE)
        
        # Initialize settings for window geometry
        self.settings = QSettings("CustomAction", "Jovan") # Settings to save current location of the windows on exit
        geometry = self.settings.value("action_geometry", bytes())
        icon = QIcon(os.path.join(CURRENT_WORKING_DIR, "_internal", "icon", "sftp_icon.ico"))
        
        # Set window properties
        self.setWindowTitle("Custom Autofill Action Manager")
        self.setWindowIcon(icon)
        self.setFixedHeight(280)
        self.restoreGeometry(geometry)
        self.initUI()
        
        # Populate combobox with keys from the configuration file
        self.update_combobox()
    
    def initUI(self):
        main_layout = QVBoxLayout()
        form_layout = QFormLayout()
        hor_layout = QHBoxLayout()

        # Elements
        self.description = QLabel("Here you can use the inputs below to create a custom autofill action:")
        self.action_name_input = QLineEdit()
        self.action_name_input.setPlaceholderText("Enter a name for the action")
        self.host_action_input = QLineEdit()
        self.host_action_input.setPlaceholderText("Enter the host address")
        self.directory_action_input = QLineEdit()
        self.directory_action_input.setPlaceholderText("Enter the directory")
        self.username_action_input = QLineEdit()
        self.username_action_input.setPlaceholderText("Enter the username")
        self.password_action_input = QLineEdit()
        self.password_action_input.setPlaceholderText("Enter the password")
        self.password_action_input.setEchoMode(QLineEdit.Password)
        self.save_button = QPushButton("Save Action")
        self.save_button.clicked.connect(self.save_custom_action)

        # Elements for horizontal layout
        self.combobox_label = QLabel("Select an existing action:")
        self.custom_autofill_actions_combobox = QComboBox()
        self.custom_autofill_actions_combobox.setDisabled(True)
        self.load_action_button = QPushButton("Load Action")
        self.load_action_button.clicked.connect(self.load_custom_action)
        self.delete_action_button = QPushButton("Delete Action")
        self.delete_action_button.clicked.connect(self.delete_custom_action)

        # Add elements to horizontal layout
        hor_layout.addWidget(self.combobox_label)
        hor_layout.addWidget(self.custom_autofill_actions_combobox, stretch=1)
        hor_layout.addWidget(self.load_action_button)
        hor_layout.addWidget(self.delete_action_button)

        # Add elements to form layout with labels
        form_layout.addRow(QLabel("Description:"), self.description)
        form_layout.addRow(QLabel("Action Name:"), self.action_name_input)
        form_layout.addRow(QLabel("Host:"), self.host_action_input)
        form_layout.addRow(QLabel("Directory:"), self.directory_action_input)
        form_layout.addRow(QLabel("Username:"), self.username_action_input)
        form_layout.addRow(QLabel("Password:"), self.password_action_input)

        # Add form layout to main layout
        main_layout.addLayout(hor_layout)
        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.save_button)

        self.setLayout(main_layout)
    
    def check_configuration_file_exists(self, file_path):
        try:
            # Initialize configuration file
            config_file =  "custom_actions.json"
            if not os.path.exists(file_path):
                os.makedirs(file_path, exist_ok=True)
                if not os.path.exists(os.path.join(file_path, config_file)):
                    with open(os.path.join(file_path, config_file), "w") as f:
                        f.write("{}")

        except FileNotFoundError as ex:
            QMessageBox.critical(self, "Configuration file error", f"An error occurred while trying to load the custom action configuration file: {str(ex)}")

    def save_custom_action(self):
        try:
            action_name = self.action_name_input.text()
            host = self.host_action_input.text()
            directory = self.directory_action_input.text()
            username = self.username_action_input.text()
            password = self.password_action_input.text()
            
            if not action_name:
                QMessageBox.warning(self, "Missing action name", "Please fill in the Action Name in order to save the custom action.")
                return
            
            if not host and not directory and not username and not password:
                QMessageBox.warning(self, "Missing action details", "Please fill in at least one of the other fields, other than Action Name to save the custom action.")
                return
            
            # Save the custom action to the configuration file
            self.custom_action_config.set(action_name, {
                "host": host,
                "directory": directory,
                "username": username,
                "password": password
            })
            
            self.update_combobox()
            self.parent().load_custom_actions()
            
            QMessageBox.information(self, "Action saved", f"Custom action '{action_name}' has been saved successfully.")
        except Exception as ex:
            QMessageBox.critical(self, "Error", f"An error occurred while saving the custom action: {str(ex)}")

    def load_custom_action(self):
        try:
            custom_action_combobox_value = self.custom_autofill_actions_combobox.currentText()
            data = self.custom_action_config.get(custom_action_combobox_value)
            
            if data:
                self.action_name_input.setText(custom_action_combobox_value)
                self.host_action_input.setText(data["host"])
                self.directory_action_input.setText(data["directory"])
                self.username_action_input.setText(data["username"])
                self.password_action_input.setText(data["password"])
            
        except Exception as ex:
            QMessageBox.critical(self, "Load custom action error", f"An error occurred, {str(ex)}")
    
    def delete_custom_action(self):
        try:
            custom_action_combobox_value = self.custom_autofill_actions_combobox.currentText()
            custom_action_combobox_index = self.custom_autofill_actions_combobox.currentIndex()
            if custom_action_combobox_value:
                reply = QMessageBox.question(self, "Delete selected action?", f"Are you sure you want to delete the action {custom_action_combobox_value}?",QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.custom_action_config.delete(custom_action_combobox_value)
                    self.custom_autofill_actions_combobox.removeItem(custom_action_combobox_index)
                    self.main_window.load_custom_actions() # Removes action from fill menu
                    self.clear_all_inputs()
                else:
                    return
            else:
                QMessageBox.information(self, "No action to delete", "Please select an action from the combobox first.")
        except Exception as ex:
            QMessageBox.critical(self, "Error while trying to delete action", f"An error has occurred while trying to delete the custom action. {str(ex)}")
    
    def update_combobox(self):
        config_file_values = self.custom_action_config.get_all_keys()
        if len(config_file_values) > 0:
            self.custom_autofill_actions_combobox.setDisabled(False)
            self.custom_autofill_actions_combobox.clear()
            self.custom_autofill_actions_combobox.addItems(config_file_values)
    
    def clear_all_inputs(self):
        inputs = [self.action_name_input, self.host_action_input , self.directory_action_input, self.username_action_input, self.password_action_input]
        for input in inputs:
            input.clear()
    
    def closeEvent(self, event: QCloseEvent):
        # Save geometry on close
        geometry = self.saveGeometry()
        self.settings.setValue("action_geometry", geometry)
        super(CustomAutoFillAction, self).closeEvent(event)
        
class MyTextEdit(QTextEdit):
    def __init__(self):
        super().__init__()

    def contextMenuEvent(self, event):
        # Get the default menu
        menu = self.createStandardContextMenu()

        # Custom action for clearing the log output
        clear_log = QAction("Clear log", self)
        clear_log.triggered.connect(self.clear_log_handler)
        
        # Custom action for sorting the log output
        sort_log = QAction("Sort log", self)
        sort_log.triggered.connect(self.sort_log_handler)

        # Add the action to the menu (you can choose where to insert it)
        menu.addSeparator()
        menu.addAction(clear_log)
        menu.addAction(sort_log)

        # Show the menu at the cursor position
        menu.exec(event.globalPos())

    def clear_log_handler(self):
        self.clear()
    
    def sort_log_handler(self):
        test_log_text = self.toPlainText()
        test_log_lines = test_log_text.splitlines()
        sorted_lines = sorted(test_log_lines, key=lambda x: x.lower())  # Sort case-insensitive
        sorted_text = '\n'.join(sorted_lines)
        self.setPlainText(sorted_text)
        
class NetworkMonitor(QThread):
    status_signal = Signal(str, int)

    def __init__(self, interval=1):
        super().__init__()
        self.interval = interval
        self._running = True
        self.process = psutil.Process()  # This process (your PySide6 app)

    def run(self):
        prev_io = psutil.net_io_counters()
        while self._running:
            time.sleep(self.interval)
            current_io = psutil.net_io_counters()
            
            # Get current process memory usage (RSS = resident set size = RAM in use)
            process_mem_bytes = self.process.memory_info().rss
            process_cpu_usage = self.process.cpu_percent(interval=None)
            process_mem_mb = process_mem_bytes / (1024 * 1024)
            bytes_sent = current_io.bytes_sent - prev_io.bytes_sent
            bytes_recv = current_io.bytes_recv - prev_io.bytes_recv

            sent_per_sec = bytes_sent / self.interval / 1024
            recv_per_sec = bytes_recv / self.interval / 1024

            self.status_signal.emit(f"Upload: {sent_per_sec:.2f} KB/s | Download: {recv_per_sec:.2f} KB/s | App Usage: RAM: {process_mem_mb:.2f}MB | CPU: {process_cpu_usage:.2f}%", 5000)

            prev_io = current_io

    def stop(self):
        self._running = False
        
class SFTPWorker(QThread):
    """Worker thread for SFTP uploads"""
    progress_signal = Signal(int)
    multi_file_progress_signal = Signal(int)  # For multiple files
    task_progress_signal = Signal(int, bool)  # task_id, success
    log_signal = Signal(str)
    finished_signal = Signal(float)
    statusbar_signal = Signal(str, int)
    statusbar_hidden_state = Signal(bool)
    
    def __init__(self, connections:int, test_file: str, multiple_files_state: bool, host: str, port: str, directory: str, username: str, password: str):
        super().__init__()
        self.connections = connections
        self.test_file = test_file
        self.transfer_multiple_files = multiple_files_state
        self.host = host
        self.port = port
        self.directory = directory
        self.username = username
        self.password = password
        self.tasks_completed = 0
        self.tasks_total = connections
        self.network_monitor = NetworkMonitor(interval=0.5)
        self.network_monitor.status_signal.connect(self.statusbar_signal)
        
        self.stop_event = threading.Event()
        
    def run(self):
        self.statusbar_hidden_state.emit(True)
        start_time = time.time()
        self.tasks_completed = 0

        # Start network monitor
        self.network_monitor.start()
        
        try:
            with ThreadPoolExecutor(max_workers=self.connections) as executor:
                futures = {executor.submit(self.sftp_upload_task, i): i for i in range(self.tasks_total)}

                for future in as_completed(futures):
                    if self.stop_event.is_set():
                        executor.shutdown(wait=False)
                        self.log_signal.emit("SFTP stress test canceled during execution.")
                        break
                    
                    task_id = futures[future]
                    try:
                        success = future.result()
                        self.task_progress_signal.emit(task_id, success)
                        self.tasks_completed += 1
                        progress = int((self.tasks_completed / self.tasks_total) * 100)
                        self.progress_signal.emit(progress)
                    except Exception as e:
                        self.log_signal.emit(f"Task {task_id} generated an exception: {str(e)}")
                        self.tasks_completed += 1
                        progress = int((self.tasks_completed / self.tasks_total) * 100)
                        self.progress_signal.emit(progress)
        finally:
            self.network_monitor.stop()
            self.network_monitor.wait()  # Thread stops cleanly

            end_time = time.time()
            total_time = end_time - start_time
            # Dynamic message based on how the task ended
            if self.stop_event.is_set():
                self.log_signal.emit("=" * 50)
                self.log_signal.emit(f"Task was canceled after {self.tasks_completed} uploads in {total_time:.2f} seconds.")
            elif self.tasks_completed == self.tasks_total:
                self.log_signal.emit("=" * 50)
                self.log_signal.emit(f"Completed all {self.tasks_completed} SFTP uploads in {total_time:.2f} seconds.")
            else:
                self.log_signal.emit("=" * 50)
                self.log_signal.emit(f"Task ended early with {self.tasks_completed} of {self.tasks_total} uploads completed in {total_time:.2f} seconds.")
            self.finished_signal.emit(total_time)

    
    def sftp_upload_task(self, task_id):
        """Individual SFTP upload task"""
        if self.stop_event.is_set():
            self.log_signal.emit(f"Task {task_id}: Canceled before starting.")
            return False
        
        transport = None
        sftp = None
        total_files = 0
        update_count_state = False
    
        try:
            self.log_signal.emit(f"Task {task_id}: Starting upload...")
    
            # Establish the connection once
            transport = paramiko.Transport((self.host, self.port))
            transport.connect(username=self.username, password=self.password)
            sftp = paramiko.SFTPClient.from_transport(transport)
    
            if self.transfer_multiple_files:
                if self.connections > 1:
                    update_count_state = False
                else:
                    update_count_state = True
                # Assuming self.test_file is a directory in this case
                files = os.listdir(self.test_file)
                self.log_signal.emit(f"Task {task_id}: Uploading {len(files)} files...")
    
                for file in files:
                    if self.stop_event.is_set():
                        self.log_signal.emit(f"Task {task_id}: Canceled during file uploads.")
                        return False
                    local_path = os.path.join(self.test_file, file)
                    remote_path = self._get_remote_path(file, task_id)
    
                    sftp.put(local_path, remote_path)
                    self.log_signal.emit(f"Task {task_id}: Upload successful to dir: '{remote_path}'.")
                    if update_count_state:
                        total_files += 1
                        progress = int((total_files / len(files)) * 100)
                        self.multi_file_progress_signal.emit(progress)
            else:
                if self.stop_event.is_set():
                    self.log_signal.emit(f"Task {task_id}: Canceled during file uploads.")
                    return False
                
                file_name = os.path.basename(self.test_file)
                remote_path = self._get_remote_path(file_name, task_id)
    
                sftp.put(self.test_file, remote_path)
                self.log_signal.emit(f"Task {task_id}: Upload successful to {remote_path}.")
    
            return True
    
        except Exception as e:
            self.log_signal.emit(f"Task {task_id}: Upload failed - {str(e)}")
            return False
    
        finally:
            # Ensure clean-up happens no matter what
            if sftp:
                sftp.close()
            if transport:
                transport.close()
    
    
    def _get_remote_path(self, file_name, task_id):
        """
        Helper method to construct the remote file path.
        Adds task_id to filename if task_id > 0.
        """
        base, ext = os.path.splitext(file_name)
        if task_id > 0:
            file_name = f"{base}_taskid_{task_id}{ext}"
    
        return f"{self.directory}/{file_name}"


class DummyFileWorker(QThread):
    """Worker thread for dummy file generation"""
    progress_signal = Signal(int)
    log_signal = Signal(str)
    finished_signal = Signal()
    
    def __init__(self, amount_of_files, file_name, save_path, file_size_suffix_index, size_in_mb):
        super().__init__()
        self.amount_of_files = amount_of_files
        self.file_name = file_name
        self.save_path = save_path
        self.file_size_suffix_index = file_size_suffix_index
        self.size_in_mb = size_in_mb
        
    def run(self):
        """Create dummy files with the specified parameters"""
        try:
            os.makedirs(self.save_path, exist_ok=True)
            initial_chuck_size = 1024 if self.file_size_suffix_index == 0 else 1 if self.file_size_suffix_index == 1 else 1024
            for i in range(1, self.amount_of_files + 1):
                save_to = os.path.join(self.save_path, f"{self.file_name}_{i}.txt")
                
                if isinstance(self.size_in_mb, int):
                    file_size = self.size_in_mb
                elif self.size_in_mb.lower() == "random":
                    file_size = random.randint(1, 25)
                    self.log_signal.emit(f"File {i}: Using random size of {file_size} MB")
                else:
                    file_size = int(self.size_in_mb)
                
                self.log_signal.emit(f"Creating file {i}/{self.amount_of_files}")
                
                with open(save_to, 'wb') as f:
                    # Write in chunks to avoid memory issues with large files
                    chunk_size = initial_chuck_size * 1024  # 1 MB or 1KB ---> Depends on the index of the combobox in previous class
                    for j in range(file_size):
                        f.write(b'\0' * chunk_size)
                        # Update progress more granularly for large files
                        if file_size > 10:
                            sub_progress = int((i-1) / self.amount_of_files * 100) + int(j / file_size * (100 / self.amount_of_files))
                            self.progress_signal.emit(sub_progress)
                
                # Update progress
                overall_progress = int(i / self.amount_of_files * 100)
                self.progress_signal.emit(overall_progress)
                
            self.log_signal.emit(f"Successfully created {self.amount_of_files} dummy files in {self.save_path}")
            self.finished_signal.emit()
            
        except Exception as e:
            self.log_signal.emit(f"Error creating dummy files: {str(e)}")
            self.finished_signal.emit()

def get_files(files_path):
    """Get all files as list from the specified directory"""
    try:
        files = [f for f in os.listdir(files_path) if os.path.isfile(os.path.join(files_path, f))]
        if len(files) == 0:
            return []
        else:
            return files
    except FileNotFoundError:
        return []

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        icon_file_path = os.path.join(CURRENT_WORKING_DIR,"_internal","icon")
        app_icon = QIcon(os.path.join(icon_file_path,"sftp_icon.ico"))
        # Config file for custom autofill actions
        self.custom_actions_config = os.path.join(CURRENT_WORKING_DIR, "_internal", "configuration", "custom_actions.json")
        # Initialize settings for window geometry
        self.settings = QSettings("SFTP_Main", "Jovan") # Settings to save current location of the windows on exit
        geometry = self.settings.value("main_window_geometry", bytes())

        self.setWindowTitle("SFTP Stress Test Tool")
        self.setWindowIcon(app_icon)
        self.setMinimumSize(800, 600)
        self.restoreGeometry(geometry)
        
        # Main layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Create tab widget
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # Create tabs
        self.stress_test_tab = QWidget()
        self.file_generator_tab = QWidget()
        
        tabs.addTab(self.stress_test_tab, "SFTP Stress Test")
        tabs.addTab(self.file_generator_tab, "Dummy File Generator")
        
        # Setup each tab
        self.setup_stress_test_tab()
        self.setup_file_generator_tab()
        
        self.setup_menu_bar()
    
    def setup_menu_bar(self):
        menu_bar = self.menuBar()
        
        # Open Menu
        open_menu = menu_bar.addMenu("&Open")
        open_test_file_folder_action = QAction("Open test file folder", self)
        open_test_file_folder_action.triggered.connect(lambda: self.open_folder_helper(self.test_file_input.text(), "Test File"))
        open_generated_file_folder_action = QAction("Open generated files folder", self)
        open_generated_file_folder_action.triggered.connect(lambda: self.open_folder_helper(self.save_path_input.text(), "Generated File"))
        open_menu.addAction(open_test_file_folder_action)
        open_menu.addAction(open_generated_file_folder_action)
        
        # Settings Menu
        settings_menu = menu_bar.addMenu("&Settings")
        settings_action = QAction("Custom Autofill Manager", self)
        settings_action.triggered.connect(self.open_custom_action_dialog)
        settings_menu.addAction(settings_action)
        
        # Autofill menu
        self.autofill_menu = menu_bar.addMenu("&Autofill")
        autofill_action = QAction("Geis NCT01", self)
        autofill_action.triggered.connect(self.autofill_geis_nct01)
        self.autofill_menu.addAction(autofill_action)
        
        self.load_custom_actions()

    def open_folder_helper(self, path, element):
        try:
            if os.path.isdir(path):
                os.startfile(path)
            elif os.path.isfile(path):
                head, tail = os.path.split(path)
                os.startfile(head)
            elif path == "" and element == "Test File":
                QMessageBox.warning(self, "Path not found", "Cannot open path, test file input is empty in test parameters.")
            elif path == "" and element == "Generated File":
                QMessageBox.warning(self, "Path not found", "Cannot open path, save path input is empty in file generation parameters.")
        except OSError as os_error:
            QMessageBox.critical(self, "OSError occurred", f"An exception has occurred: {str(os_error)}.")
        
    def load_custom_actions(self):
        try:
            with open(self.custom_actions_config, "r") as jf:
                data = json.load(jf)
            if data or data == {}:
                # Clear existing custom actions
                for action in self.autofill_menu.actions():
                    if action.text() not in "Geis NCT01":
                        self.autofill_menu.removeAction(action)
                # Add new custom actions
                for key, value in data.items():
                    action = QAction(key, self)
                    action.triggered.connect(lambda checked, k=key, v=value: self.execute_custom_action(k, v))
                    self.autofill_menu.insertAction(self.autofill_menu.actions()[0], action)

        except json.JSONDecodeError:
            QMessageBox.critical(self, "Error occurred", "The JSON file contains invalid JSON.")
        except FileNotFoundError:
            QMessageBox.critical(self, "Error occurred", "The JSON file was not found.")
        except Exception as ex:
            QMessageBox.critical(self, "Error occurred", f"An error occurred while loading custom actions: {str(ex)}")
    
    def execute_custom_action(self, action_name, config_data):
        try:
            if config_data:
                self.host_input.setText(config_data["host"])
                self.directory_input.setText(config_data["directory"])
                self.username_input.setText(config_data["username"])
                self.password_input.setText(config_data["password"])
            else:
                QMessageBox.warning(self, "Action not found", f"No data found for action '{action_name}'.")
        except Exception as ex:
            QMessageBox.critical(self, "Error", f"An error occurred while executing the custom action: {str(ex)}")
    
    def open_custom_action_dialog(self):
        self.w = CustomAutoFillAction(self)
        self.w.exec()
    
    def setup_stress_test_tab(self):
        layout = QVBoxLayout()
        self.stress_test_tab.setLayout(layout)
        
        # SFTP Configuration Group
        config_group = QGroupBox("SFTP Configuration")
        config_layout = QFormLayout()
        config_group.setLayout(config_layout)
        
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("Enter SFTP host address")
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(SFTP_PORT)
        self.directory_input = QLineEdit()
        self.directory_input.setPlaceholderText("Enter SFTP directory")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter SFTP username")
        
        password_layout = QHBoxLayout()
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter SFTP password")
        self.show_password_check = QPushButton("Show Password")
        self.show_password_check.setCheckable(True)
        self.show_password_check.toggled.connect(lambda state: self.password_input.setEchoMode(QLineEdit.Normal) if state else self.password_input.setEchoMode(QLineEdit.Password))
        
        password_layout.addWidget(self.password_input)
        password_layout.addWidget(self.show_password_check)
        
        config_layout.addRow("Host:", self.host_input)
        config_layout.addRow("Port:", self.port_input)
        config_layout.addRow("Directory:", self.directory_input)
        config_layout.addRow("Username:", self.username_input)
        config_layout.addRow("Password:", password_layout)
        
        # Test File Selection
        file_layout = QHBoxLayout()
        self.multi_file_checkbox = QCheckBox("Enable transfer of multiple files at once")
        self.multi_file_progressbar = QProgressBar()
        self.multi_file_progressbar.setHidden(True)
        self.multi_file_checkbox.setChecked(False)
        self.multi_file_checkbox.stateChanged.connect(self.multi_select_state_changed)
        
        # Horizontal layout for multifile and progress bar
        multi_file_layout = QHBoxLayout()
        multi_file_layout.addWidget(self.multi_file_checkbox, 1)
        multi_file_layout.addWidget(self.multi_file_progressbar, 2)
        
        self.test_file_input = QLineEdit()
        self.test_file_input.setPlaceholderText("Please select a test file...")
        self.test_file_input.textChanged.connect(lambda: self.log_output.setText(f"The total number of files in selected folder is {len(os.listdir(self.test_file_input.text()))}") if os.path.isdir(self.test_file_input.text()) else None)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_test_file)
        file_layout.addWidget(self.test_file_input, 1)
        file_layout.addWidget(browse_button)
        
        # Test Parameters
        test_group = QGroupBox("Test Parameters")
        test_layout = QFormLayout()
        test_group.setLayout(test_layout)
        
        self.connections_input = QSpinBox()
        self.connections_input.setRange(1, 100)
        self.connections_input.setValue(5)
        
        test_layout.addRow("Test File:", file_layout)
        test_layout.addRow("Concurrent Connections:", self.connections_input)
        test_layout.addRow("Multiple Files", multi_file_layout) # Added Horizotnal layout for multiple files and progress bar instead of only checkbox
        
        # Progress
        progress_group = QGroupBox("Test Progress")
        progress_layout = QVBoxLayout()
        progress_group.setLayout(progress_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        
        progress_layout.addWidget(self.progress_bar)
        
        # Action Buttons
        button_layout = QHBoxLayout()
        self.run_test_button = QPushButton("Run SFTP Stress Test")
        self.run_test_button.clicked.connect(self.run_stress_test)
        self.cancel_test_button = QPushButton("Cancel Test")
        self.cancel_test_button.clicked.connect(self.cancel_stress_test)
        self.cancel_test_button.setEnabled(False)
        button_layout.addWidget(self.run_test_button)
        button_layout.addWidget(self.cancel_test_button)
        
        # Log Output
        log_group = QGroupBox("Test Log")
        log_layout = QVBoxLayout()
        log_group.setLayout(log_layout)
        
        self.log_output = MyTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.customContextMenuRequested.connect(self.contextMenuEvent)
        self.system_statusbar = QStatusBar()
        self.system_statusbar.setSizeGripEnabled(False)
        self.system_statusbar.setHidden(True)
        
        log_layout.addWidget(self.log_output)
        log_layout.addWidget(self.system_statusbar)
        
        # Add all to main layout
        layout.addWidget(config_group)
        layout.addWidget(test_group)
        layout.addWidget(progress_group)
        layout.addLayout(button_layout)
        layout.addWidget(log_group)
    
    def setup_file_generator_tab(self):
        layout = QVBoxLayout()
        self.file_generator_tab.setLayout(layout)
        
        # File Generation Parameters
        gen_group = QGroupBox("File Generation Parameters")
        gen_layout = QFormLayout()
        gen_group.setLayout(gen_layout)
        
        self.file_count_input = QSpinBox()
        self.file_count_input.setRange(1, 100)
        self.file_count_input.setValue(1)
        
        self.file_name_input = QLineEdit("dummy")
        self.file_name_input.setPlaceholderText("Enter a file name prefix")
        
        self.size_type_combo = QComboBox()
        self.size_type_combo.addItems(["Fixed Size (MB)", "Fixed Size (KB)", "Random Size"])
        self.size_type_combo.currentIndexChanged.connect(self.toggle_size_input)
        
        self.file_size_input = QSpinBox()
        self.file_size_input.setRange(1, 1000)
        self.file_size_input.setValue(1)
        self.file_size_input.setSuffix(" MB")
        
        # Path Selection
        path_layout = QHBoxLayout()
        self.save_path_input = QLineEdit()
        self.save_path_input.setPlaceholderText("Select a save path...")
        browse_save_button = QPushButton("Browse")
        browse_save_button.clicked.connect(self.browse_save_path)
        path_layout.addWidget(self.save_path_input, 1)
        path_layout.addWidget(browse_save_button)
        
        gen_layout.addRow("Number of Files:", self.file_count_input)
        gen_layout.addRow("File Name Prefix:", self.file_name_input)
        gen_layout.addRow("Size Type:", self.size_type_combo)
        gen_layout.addRow("File Size:", self.file_size_input)
        gen_layout.addRow("Save Path:", path_layout)
        
        # Progress
        gen_progress_group = QGroupBox("Generation Progress")
        gen_progress_layout = QVBoxLayout()
        gen_progress_group.setLayout(gen_progress_layout)
        
        self.gen_progress_bar = QProgressBar()
        self.gen_progress_bar.setValue(0)
        
        gen_progress_layout.addWidget(self.gen_progress_bar)
        
        # Action Buttons
        gen_button_layout = QHBoxLayout()
        self.generate_button = QPushButton("Generate Dummy Files")
        self.generate_button.clicked.connect(self.generate_dummy_files)
        self.cancel_generate_button = QPushButton("Cancel Generation")
        self.cancel_generate_button.clicked.connect(self.cancel_generation)
        self.cancel_generate_button.setEnabled(False)
        gen_button_layout.addWidget(self.generate_button)
        gen_button_layout.addWidget(self.cancel_generate_button)
        
        # File List
        files_group = QGroupBox("Generated Files")
        files_layout = QVBoxLayout()
        files_group.setLayout(files_layout)
        
        refresh_button = QPushButton("Refresh File List")
        refresh_button.clicked.connect(self.refresh_file_list)
        
        self.files_list = QTextEdit()
        self.files_list.setReadOnly(True)
        
        files_layout.addWidget(refresh_button)
        files_layout.addWidget(self.files_list)
        
        # Log Output
        gen_log_group = QGroupBox("Generation Log")
        gen_log_layout = QVBoxLayout()
        gen_log_group.setLayout(gen_log_layout)
        
        self.gen_log_output = MyTextEdit()
        self.gen_log_output.setReadOnly(True)
        gen_log_layout.addWidget(self.gen_log_output)
        
        # Add all to main layout
        layout.addWidget(gen_group)
        layout.addWidget(gen_progress_group)
        layout.addLayout(gen_button_layout)
        layout.addWidget(files_group)
        layout.addWidget(gen_log_group)
        
        # Initialize file list
        self.refresh_file_list()
    
    def update_file_size_suffix(self):
        if self.size_type_combo.currentIndex() == 0:
            self.file_size_input.setSuffix(" MB")
            self.file_count_input.setRange(1, 100)
        elif self.size_type_combo.currentIndex() == 1:
            self.file_size_input.setSuffix(" KB")
            self.file_count_input.setRange(1, 10000)
        else:
            self.file_size_input.setSuffix(" Random file size between 1-25 MB")
            self.file_count_input.setRange(1, 100)
    
    def browse_test_file(self):
        if not self.multi_file_checkbox.isChecked():
            file_name, _ = QFileDialog.getOpenFileName(self, "Select Test File")
            if file_name:
                self.test_file_input.setText(file_name)
        else:
            folder = QFileDialog.getExistingDirectory(self, "Select Test Files Folder")
            if folder:
                self.test_file_input.setText(folder)
    
    def multi_select_state_changed(self):
        if self.multi_file_checkbox.isChecked():
            self.test_file_input.clear()
            self.test_file_input.setPlaceholderText("Please select a folder with test files...")
        else:
            self.test_file_input.setPlaceholderText("Please select a test file...")
            self.test_file_input.clear()
    
    def browse_save_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if folder:
            self.save_path_input.setText(folder)
    
    def toggle_size_input(self, index):
        if index == 0 or index == 1:  # Fixed Size (MB) or Fixed Size (KB)
            self.file_size_input.setEnabled(True)
            
        else:  # Random Size
            self.file_size_input.setEnabled(False)
        # Update Spinbox for file size
        self.update_file_size_suffix()
            
    # Menubar action methods
    def autofill_geis_nct01(self):
        self.host_input.setText(SFTP_HOST)
        self.port_input.setValue(SFTP_PORT)
        self.directory_input.setText(SFTP_DIRECTORY)
        self.username_input.setText(SFTP_USER)
        self.password_input.setText(SFTP_PASS)
    
    def run_stress_test(self):
        # Get user input
        host = self.host_input.text()
        port = self.port_input.value()
        directory = self.directory_input.text()
        username = self.username_input.text()
        password = self.password_input.text()
        test_file = self.test_file_input.text()
        connections = self.connections_input.value()
        multiple_files_state = self.multi_file_checkbox.isChecked()
        
        # Validate inputs
        if not os.path.exists(test_file):
            self.log_output.append(f"ERROR: Test file '{test_file}' does not exist.")
            return
        
        # Clear previous log and reset progress
        self.log_output.clear()
        self.progress_bar.setValue(0)
        
        # Log start information
        self.log_output.append(f"Starting SFTP stress test with {connections} concurrent connections...")
        self.log_output.append(f"Host: {host}:{port}")
        self.log_output.append(f"Directory: {directory}")
        self.log_output.append("=" * 50)
        
        # Disable/enable buttons
        self.run_test_button.setEnabled(False)
        self.cancel_test_button.setEnabled(True)
        
        # Create and start worker thread
        self.sftp_worker = SFTPWorker(connections, test_file, multiple_files_state, host, port, directory, username, password)
        self.sftp_worker.progress_signal.connect(self.update_sftp_progress)
        self.sftp_worker.multi_file_progress_signal.connect(self.update_multi_files_progress)
        self.sftp_worker.task_progress_signal.connect(self.update_task_progress)
        self.sftp_worker.log_signal.connect(self.update_log)
        self.sftp_worker.statusbar_signal.connect(self.update_statusbar)
        self.sftp_worker.statusbar_hidden_state.connect(self.update_statusbar_state)
        self.sftp_worker.finished_signal.connect(self.test_finished)
        self.sftp_worker.start()
    
    def cancel_stress_test(self):
        if hasattr(self, 'sftp_worker') and self.sftp_worker.isRunning():
            self.sftp_worker.stop_event.set()  
            self.log_output.append("SFTP stress test canceled by user.")
            self.log_output.append("SFTP Upload may continue trying to upload file(s) when a connection attempt fails, but will stop shortly after.")
            self.run_test_button.setEnabled(True)
            self.cancel_test_button.setEnabled(False)
            self.multi_file_progressbar.setValue(0)
            self.multi_file_progressbar.setHidden(True)
    
    @Slot(int)
    def update_sftp_progress(self, value):
        self.progress_bar.setValue(value)
        
    @Slot(int)
    def update_multi_files_progress(self, value):
        self.multi_file_progressbar.setHidden(False)
        self.multi_file_progressbar.setValue(value)
    
    @Slot(int, bool)
    def update_task_progress(self, task_id, success):
        status = "succeeded." if success else "failed."
        self.log_output.append(f"=== Task with ID {task_id} has {status} ===")
    
    @Slot(str)
    def update_log(self, message):
        self.log_output.append(message)
        # Scroll to bottom
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())
    
    @Slot(str, int)
    def update_statusbar(self, message, timeout):
        self.system_statusbar.showMessage(message, timeout)
        
    @Slot(bool)
    def update_statusbar_state(self):
        self.system_statusbar.setHidden(False)
    
    @Slot(float)
    def test_finished(self, total_time):
        self.run_test_button.setEnabled(True)
        self.cancel_test_button.setEnabled(False)
        self.multi_file_progressbar.setValue(0)
        self.multi_file_progressbar.setHidden(True)
        #self.log_output.append(f"Test completed in {total_time:.2f} seconds.")
        self.log_output.append("=" * 50)
    
    def generate_dummy_files(self):
        amount = self.file_count_input.value()
        file_name = self.file_name_input.text()
        save_path = self.save_path_input.text()
        file_size_suffix_index = self.size_type_combo.currentIndex() # 0 = MB, 1 = KB
        fs_suffix = "MB" if file_size_suffix_index == 0 else "KB" if file_size_suffix_index == 1 else ""
        
        if file_size_suffix_index == 0 or file_size_suffix_index == 1:  # Fixed size (MB) or Fixed size (KB)
            size_in_mb = self.file_size_input.value()
        else:  # Random size
            size_in_mb = "random"
        
        # Clear previous log and reset progress
        self.gen_log_output.clear()
        self.gen_progress_bar.setValue(0)
        
        # Log start information
        self.gen_log_output.append(f"Starting generation of {amount} dummy files...")
        self.gen_log_output.append(f"Path: {save_path}")
        self.gen_log_output.append(f"Size: {'Random 1-25 MB' if size_in_mb == 'random' else f'{size_in_mb} {fs_suffix}'}")
        self.gen_log_output.append("=" * 50)
        
        # Disable/enable buttons
        self.generate_button.setEnabled(False)
        self.cancel_generate_button.setEnabled(True)
        
        # Create and start worker thread
        self.file_worker = DummyFileWorker(amount, file_name, save_path, file_size_suffix_index, size_in_mb)
        self.file_worker.progress_signal.connect(self.update_gen_progress)
        self.file_worker.log_signal.connect(self.update_gen_log)
        self.file_worker.finished_signal.connect(self.generation_finished)
        self.file_worker.start()
    
    def cancel_generation(self):
        if hasattr(self, 'file_worker') and self.file_worker.isRunning():
            self.file_worker.terminate()
            self.file_worker.wait()
            self.gen_log_output.append("File generation canceled by user.")
            self.generate_button.setEnabled(True)
            self.cancel_generate_button.setEnabled(False)
    
    @Slot(int)
    def update_gen_progress(self, value):
        self.gen_progress_bar.setValue(value)
    
    @Slot(str)
    def update_gen_log(self, message):
        self.gen_log_output.append(message)
        # Scroll to bottom
        self.gen_log_output.verticalScrollBar().setValue(self.gen_log_output.verticalScrollBar().maximum())
    
    @Slot()
    def generation_finished(self):
        self.generate_button.setEnabled(True)
        self.cancel_generate_button.setEnabled(False)
        self.gen_log_output.append("File generation completed.")
        self.gen_log_output.append("=" * 50)
        self.refresh_file_list()
    
    def refresh_file_list(self):
        path = self.save_path_input.text()
        files = get_files(path)
        
        self.files_list.clear()
        
        if not files:
            self.files_list.append(f"No files found in '{path}'")
            return
        
        self.files_list.append(f"Files in '{path}':")
        
        # Get file sizes
        for file in files:
            file_path = os.path.join(path, file)
            size_bytes = os.path.getsize(file_path)
            size_mb = size_bytes / (1024 * 1024)
            self.files_list.append(f"- {file} ({size_mb:.2f} MB)")
            
    def closeEvent(self, event: QCloseEvent):
        # Save geometry on close
        geometry = self.saveGeometry()
        self.settings.setValue("main_window_geometry", geometry)
        super(MainWindow, self).closeEvent(event)

def main():
    qdarktheme.enable_hi_dpi() 
    app = QApplication(sys.argv)
    
    my_custom_colors = {
        "[dark]": {
            "primary": "#3F69FD",
            "input.background": "#3f4042",
            "background>textarea": "#3f4042",
            "primary>button.hoverBackground": "#3f4042",
            "menubar.selectionBackground": "#3F69FD",
            "popupItem.selectionBackground": "#3F69FD",
            "scrollbarSlider.background": "#3F69FD"
        },
        
        "[light]": {
            "primary": "#3F69FD",
            "background": "#fcfcfc",
            "foreground": "#000000",
            "input.background": "#ebebeb",
            "background>textarea": "#ebebeb",
            "primary>button.hoverBackground": "#ebebeb",
            "border": "#949494",
            "menubar.selectionBackground": "#3F69FD",
            "popupItem.selectionBackground": "#3F69FD",
            "scrollbarSlider.background": "#3F69FD"
        }
    }
    
    qdarktheme.setup_theme(theme="auto", custom_colors=my_custom_colors)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
