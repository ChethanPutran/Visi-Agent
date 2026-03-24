# tests/conftest.py
import pytest
import cv2
import numpy as np
import tempfile
import os

@pytest.fixture(scope="session")
def sample_video():
    """Creates a temporary 1-second blank video for testing."""
    # Create a temporary file path
    temp_dir = tempfile.gettempdir()
    video_path = os.path.join(temp_dir, "test_sample.mp4")
    
    # Define video properties: 640x480, 24fps, 1 second
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_path, fourcc, 24.0, (640, 480))
    
    for _ in range(24):
        # Create a random noise frame or solid color
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        out.write(frame)
    
    out.release()
    
    yield video_path  # This provides the path to the test
    
    # Cleanup: Delete the file after all tests are done
    if os.path.exists(video_path):
        os.remove(video_path)