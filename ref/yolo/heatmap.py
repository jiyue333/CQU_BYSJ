import cv2
from ultralytics import solutions

cap = cv2.VideoCapture("/Users/taless/Downloads/videoplayback.mp4")
assert cap.isOpened(), "Error reading video file"

w, h, fps = (int(cap.get(x)) for x in (
    cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS
))
video_writer = cv2.VideoWriter(
    "heatmap_output.avi",
    cv2.VideoWriter_fourcc(*"mp4v"),
    fps,
    (w, h),
)

# 计数区域（矩形）
region_points = [(100, 100), (300, 100), (300, 300), (100, 300)]

heatmap = solutions.Heatmap(
    show=True,
    model="yolo11n.pt",
    colormap=cv2.COLORMAP_PARULA,
    region=region_points,
    show_conf=True,     # 这个开关我们会用于生成 label
    show_labels=True,
    iou=0.9,
    classes=[0],        # 只检测 person
    device="cpu",
)

def draw_boxes_with_conf(im, boxes, clss, confs, names=None):
    """把 xyxy 框 + 置信度画到图上。"""
    if boxes is None or len(boxes) == 0:
        return im

    for i, b in enumerate(boxes):
        x1, y1, x2, y2 = map(int, b)
        cls_id = int(clss[i]) if clss is not None and len(clss) > i else -1
        conf = float(confs[i]) if confs is not None and len(confs) > i else None

        # label
        cls_name = str(cls_id)
        if names is not None and cls_id in names:
            cls_name = names[cls_id]

        if conf is not None:
            label = f"{cls_name} {conf:.2f}"
        else:
            label = f"{cls_name}"

        # box
        cv2.rectangle(im, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # label bg
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(im, (x1, y1 - th - 6), (x1 + tw + 4, y1), (0, 255, 0), -1)
        cv2.putText(im, label, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    return im

while cap.isOpened():
    success, im0 = cap.read()
    if not success:
        print("Video frame is empty or processing is complete.")
        break

    # 1) 先跑 heatmap solution（它会做检测/跟踪 + 生成热图叠加画面）
    results = heatmap(im0)

    # 2) results.plot_im 是“热图叠加后的帧”
    out = results.plot_im.copy()

    # 3) 从 heatmap 对象里取出本帧的 boxes/clss/confs（solutions 会把这些存到对象里）
    boxes = getattr(heatmap, "boxes", None)   # Nx4, xyxy
    clss  = getattr(heatmap, "clss", None)    # N
    confs = getattr(heatmap, "confs", None)   # N

    # 类别名映射（可选）
    names = None
    try:
        # 有些版本是 heatmap.model.names，有些可能是 heatmap.names
        names = getattr(getattr(heatmap, "model", None), "names", None) or getattr(heatmap, "names", None)
    except Exception:
        names = None

    # 4) 画框 + conf
    out = draw_boxes_with_conf(out, boxes, clss, confs, names)

    video_writer.write(out)

cap.release()
video_writer.release()
cv2.destroyAllWindows()
