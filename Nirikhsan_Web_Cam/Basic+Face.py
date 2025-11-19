import cv2
import insightface
from insightface.app import FaceAnalysis

# Initialize ArcFace (InsightFace pre-trained model)
app = FaceAnalysis(name='antelopev2')   # ArcFace model
app.prepare(ctx_id=0, det_size=(640, 640))  # ctx_id=0 for CPU, use GPU if available

# Start webcam
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Detect faces + embeddings
    faces = app.get(frame)

    for face in faces:
        # Bounding box
        bbox = face.bbox.astype(int)
        cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)

        # Embedding vector (512-dim)
        embedding = face.embedding

        # Display info
        cv2.putText(frame, "Face Detected (ArcFace)", (bbox[0], bbox[1]-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    cv2.imshow("ArcFace Face Detection", frame)

    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
