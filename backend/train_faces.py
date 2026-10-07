# ============================================================

# Student360 - Face Training System

# ============================================================

#

# PURPOSE

# -------

# 1. Register a NEW student's face from their uploaded video.

# 2. Process ONLY that new student's video.

# 3. Extract FaceNet embeddings from the new student's face.

# 4. Add those embeddings to the persistent training data.

# 5. Retrain the SVM using the stored embeddings.

# 6. Save the updated face model + label encoder.

# 7. Reload the live recognition system automatically.

#

# IMPORTANT

# ---------

# Existing students' videos are NOT required.

# Their previously stored FaceNet embeddings are reused.

#

# A critical NumPy label-truncation bug has been fixed.

# NEVER use:

#

#     np.full(..., dtype=str)

#

# because it can create a one-character Unicode array.

#

# Labels are handled using dtype=object and explicit validation.

# ============================================================



import os

import cv2

import joblib

import threading

import traceback



import numpy as np



from datetime import datetime

from pathlib import Path



from sklearn.svm import SVC

from sklearn.preprocessing import LabelEncoder



from mtcnn import MTCNN

from keras_facenet import FaceNet





# ============================================================

# PATHS

# ============================================================



BASE_DIR = Path(__file__).resolve().parent



DATASET_DIR = BASE_DIR / "dataset"

MODELS_DIR = BASE_DIR / "models"

AI_ENGINE_MODELS_DIR = BASE_DIR / "ai_engine" / "models"

UPLOADS_DIR = BASE_DIR / "uploads" / "videos"



FACE_MODEL_FILE = MODELS_DIR / "face_model.pkl"

LABEL_ENCODER_FILE = MODELS_DIR / "label_encoder.pkl"



TRAINING_DATA_FILE = MODELS_DIR / "face_training_data.pkl"



AI_FACE_MODEL_FILE = AI_ENGINE_MODELS_DIR / "face_model.pkl"

AI_LABEL_ENCODER_FILE = AI_ENGINE_MODELS_DIR / "label_encoder.pkl"





# ============================================================

# TRAINING SETTINGS

# ============================================================



MIN_NEW_SAMPLES = 5



# Maximum number of frames sampled from a video.

MAX_VIDEO_FRAMES = 30



# SVM settings

SVM_C = 1.0

SVM_KERNEL = "linear"



# Minimum face size used when choosing between detections.

MIN_FACE_SIZE = 40





# ============================================================

# CREATE REQUIRED DIRECTORIES

# ============================================================



DATASET_DIR.mkdir(parents=True, exist_ok=True)

MODELS_DIR.mkdir(parents=True, exist_ok=True)

AI_ENGINE_MODELS_DIR.mkdir(parents=True, exist_ok=True)

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)





# ============================================================

# GLOBAL AI MODELS

# ============================================================



_mtcnn = None

_facenet = None



_model_lock = threading.Lock()





# ============================================================

# TRAINING STATE

# ============================================================



_training_state = {

    "status": "idle",

    "message": "Face training system ready.",

    "student_id": None,

    "students": [],

    "samples": 0,

    "started_at": None,

    "completed_at": None,

    "error": None,

}





# ============================================================

# STUDENT ID HELPERS

# ============================================================



def normalize_student_id(student_id):

    """

    Normalize a student ID safely.



    IMPORTANT:

    We return a Python string, not a NumPy string.

    """



    if student_id is None:

        raise ValueError("Student ID cannot be None.")



    student_id = str(student_id).strip()



    if not student_id:

        raise ValueError("Student ID cannot be empty.")



    return student_id





# ============================================================

# TRAINING STATE FUNCTIONS

# ============================================================



def _set_training_state(

    status,

    message,

    student_id=None,

    students=None,

    samples=0,

    error=None,

):

    """

    Update global training state.

    """



    global _training_state



    _training_state["status"] = status

    _training_state["message"] = message

    _training_state["student_id"] = student_id



    if students is not None:

        _training_state["students"] = list(students)



    _training_state["samples"] = int(samples)



    if status == "training":

        _training_state["started_at"] = datetime.now().isoformat()

        _training_state["completed_at"] = None



    if status in ("completed", "failed"):

        _training_state["completed_at"] = datetime.now().isoformat()



    _training_state["error"] = error





def get_training_state():

    """

    Used by routes/model_routes.py.



    Returns a copy so external code cannot accidentally modify

    the internal state.

    """



    return dict(_training_state)





# ============================================================

# DATABASE STATUS HELPER

# ============================================================



def _update_student_status(
    student_id,
    is_model_trained=None,
    face_training_status=None,
    face_training_error=None,
):
    """Update face-training status in MongoDB students collection."""
    try:
        from database import students_collection

        student_id = normalize_student_id(student_id)
        update_fields = {}

        if is_model_trained is not None:
            update_fields["is_model_trained"] = bool(is_model_trained)

        if face_training_status is not None:
            update_fields["face_training_status"] = str(face_training_status)

        if face_training_error is not None:
            update_fields["face_training_error"] = str(face_training_error)

        if is_model_trained is True:
            update_fields["face_model_updated_at"] = datetime.now()

        if not update_fields:
            return False

        result = students_collection.update_one(
            {"student_id": student_id},
            {"$set": update_fields},
        )

        if result.matched_count == 0:
            print(f"WARNING: Student {student_id} was not found in MongoDB.")
            return False

        print(
            f"DB FACE STATUS UPDATED: {student_id} -> "
            f"{update_fields.get('face_training_status', 'unchanged')}"
        )
        return True

    except Exception as exc:
        print(
            f"WARNING: Could not update MongoDB face-training status "
            f"for {student_id}: {exc}"
        )
        traceback.print_exc()
        return False


