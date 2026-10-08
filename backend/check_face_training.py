import os
import joblib
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

encoder_path = os.path.join(MODELS_DIR, "label_encoder.pkl")
training_path = os.path.join(MODELS_DIR, "face_training_data.pkl")

print("=" * 70)
print("STUDENT360 FACE MODEL CHECK")
print("=" * 70)

if not os.path.exists(encoder_path):
    print("MISSING:", encoder_path)
else:
    encoder = joblib.load(encoder_path)
    print("\nLABEL ENCODER STUDENTS:")
    for label in encoder.classes_:
        print(" -", str(label))

if not os.path.exists(training_path):
    print("\nMISSING:", training_path)
else:
    data = joblib.load(training_path)
    X = np.asarray(data.get("X"))
    y = np.asarray(data.get("y"), dtype=object)

    print("\nTRAINING EMBEDDINGS:")
    print("Shape:", X.shape)

    if len(y):
        unique, counts = np.unique(y, return_counts=True)
        print("\nSAMPLES PER STUDENT:")
        for label, count in zip(unique, counts):
            print(f" - {label}: {int(count)} samples")

print("=" * 70)
