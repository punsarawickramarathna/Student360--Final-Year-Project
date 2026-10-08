from ultralytics import YOLO

for filename in [
    "models/classroom_model.pt",
    "models/exam_model.pt",
    "models/yolov8n.pt",
]:
    print("\n" + "=" * 70)
    print("MODEL:", filename)
    try:
        model = YOLO(filename)
        print("CLASSES:", model.names)
    except Exception as exc:
        print("ERROR:", repr(exc))