# LOAD MTCNN + FACENET

# ============================================================



def load_face_models():

    """

    Load MTCNN and FaceNet only once.

    """



    global _mtcnn

    global _facenet



    with _model_lock:



        if _mtcnn is None:

            print("Loading MTCNN...")

            _mtcnn = MTCNN()



        if _facenet is None:

            print("Loading FaceNet...")

            _facenet = FaceNet()



        print("MTCNN and FaceNet loaded.")



    return _mtcnn, _facenet





# ============================================================

# STUDENT DATASET DIRECTORY

# ============================================================



def get_student_dataset_dir(student_id):

    """

    Return:



        backend/dataset/<student_id>/



    """



    student_id = normalize_student_id(student_id)



    student_dir = DATASET_DIR / student_id



    student_dir.mkdir(parents=True, exist_ok=True)



    return student_dir





# ============================================================

# EXTRACT VIDEO FRAMES

# ============================================================



def extract_frames_from_video(video_path, student_id):

    """

    Extract sampled frames from the student's uploaded video.



    Frames are now ALSO SAVED to:



        backend/dataset/<student_id>/extracted_frames/



    This makes it easy to verify that the new student's video

    was actually processed.



    Returns:

        list[np.ndarray]

    """



    student_id = normalize_student_id(student_id)



    video_path = Path(video_path)



    if not video_path.exists():

        raise FileNotFoundError(

            f"Training video does not exist: {video_path}"

        )



    print()

    print(f"🎥 Processing video for {student_id}")

    print(f"🎥 Video: {video_path.name}")



    cap = cv2.VideoCapture(str(video_path))



    if not cap.isOpened():

        raise RuntimeError(

            f"Could not open training video: {video_path}"

        )



    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    fps = float(cap.get(cv2.CAP_PROP_FPS))



    print(f"Total frames: {total_frames}")

    print(f"FPS: {fps:.2f}")



    if total_frames <= 0:

        cap.release()

        raise RuntimeError(

            "Training video contains no readable frames."

        )



    # --------------------------------------------------------

    # Choose evenly distributed frames.

    # --------------------------------------------------------



    frame_count = min(MAX_VIDEO_FRAMES, total_frames)



    if frame_count <= 1:

        frame_indices = [0]

    else:

        frame_indices = np.linspace(

            0,

            total_frames - 1,

            frame_count,

            dtype=int,

        )



    # --------------------------------------------------------

    # Dataset output directory

    # --------------------------------------------------------



    student_dir = get_student_dataset_dir(student_id)



    frames_dir = student_dir / "extracted_frames"



    frames_dir.mkdir(parents=True, exist_ok=True)



    frames = []



    saved_count = 0



    for index in frame_indices:



        cap.set(cv2.CAP_PROP_POS_FRAMES, int(index))



        success, frame = cap.read()



        if not success or frame is None:

            continue



        frames.append(frame)



        # ----------------------------------------------------

        # Save the original sampled frame.

        # ----------------------------------------------------



        filename = (

            frames_dir /

            f"frame_{saved_count:04d}.jpg"

        )



        cv2.imwrite(

            str(filename),

            frame,

            [

                int(cv2.IMWRITE_JPEG_QUALITY),

                95,

            ],

        )



        saved_count += 1



    cap.release()



    print(f"📸 Extracted {len(frames)} frames")

    print(f"💾 Saved {saved_count} frames to:")

    print(f"   {frames_dir}")



    if len(frames) == 0:

        raise RuntimeError(

            "No frames could be extracted from the training video."

        )



    return frames





# ============================================================

# SELECT BEST FACE

# ============================================================



def select_best_face(detections):

    """

    Select the largest/highest-quality face detection.

    """



    if not detections:

        return None



    valid = []



    for detection in detections:



        box = detection.get("box")



        if not box or len(box) < 4:

            continue



        x, y, w, h = box



        w = abs(int(w))

        h = abs(int(h))



        if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:

            continue



        confidence = float(

            detection.get("confidence", 0.0)

        )



        area = w * h



        valid.append(

            (

                confidence,

                area,

                detection,

            )

        )



    if not valid:

        return None



    # Prefer confidence, then face area.

    valid.sort(

        key=lambda item: (

            item[0],

            item[1],

        ),

        reverse=True,

    )



    return valid[0][2]





# ============================================================

# EXTRACT FACENET EMBEDDINGS

# ============================================================



