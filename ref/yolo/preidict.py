from ultralytics import YOLO

# Load the custom trained model
model = YOLO("runs/detect/train2/weights/best.pt")


# Perform object detection on the local image
# save=True ensures the annotated image is saved to runs/detect/predict (or similar)
# project="runs/detect" and name="predict" sets the output directory specifically
results = model.predict("bus.jpg", save=True, name="predict", exist_ok=True)

# Process results if needed
for result in results:
    print(f"Results saved to: {result.save_dir}")