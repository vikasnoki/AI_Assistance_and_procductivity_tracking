"""
Test script to verify emotion detection works with your setup
Run this before using the main app: python test_emotion_detection.py
"""

import cv2
import sys

print("Testing emotion detection setup...")
print("-" * 50)

# Test 1: OpenCV
try:
    import cv2
    print(f"✓ OpenCV installed: {cv2.__version__}")
except ImportError as e:
    print(f"✗ OpenCV not installed: {e}")
    sys.exit(1)

# Test 2: DeepFace
deepface_available = False
try:
    from deepface import DeepFace
    import h5py
    import tensorflow as tf
    print(f"✓ DeepFace installed")
    print(f"✓ TensorFlow: {tf.__version__}")
    print(f"✓ h5py: {h5py.__version__}")
    deepface_available = True
except ImportError as e:
    print(f"✗ DeepFace not available: {e}")

# Test 3: FER
fer_available = False
try:
    from fer import FER
    print(f"✓ FER installed")
    fer_available = True
except ImportError as e:
    print(f"✗ FER not available: {e}")

print("-" * 50)

if not deepface_available and not fer_available:
    print("\n❌ No emotion detection library available!")
    print("\nInstall one of:")
    print("  Option 1 (DeepFace): pip install deepface tensorflow tf-keras h5py")
    print("  Option 2 (FER):      pip install fer==22.4.0 tensorflow==2.15.0")
    sys.exit(1)

# Test 4: Camera
print("\nTesting camera access...")
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("✗ Cannot access camera!")
    sys.exit(1)

ret, frame = cap.read()
if not ret:
    print("✗ Cannot read from camera!")
    cap.release()
    sys.exit(1)

print(f"✓ Camera working: {frame.shape}")

# Test 5: Emotion Detection
print("\nTesting emotion detection (look at camera)...")

if deepface_available:
    try:
        print("Using DeepFace...")
        result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False, silent=True)
        if isinstance(result, list):
            result = result[0]
        emotion = result['dominant_emotion']
        confidence = result['emotion'][emotion]
        print(f"✓ DeepFace works! Detected: {emotion} ({confidence:.1f}%)")
    except Exception as e:
        print(f"✗ DeepFace error: {e}")
        deepface_available = False

if fer_available and not deepface_available:
    try:
        print("Using FER...")
        detector = FER(mtcnn=False)
        result = detector.detect_emotions(frame)
        if result and len(result) > 0:
            emotions = result[0]['emotions']
            emotion = max(emotions, key=emotions.get)
            confidence = emotions[emotion] * 100
            print(f"✓ FER works! Detected: {emotion} ({confidence:.1f}%)")
        else:
            print("⚠ FER couldn't detect face (try better lighting)")
    except Exception as e:
        print(f"✗ FER error: {e}")

cap.release()
print("\n" + "=" * 50)
print("✓ All tests passed! You're ready to use the app.")
print("=" * 50)