def extract_embeddings_from_frames(frames):

    """

    Detect a face in each frame and extract its FaceNet

    512-dimensional embedding.



    Returns:

        np.ndarray with shape (N, 512)

    """



    mtcnn, facenet = load_face_models()



    embeddings = []



    for frame_number, frame in enumerate(frames):



        try:



            rgb = cv2.cvtColor(

                frame,

                cv2.COLOR_BGR2RGB,

            )



            detections = mtcnn.detect_faces(rgb)



            detection = select_best_face(detections)



            if detection is None:

                continue



            x, y, w, h = detection["box"]



            x = max(0, int(x))

            y = max(0, int(y))

            w = int(w)

            h = int(h)



            if w <= 0 or h <= 0:

                continue



            height, width = rgb.shape[:2]



            x2 = min(width, x + w)

            y2 = min(height, y + h)



            if x2 <= x or y2 <= y:

                continue



            face = rgb[y:y2, x:x2]



            if face.size == 0:

                continue



            # FaceNet expects 160x160 images.

            face = cv2.resize(

                face,

                (160, 160),

                interpolation=cv2.INTER_AREA,

            )



            face = face.astype(np.float32)



            # Add batch dimension.

            face_batch = np.expand_dims(

                face,

                axis=0,

            )



            embedding = facenet.embeddings(

                face_batch

            )



            if embedding is None:

                continue



            embedding = np.asarray(

                embedding,

                dtype=np.float32,

            )



            if embedding.ndim == 2:

                embedding = embedding[0]



            if embedding.shape[0] != 512:

                print(

                    f"⚠️ Invalid embedding size "

                    f"at frame {frame_number}: "

                    f"{embedding.shape}"

                )

                continue



            if not np.all(np.isfinite(embedding)):

                print(

                    f"⚠️ Invalid numerical embedding "

                    f"at frame {frame_number}"

                )

                continue



            embeddings.append(embedding)



        except Exception as exc:



            print(

                f"⚠️ Could not process frame "

                f"{frame_number}: {exc}"

            )



    if not embeddings:

        return np.empty(

            (0, 512),

            dtype=np.float32,

        )



    return np.asarray(

        embeddings,

        dtype=np.float32,

    )





# ============================================================

# LOAD PERSISTENT TRAINING DATA

# ============================================================



def load_training_data():

    """

    Load persistent FaceNet embeddings.



    Expected format:



    {

        "X": np.ndarray,       # N x 512

        "y": np.ndarray,       # student IDs

        "updated_at": ...

    }

    """



    if not TRAINING_DATA_FILE.exists():

        return None, None



    try:



        data = joblib.load(

            TRAINING_DATA_FILE

        )



        if not isinstance(data, dict):

            print(

                "⚠️ Training data file has "

                "an unexpected format."

            )

            return None, None



        X = data.get("X")

        y = data.get("y")



        if X is None or y is None:

            print(

                "⚠️ Training data is missing X or y."

            )

            return None, None



        X = np.asarray(

            X,

            dtype=np.float32,

        )



        # ----------------------------------------------------

        # VERY IMPORTANT:

        # Labels are converted to object dtype.

        #

        # This prevents student IDs from being silently

        # truncated by NumPy fixed-width strings.

        # ----------------------------------------------------



        y = np.asarray(

            [

                normalize_student_id(label)

                for label in y

            ],

            dtype=object,

        )



        if len(X) != len(y):

            raise RuntimeError(

                "Training data X/y length mismatch: "

                f"{len(X)} embeddings vs "

                f"{len(y)} labels."

            )



        if X.ndim != 2 or X.shape[1] != 512:

            raise RuntimeError(

                f"Invalid training embedding shape: "

                f"{X.shape}. Expected (N, 512)."

            )



        print(

            f"📦 Loaded persistent training data: "

            f"{len(X)} embeddings"

        )



        print(

            f"👥 Students in stored data: "

            f"{len(set(y.tolist()))}"

        )



        return X, y



    except Exception as exc:



        print(

            f"❌ Failed to load persistent "

            f"training data: {exc}"

        )



        traceback.print_exc()



        return None, None





# ============================================================

# SAVE PERSISTENT TRAINING DATA

# ============================================================



def save_training_data(X, y):

    """

    Save FaceNet embeddings and student labels.



    Labels are deliberately saved as object/string-safe

    Python values.

    """



    X = np.asarray(

        X,

        dtype=np.float32,

    )



    # IMPORTANT:

    # Do not use np.asarray(y, dtype=str).

    #

    # Use object dtype so IDs cannot be truncated.

    y = np.asarray(

        [

            normalize_student_id(label)

            for label in y

        ],

        dtype=object,

    )



    if X.ndim != 2 or X.shape[1] != 512:

        raise RuntimeError(

            f"Cannot save invalid embeddings: {X.shape}"

        )



    if len(X) != len(y):

        raise RuntimeError(

            "Cannot save training data because "

            "X and y have different lengths."

        )



    unique_students = sorted(

        set(y.tolist())

    )



    if not unique_students:

        raise RuntimeError(

            "Cannot save training data with zero students."

        )



    data = {

        "X": X,

        "y": y,

        "updated_at": datetime.now().isoformat(),

    }



    joblib.dump(

        data,

        TRAINING_DATA_FILE,

    )



    print()

    print("💾 Training data saved:")

    print(f"   File: {TRAINING_DATA_FILE}")

    print(f"   Samples: {len(X)}")

    print(f"   Students: {len(unique_students)}")



    return True





