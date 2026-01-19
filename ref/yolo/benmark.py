from ultralytics.utils.benchmarks import benchmark

# Benchmark
dataframe = benchmark(model="yolo11n.pt", data="coco8.yaml", imgsz=640, half=False, device="cpu", format="onnx")

# save to csv
dataframe.write_csv("benchmarks.csv")

# visualize
# dataframe.plot()  # Polars DataFrame does not support .plot() directly and requires pandas/matplotlib handling
print("Benchmarks saved to benchmarks.csv")