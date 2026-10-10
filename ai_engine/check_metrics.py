from ultralytics import YOLO

# 1. Local PC eke thiyena model eka load karanna
model = YOLO('models/classroom_model.pt')

# 2. Dataset eka deela validation run karanna
print("📊 Calculating Metrics on Local PC...")
metrics = model.val(data='path/to/your/dataset/data.yaml')

# 3. Print the scores
print(f"Precision: {metrics.box.mp:.4f}")
print(f"Recall: {metrics.box.mr:.4f}")
print(f"mAP50: {metrics.box.map50:.4f}")

f1_score = 2 * (metrics.box.mp * metrics.box.mr) / (metrics.box.mp + metrics.box.mr)
print(f"F1 Score: {f1_score:.4f}")