# ============================================================

# ATOMIC JOBLIB SAVE

# ============================================================



def _atomic_joblib_dump(data, target_path):

    """

    Save a joblib file through a temporary file first.



    This reduces the chance of leaving a partially written

    model if the process is interrupted.

    """



    target_path = Path(target_path)



    target_path.parent.mkdir(

        parents=True,

        exist_ok=True,

    )



    temp_path = target_path.with_suffix(

        target_path.suffix + ".tmp"

    )



    joblib.dump(

        data,

        temp_path,

    )



    os.replace(

        temp_path,

        target_path,

    )





# ============================================================

# BOOTSTRAP FROM EXISTING SVM

# ============================================================



def bootstrap_training_data_from_existing_model():

    """

    One-time compatibility helper.



    If face_training_data.pkl does not exist but an old

    face_model.pkl does, try to create persistent training

    data from the existing SVM support vectors.



    IMPORTANT:

    This is only a fallback for old installations.



    Existing student videos are NOT required.



    NOTE:

    SVM support vectors are not the same thing as the original

    training embeddings. Therefore this fallback is only used

    once, before persistent training data exists.

    """



    if TRAINING_DATA_FILE.exists():

        return load_training_data()



    if not FACE_MODEL_FILE.exists():

        return None, None



    if not LABEL_ENCODER_FILE.exists():

        return None, None



    try:



        print()

        print("=" * 70)

        print("🔄 BOOTSTRAPPING PERSISTENT TRAINING DATA")

        print("=" * 70)



        model = joblib.load(

            FACE_MODEL_FILE

        )



        label_encoder = joblib.load(

            LABEL_ENCODER_FILE

        )



        if not hasattr(model, "support_vectors_"):

            print(

                "⚠️ Existing model has no support_vectors_."

            )

            return None, None



        support_vectors = np.asarray(

            model.support_vectors_,

            dtype=np.float32,

        )



        if support_vectors.ndim != 2:

            print(

                "⚠️ Invalid support-vector shape:"

                f" {support_vectors.shape}"

            )

            return None, None



        classes = list(

            getattr(

                label_encoder,

                "classes_",

                [],

            )

        )



        if not classes:

            print(

                "⚠️ Existing label encoder has "

                "no classes."

            )

            return None, None



        # ----------------------------------------------------

        # We need one label for each support vector.

        #

        # In a normal linear SVC, support_ vectors_ correspond

        # to support indices. There is no universal direct

        # class array exposed by all sklearn versions.

        #

        # Therefore this fallback is intentionally conservative.

        # ----------------------------------------------------



        if hasattr(model, "_n_support"):

            n_support = list(

                model._n_support

            )

        else:

            n_support = None



        if (

            n_support is None

            or len(n_support) != len(classes)

            or sum(n_support) != len(support_vectors)

        ):

            print(

                "⚠️ Cannot safely reconstruct labels "

                "for existing support vectors."

            )



            print(

                "   Existing videos may be required "

                "for a clean initial dataset."

            )



            return None, None



        labels = []



        for class_index, count in enumerate(

            n_support

        ):



            label = normalize_student_id(

                classes[class_index]

            )



            for _ in range(int(count)):

                labels.append(label)



        X = support_vectors



        # IMPORTANT: object dtype.

        y = np.asarray(

            labels,

            dtype=object,

        )



        print(

            f"Recovered {len(X)} embeddings."

        )



        print(

            f"Recovered {len(set(y.tolist()))} students."

        )



        save_training_data(

            X,

            y,

        )



        return X, y



    except Exception as exc:



        print(

            "❌ Could not bootstrap existing model:"

            f" {exc}"

        )



        traceback.print_exc()



        return None, None





# ============================================================

# GET EXISTING TRAINING DATA

# ============================================================



def get_existing_training_data():

    """

    Get persistent training data.



    First tries face_training_data.pkl.



    If it does not exist, tries the one-time bootstrap.

    """



    X, y = load_training_data()



    if X is not None and y is not None:

        return X, y



    return bootstrap_training_data_from_existing_model()





# ============================================================

# SAVE FACE MODEL

# ============================================================



