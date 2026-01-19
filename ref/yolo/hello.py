from ultralytics import YOLO

# Load a model
model = YOLO("yolo11n.pt")  # load an official detection model

# Track with the model
results = model.track(source="https://youtu.be/LNwODJXcvt4", show=True)
results = model.track(source="https://youtu.be/LNwODJXcvt4", show=True, tracker="bytetrack.yaml")