import os
import sys

# Force TensorFlow to use the legacy Keras 2 engine.
# Teachable Machine exports Keras 2 models, which Keras 3 cannot load.
# This must be set before TensorFlow is imported.
os.environ["TF_USE_LEGACY_KERAS"] = "1"

# On macOS, pyarrow (pulled in through pandas) can crash TensorFlow on import
# with "mutex lock failed: Invalid argument". This code does not need pyarrow,
# so block it before TensorFlow loads.
sys.modules["pyarrow"] = None

import cv2
import numpy as np
from tf_keras.models import load_model

# Find the model and labels next to this script, whatever folder you run it from
HERE = os.path.dirname(os.path.abspath(__file__))

# Load the model directly using legacy Keras
model = load_model(os.path.join(HERE, "keras_model.h5"), compile=False)

# Load the labels. Each line looks like "0 Background", so keep only the name.
with open(os.path.join(HERE, "labels.txt"), "r") as f:
    class_names = [line.strip().split(" ", 1)[1] for line in f if line.strip()]

# CAMERA can be 0 or 1 based on default camera of your computer
camera = cv2.VideoCapture(0)
if not camera.isOpened():
    sys.exit("Could not open the camera. Try VideoCapture(1), or allow camera access "
             "for your terminal or VS Code in System Settings > Privacy & Security > Camera.")

print("Click the webcam window, then press Esc or q to quit (or Ctrl+C in the terminal).")

while True:
    # Grab the webcamera's image.
    ret, frame = camera.read()
    if not ret:
        print("Could not read a frame from the camera.")
        break

    # Crop the center square, like Teachable Machine does, so the image is not squashed
    h, w = frame.shape[:2]
    size = min(h, w)
    top, left = (h - size) // 2, (w - size) // 2
    frame = frame[top:top + size, left:left + size]

    # Resize the square image to (224-height,224-width) pixels
    frame = cv2.resize(frame, (224, 224), interpolation=cv2.INTER_AREA)

    # Show the image in a window
    cv2.imshow("Webcam Image", frame)

    # OpenCV uses BGR color order, but the model was trained on RGB images
    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Make the image a numpy array and reshape it to the model's input shape.
    image = np.asarray(image, dtype=np.float32).reshape(1, 224, 224, 3)

    # Normalize the image array to the range -1 to 1
    image = (image / 127.5) - 1

    # Predict. verbose=0 stops Keras from printing a progress bar every frame.
    prediction = model.predict(image, verbose=0)
    index = np.argmax(prediction[0])
    class_name = class_names[index]
    confidence_score = prediction[0][index]

    # Print prediction and confidence score
    print(f"Class: {class_name}   Confidence Score: {confidence_score * 100:.0f} %")

    # Listen to the keyboard for presses. Esc key (27) or q to exit.
    # The webcam window must be selected (clicked) to receive key presses.
    # "& 0xFF" keeps only the key code, since macOS can add extra bits.
    key = cv2.waitKey(1) & 0xFF
    if key == 27 or key == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()