def save_face_model(model, label_encoder):

    """

    Save face model and label encoder to both locations

    used by Student360.

    """



    MODELS_DIR.mkdir(

        parents=True,

        exist_ok=True,

    )



    AI_ENGINE_MODELS_DIR.mkdir(

        parents=True,

        exist_ok=True,

    )



    # --------------------------------------------------------

    # Validate encoder before saving.

    # --------------------------------------------------------



    classes = [

        normalize_student_id(label)

        for label in label_encoder.classes_

    ]



    if not classes:

        raise RuntimeError(

            "Cannot save face model with zero classes."

        )



    # --------------------------------------------------------

    # Save main model.

    # --------------------------------------------------------



    _atomic_joblib_dump(

        model,

        FACE_MODEL_FILE,

    )



    _atomic_joblib_dump(

        label_encoder,

        LABEL_ENCODER_FILE,

    )



    print()

    print("💾 Face model saved successfully.")

    print(f"   {FACE_MODEL_FILE}")

    print(f"   {LABEL_ENCODER_FILE}")



    # --------------------------------------------------------

    # Save AI engine copies.

    # --------------------------------------------------------



    _atomic_joblib_dump(

        model,

        AI_FACE_MODEL_FILE,

    )



    _atomic_joblib_dump(

        label_encoder,

        AI_LABEL_ENCODER_FILE,

    )



    print("💾 AI engine model copy saved.")

    print(f"   {AI_FACE_MODEL_FILE}")

    print(f"   {AI_LABEL_ENCODER_FILE}")



    return True





# ============================================================

# HOT RELOAD LIVE FACE MODEL

# ============================================================



def reload_live_face_models():

    """

    Reload the live face-recognition model.



    Uses the reload_face_models() function from

    routes.process_video when available.

    """



    print()

    print("🔄 Reloading live face-recognition model...")



    try:



        # ----------------------------------------------------

        # Import the live route module.

        # ----------------------------------------------------



        from routes.process_video import reload_face_models



        result = reload_face_models()



        print(

            f"🔄 Model reload result: {result}"

        )



        return result



    except ImportError as exc:



        print(

            "⚠️ Could not import live model reload:"

            f" {exc}"

        )



        return {

            "status": "warning",

            "message": str(exc),

        }



    except Exception as exc:



        print(

            "⚠️ Live face model reload failed:"

            f" {exc}"

        )



        traceback.print_exc()



        return {

            "status": "error",

            "message": str(exc),

        }





# ============================================================

# TRAIN FACE RECOGNITION MODEL

# ============================================================



