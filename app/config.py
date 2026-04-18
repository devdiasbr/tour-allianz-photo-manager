import os

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(BASE_DIR, "footer_template", "template_allianz.jpg")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Template dimensions (pixels)
TEMPLATE_W = 800
TEMPLATE_H = 600
FOOTER_Y_START = 501
FOOTER_HEIGHT = 99  # 600 - 501
PHOTO_AREA_W = 800
PHOTO_AREA_H = 501  # area above footer

# Print dimensions (300 DPI)
PRINT_DPI = 300
LANDSCAPE_W = 2362  # 20cm at 300 DPI
LANDSCAPE_H = 1772  # 15cm at 300 DPI
PORTRAIT_W = 1772   # 15cm at 300 DPI
PORTRAIT_H = 2362   # 20cm at 300 DPI

# Face recognition
FACE_TOLERANCE = 0.70  # More generous matching (default 0.6)
FACE_DETECTION_MODEL = "hog"  # "hog" for CPU, "cnn" for GPU
FACE_SCAN_MAX_WIDTH = 1200  # Downscale limit for session photos
FACE_UPSAMPLE = 2  # Upsample times for small face detection

# Camera
CAMERA_PREVIEW_W = 640
CAMERA_PREVIEW_H = 480
CAMERA_FPS = 15

# UI
THUMBNAIL_SIZE = (240, 160)
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800

# Ensure output dir exists
os.makedirs(OUTPUT_DIR, exist_ok=True)