def train_face_recognition_model(

    new_student_id,

    new_embeddings,

):

    """

    Add the NEW student's embeddings to the persistent dataset

    and retrain the SVM.



    Existing students are NOT processed from video.



    Parameters:

        new_student_id:

            Student ID being registered now.



        new_embeddings:

            FaceNet embeddings extracted ONLY from the new

            student's video.

    """



    new_student_id = normalize_student_id(

        new_student_id

    )



    # --------------------------------------------------------

    # Validate new embeddings.

    # --------------------------------------------------------



    new_embeddings = np.asarray(

        new_embeddings,

        dtype=np.float32,

    )



    if new_embeddings.ndim != 2:

        raise RuntimeError(

            f"New embeddings must be 2D. "

            f"Received {new_embeddings.shape}."

        )



    if new_embeddings.shape[1] != 512:

        raise RuntimeError(

            f"FaceNet embeddings must have 512 "

            f"dimensions. Received "

            f"{new_embeddings.shape[1]}."

        )



    if len(new_embeddings) < MIN_NEW_SAMPLES:

        raise RuntimeError(

            f"Only {len(new_embeddings)} valid face "

            f"embeddings were extracted for "

            f"{new_student_id}."

            f" Minimum required: {MIN_NEW_SAMPLES}."

        )



    # --------------------------------------------------------

    # Validate numerical values.

    # --------------------------------------------------------



    if not np.all(

        np.isfinite(new_embeddings)

    ):

        raise RuntimeError(

            "New embeddings contain NaN or infinity."

        )



    # --------------------------------------------------------

    # Load existing persistent data.

    # --------------------------------------------------------



    X_old, y_old = get_existing_training_data()



    if X_old is None or y_old is None:

        raise RuntimeError(

            "No persistent face training data exists. "

            "The system cannot safely add a new student "

            "without an existing trained model/dataset."

        )



    X_old = np.asarray(

        X_old,

        dtype=np.float32,

    )



    # IMPORTANT:

    # Explicitly use object dtype for labels.

    y_old = np.asarray(

        [

            normalize_student_id(label)

            for label in y_old

        ],

        dtype=object,

    )



    if X_old.ndim != 2 or X_old.shape[1] != 512:

        raise RuntimeError(

            f"Existing training data has invalid "

            f"embedding shape: {X_old.shape}"

        )



    if len(X_old) != len(y_old):

        raise RuntimeError(

            "Existing X/y length mismatch."

        )



    # --------------------------------------------------------

    # Display current data.

    # --------------------------------------------------------



    print()

    print(

        f"📦 Loaded persistent training data: "

        f"{len(X_old)} embeddings"

    )



    print(

        f"👥 Students in stored data: "

        f"{len(set(y_old.tolist()))}"

    )



    # --------------------------------------------------------

    # CRITICAL FIX

    #

    # DO NOT use:

    #

    #     np.full(len(X_new), new_student_id, dtype=str)

    #

    # because dtype=str can become <U1.

    #

    # Instead create a Python list and convert it to object.

    # --------------------------------------------------------



    y_new = np.asarray(

        [

            new_student_id

            for _ in range(len(new_embeddings))

        ],

        dtype=object,

    )



    # --------------------------------------------------------

    # HARD VALIDATION OF NEW LABEL

    # --------------------------------------------------------



    if not all(

        isinstance(label, str)

        for label in y_new.tolist()

    ):

        raise RuntimeError(

            "New student labels are not strings."

        )



    if not all(

        label == new_student_id

        for label in y_new.tolist()

    ):

        raise RuntimeError(

            "New student labels were corrupted "

            "before training."

        )



    # --------------------------------------------------------

    # Combine old + new embeddings.

    # --------------------------------------------------------



    X_combined = np.concatenate(

        [

            X_old,

            new_embeddings,

        ],

        axis=0,

    ).astype(

        np.float32

    )



    # --------------------------------------------------------

    # Combine labels using object dtype.

    # --------------------------------------------------------



    y_combined = np.concatenate(

        [

            y_old,

            y_new,

        ],

        axis=0,

    ).astype(

        object

    )



    # --------------------------------------------------------

    # CRITICAL VALIDATION

    #

    # Make absolutely sure the new student survived the

    # concatenation operation.

    # --------------------------------------------------------



    combined_students = set(

        y_combined.tolist()

    )



    if new_student_id not in combined_students:

        raise RuntimeError(

            "CRITICAL TRAINING ERROR: "

            f"{new_student_id} disappeared while "

            "combining training labels."

        )



    new_student_count = sum(

        label == new_student_id

        for label in y_combined.tolist()

    )



    if new_student_count != len(new_embeddings):

        raise RuntimeError(

            "CRITICAL TRAINING ERROR: "

            f"Expected {len(new_embeddings)} samples "

            f"for {new_student_id}, but found "

            f"{new_student_count}."

        )



    # --------------------------------------------------------

    # Print summary.

    # --------------------------------------------------------



    print()

    print("=" * 70)

    print("TRAINING DATA SUMMARY")

    print("=" * 70)



    print(

        f"Total face samples: {len(X_combined)}"

    )



    print(

        f"Students with samples: "

        f"{len(combined_students)}"

    )



    for student in sorted(

        combined_students

    ):



        count = sum(

            label == student

            for label in y_combined.tolist()

        )



        print(

            f"{student}: {count} samples"

        )



    # --------------------------------------------------------

    # Train label encoder.

    # --------------------------------------------------------



    label_encoder = LabelEncoder()



    # LabelEncoder accepts strings safely.

    y_for_encoder = np.asarray(

        y_combined.tolist(),

        dtype=object,

    )



    encoded_labels = label_encoder.fit_transform(

        y_for_encoder

    )



    # --------------------------------------------------------

    # Verify new student is in encoder.

    # --------------------------------------------------------



    encoder_classes = [

        normalize_student_id(label)

        for label in label_encoder.classes_

    ]



    if new_student_id not in encoder_classes:

        raise RuntimeError(

            "CRITICAL TRAINING ERROR: "

            f"{new_student_id} is not present "

            "in LabelEncoder classes."

        )



    print()

    print("🧠 Training SVM...")



    # --------------------------------------------------------

    # Train SVM.

    # --------------------------------------------------------



    model = SVC(

        C=SVM_C,

        kernel=SVM_KERNEL,

        probability=True,

        class_weight="balanced",

    )



    model.fit(

        X_combined,

        encoded_labels,

    )



    # --------------------------------------------------------

    # Verify trained SVM classes.

    # --------------------------------------------------------



    model_class_indices = list(

        model.classes_

    )



    model_student_classes = []



    for index in model_class_indices:



        index = int(index)



        if index < 0 or index >= len(

            label_encoder.classes_

        ):

            raise RuntimeError(

                "SVM contains an invalid class index."

            )



        model_student_classes.append(

            normalize_student_id(

                label_encoder.inverse_transform(

                    [index]

                )[0]

            )

        )



    if new_student_id not in model_student_classes:

        raise RuntimeError(

            "CRITICAL TRAINING ERROR: "

            f"{new_student_id} is not present "

            "in the trained SVM."

        )



    # --------------------------------------------------------

    # Save persistent training data.

    # --------------------------------------------------------



    save_training_data(

        X_combined,

        y_combined,

    )



    # --------------------------------------------------------

    # Save model.

    # --------------------------------------------------------



    save_face_model(

        model,

        label_encoder,

    )



    # --------------------------------------------------------

    # FINAL VERIFICATION AFTER SAVE

    # --------------------------------------------------------



    saved_encoder = joblib.load(

        LABEL_ENCODER_FILE

    )



    saved_classes = [

        normalize_student_id(label)

        for label in saved_encoder.classes_

    ]



    if new_student_id not in saved_classes:

        raise RuntimeError(

            "CRITICAL SAVE ERROR: "

            f"{new_student_id} is missing from "

            "the saved label encoder."

        )



    # --------------------------------------------------------

    # Print classes.

    # --------------------------------------------------------



    print()

    print("🎯 FACE MODEL CLASSES")

    print("=" * 70)



    for student in saved_classes:

        print(f"   {student}")



    print("=" * 70)



    print()

    print("✅ SVM retraining completed successfully.")



    return {

        "status": "success",

        "student_id": new_student_id,

        "new_samples": len(new_embeddings),

        "total_samples": len(X_combined),

        "students": saved_classes,

        "model_file": str(FACE_MODEL_FILE),

        "label_encoder_file": str(LABEL_ENCODER_FILE),

    }





# ============================================================

# ADD ONE NEW STUDENT FROM VIDEO

# ============================================================



def add_student_from_video(

    student_id,

    video_path,

):

    """

    Complete training pipeline for ONE newly registered

    student.



    ONLY this student's video is processed.

    """



    student_id = normalize_student_id(

        student_id

    )



    _set_training_state(

        status="training",

        message=(

            f"Processing face training for "

            f"{student_id}"

        ),

        student_id=student_id,

        error=None,

    )



    _update_student_status(

        student_id,

        is_model_trained=False,

        face_training_status="processing",

        face_training_error="",

    )



    try:



        print()

        print("=" * 70)

        print(

            f"🎥 STARTING FACE TRAINING FOR "

            f"{student_id}"

        )

        print("=" * 70)



        # ----------------------------------------------------

        # Step 1: Extract video frames.

        # ----------------------------------------------------



        frames = extract_frames_from_video(

            video_path,

            student_id,

        )



        # ----------------------------------------------------

        # Step 2: Extract FaceNet embeddings.

        # ----------------------------------------------------



        embeddings = extract_embeddings_from_frames(

            frames

        )



        print()

        print(

            f"📸 {student_id}: "

            f"{len(embeddings)} valid embeddings"

        )



        if len(embeddings) < MIN_NEW_SAMPLES:

            raise RuntimeError(

                f"{student_id}: only "

                f"{len(embeddings)} valid face samples "

                f"were found."

            )



        print(

            f"✅ {student_id}: "

            f"{len(embeddings)} valid face samples"

        )



        # ----------------------------------------------------

        # Step 3: Add to persistent dataset + retrain.

        # ----------------------------------------------------



        result = train_face_recognition_model(

            student_id,

            embeddings,

        )



        # ----------------------------------------------------

        # Step 4: Hot reload live recognition.

        # ----------------------------------------------------



        reload_result = (

            reload_live_face_models()

        )



        result["reload"] = reload_result



        # ----------------------------------------------------

        # Mark database training complete.

        # ----------------------------------------------------



        _update_student_status(

            student_id,

            is_model_trained=True,

            face_training_status="completed",

            face_training_error="",

        )



        _set_training_state(

            status="completed",

            message=(

                f"Face training completed "

                f"successfully for {student_id}."

            ),

            student_id=student_id,

            students=result.get(

                "students",

                [],

            ),

            samples=result.get(

                "total_samples",

                0,

            ),

            error=None,

        )



        print()

        print("=" * 70)

        print("✅ FACE TRAINING PROCESS COMPLETED")

        print("=" * 70)



        print(

            f"Face recognition training completed "

            f"successfully for {student_id}."

        )



        print("=" * 70)



        return result



    except Exception as exc:



        error_message = str(exc)



        print()

        print("=" * 70)

        print("❌ FACE TRAINING FAILED")

        print("=" * 70)



        print(

            f"Student: {student_id}"

        )



        print(

            f"Error: {error_message}"

        )



        traceback.print_exc()



        _update_student_status(

            student_id,

            is_model_trained=False,

            face_training_status="failed",

            face_training_error=error_message,

        )



        _set_training_state(

            status="failed",

            message=(

                f"Face training failed "

                f"for {student_id}."

            ),

            student_id=student_id,

            error=error_message,

        )



        # ----------------------------------------------------

        # Re-raise so the background task/log can report the

        # failure correctly.

        # ----------------------------------------------------



        raise





# ============================================================

# RETRAIN REGISTERED STUDENTS

# ============================================================



def retrain_registered_students(

    student_ids=None,

):

    """

    Background-task entry point used by register.py.



    IMPORTANT:

    If student_ids contains one new student, ONLY that

    student's video is processed.



    Example:



        retrain_registered_students(

            ["ITBIN-2211-0110"]

        )



    will NOT process old students' videos.

    """



    print()

    print("=" * 70)

    print("🔄 AUTOMATIC REGISTERED-STUDENT RETRAINING")

    print("=" * 70)



    # --------------------------------------------------------

    # Normalize input.

    # --------------------------------------------------------



    if student_ids is None:

        student_ids = []



    if isinstance(

        student_ids,

        str,

    ):

        student_ids = [

            student_ids

        ]



    student_ids = [

        normalize_student_id(student_id)

        for student_id in student_ids

    ]



    # Remove duplicates while preserving order.

    student_ids = list(

        dict.fromkeys(student_ids)

    )



    print(

        f"👥 Students to process: "

        f"{len(student_ids)}"

    )



    for student_id in student_ids:

        print(

            f"   • {student_id}"

        )



    if not student_ids:

        print(

            "⚠️ No students were supplied."

        )



        _set_training_state(

            status="idle",

            message="No students to train.",

            students=[],

        )



        return {

            "status": "idle",

            "message": "No students to train.",

        }



    successful = []

    failed = []



    # --------------------------------------------------------

    # Process each supplied NEW student.

    # --------------------------------------------------------



    for student_id in student_ids:



        # ----------------------------------------------------

        # Find uploaded video.

        # ----------------------------------------------------



        video_candidates = [

            UPLOADS_DIR / f"{student_id}.mp4",

            UPLOADS_DIR / f"{student_id}.MP4",

            UPLOADS_DIR / f"{student_id}.avi",

            UPLOADS_DIR / f"{student_id}.AVI",

            UPLOADS_DIR / f"{student_id}.mov",

            UPLOADS_DIR / f"{student_id}.MOV",

            UPLOADS_DIR / f"{student_id}.mkv",

            UPLOADS_DIR / f"{student_id}.MKV",

            UPLOADS_DIR / f"{student_id}.webm",

            UPLOADS_DIR / f"{student_id}.WEBM",

        ]



        video_path = None



        for candidate in video_candidates:



            if candidate.exists():

                video_path = candidate

                break



        # ----------------------------------------------------

        # If not found, search by stem as a fallback.

        # ----------------------------------------------------



        if video_path is None:



            for candidate in UPLOADS_DIR.glob(

                f"{student_id}.*"

            ):



                if candidate.is_file():

                    video_path = candidate

                    break



        if video_path is None:



            error_message = (

                f"No training video found for "

                f"{student_id} in {UPLOADS_DIR}"

            )



            print()

            print(

                f"❌ {error_message}"

            )



            failed.append(

                {

                    "student_id": student_id,

                    "error": error_message,

                }

            )



            _update_student_status(

                student_id,

                is_model_trained=False,

                face_training_status="failed",

                face_training_error=error_message,

            )



            continue



        print()

        print(

            f"🎥 Video: {video_path.name}"

        )



        try:



            result = add_student_from_video(

                student_id,

                video_path,

            )



            successful.append(

                result

            )



        except Exception as exc:



            failed.append(

                {

                    "student_id": student_id,

                    "error": str(exc),

                }

            )



    # --------------------------------------------------------

    # Final result.

    # --------------------------------------------------------



    if failed and successful:



        status = "partial"



    elif failed:



        status = "failed"



    else:



        status = "success"



    print()

    print("=" * 70)

    print(

        "🏁 REGISTERED-STUDENT RETRAINING FINISHED"

    )

    print("=" * 70)



    print(

        f"Successful: {len(successful)}"

    )



    print(

        f"Failed: {len(failed)}"

    )



    if failed:



        print()

        print("❌ Failed students:")



        for item in failed:



            print(

                f"   {item['student_id']}: "

                f"{item['error']}"

            )



    print("=" * 70)



    return {

        "status": status,

        "successful": successful,

        "failed": failed,

    }





# ============================================================

# PROCESS STUDENT DATASET

# ============================================================



def process_student_dataset(

    student_id,

):

    """

    Compatibility function.



    Processes image files already present under:



        backend/dataset/<student_id>/



    including:



        backend/dataset/<student_id>/extracted_frames/



    This is NOT used by the new registration workflow,

    which processes the uploaded video directly.



    It is retained for compatibility with older code.

    """



    student_id = normalize_student_id(

        student_id

    )



    student_dir = (

        DATASET_DIR / student_id

    )



    if not student_dir.exists():

        raise FileNotFoundError(

            f"Student dataset directory does not exist: "

            f"{student_dir}"

        )



    print()

    print(

        f"📁 Processing dataset for {student_id}"

    )



    # --------------------------------------------------------

    # Recursively find images.

    #

    # This fixes the earlier problem where nested

    # extracted_frames directories were skipped.

    # --------------------------------------------------------



    image_files = []



    supported_extensions = {

        ".jpg",

        ".jpeg",

        ".png",

        ".bmp",

        ".webp",

    }



    for path in student_dir.rglob("*"):



        if not path.is_file():

            continue



        if path.suffix.lower() in supported_extensions:

            image_files.append(path)



    image_files.sort()



    if not image_files:



        raise RuntimeError(

            f"No image files found under "

            f"{student_dir}"

        )



    print(

        f"📸 Found {len(image_files)} image files."

    )



    frames = []



    for image_path in image_files:



        frame = cv2.imread(

            str(image_path)

        )



        if frame is not None:

            frames.append(frame)



    if not frames:



        raise RuntimeError(

            f"Could not read any images from "

            f"{student_dir}"

        )



    embeddings = extract_embeddings_from_frames(

        frames

    )



    print(

        f"📸 {student_id}: "

        f"{len(embeddings)} valid embeddings"

    )



    if len(embeddings) < MIN_NEW_SAMPLES:



        raise RuntimeError(

            f"{student_id}: only "

            f"{len(embeddings)} valid embeddings."

        )



    return train_face_recognition_model(

        student_id,

        embeddings,

    )





# ============================================================

# STARTUP MESSAGE

# ============================================================



print()

print("=" * 70)

print("🎓 Student360 Face Training System Loaded")

print("=" * 70)

print(f"Dataset directory: {DATASET_DIR}")

print(f"Models directory:  {MODELS_DIR}")

print(f"Training data:     {TRAINING_DATA_FILE}")

print(f"Video directory:   {UPLOADS_DIR}")

print("=" * 70)