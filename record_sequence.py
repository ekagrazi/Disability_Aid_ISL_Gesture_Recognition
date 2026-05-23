import cv2
import numpy as np
import mediapipe as mp
import os

DATASET_DIR = "dataset"
MAX_LEN = 40
DOMINANT = "Right"

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils


# ---------------- HAND FEATURE EXTRACTION ----------------

def extract_hand_features(pts):

    pts = np.array(pts)

    wrist = pts[0]
    pts = pts - wrist

    scale = np.linalg.norm(pts[5]) + 1e-6
    pts = pts / scale

    # 1️⃣ Joint coordinates (63)
    joint_coords = pts.flatten()

    # 2️⃣ Pairwise distances (210)
    pairwise = []
    for i in range(21):
        for j in range(i+1, 21):
            d = np.linalg.norm(pts[i] - pts[j])
            pairwise.append(d)

    pairwise = np.array(pairwise)

    # 3️⃣ Palm normal (3)
    v1 = pts[5]
    v2 = pts[17]
    normal = np.cross(v1, v2)
    normal = normal / (np.linalg.norm(normal) + 1e-6)

    return np.concatenate([joint_coords, pairwise, normal])  # 276


# ---------------- RECORD FUNCTION ----------------

def record_word(word, samples=30):

    os.makedirs(f"{DATASET_DIR}/{word}", exist_ok=True)

    cap = cv2.VideoCapture(0)
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    for s in range(samples):

        print(f"Recording {word} sample {s}")
        sequence = []
        recording = False

        while True:

            ret, frame = cap.read()
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            results = hands.process(rgb)

            dom = np.zeros(276)
            nondom = np.zeros(276)

            dom_pts = None
            nondom_pts = None

            if results.multi_hand_landmarks:
                for hand_landmarks, handedness in zip(
                        results.multi_hand_landmarks,
                        results.multi_handedness):

                    pts = [[p.x, p.y, p.z]
                           for p in hand_landmarks.landmark]

                    if handedness.classification[0].label == DOMINANT:
                        dom = extract_hand_features(pts)
                        dom_pts = np.array(pts)
                    else:
                        nondom = extract_hand_features(pts)
                        nondom_pts = np.array(pts)

                    mp_draw.draw_landmarks(
                        frame, hand_landmarks,
                        mp_hands.HAND_CONNECTIONS
                    )

            # 4️⃣ Cross-hand fingertip distances (25)
            cross = np.zeros(25)
            if dom_pts is not None and nondom_pts is not None:

                tips = [4,8,12,16,20]
                idx = 0
                for i in tips:
                    for j in tips:
                        cross[idx] = np.linalg.norm(
                            dom_pts[i] - nondom_pts[j]
                        )
                        idx += 1

            full_frame = np.concatenate([dom, nondom, cross])  # 577

            if recording:
                sequence.append(full_frame)
                cv2.putText(frame,"RECORDING",
                            (10,50),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1,(0,0,255),2)

            cv2.imshow("Recorder", frame)
            key = cv2.waitKey(1)

            if key == 27:
                cap.release()
                cv2.destroyAllWindows()
                return

            if key == 32:
                recording = not recording
                if not recording and len(sequence) > 5:
                    break

        seq = np.array(sequence)

        # Pad/trim
        if len(seq) >= MAX_LEN:
            seq = seq[:MAX_LEN]
        else:
            pad = np.zeros((MAX_LEN - len(seq), 577))
            seq = np.vstack([seq, pad])

        # Velocity
        vel = np.diff(seq, axis=0)
        vel = np.vstack([vel[0], vel])

        seq = np.concatenate([seq, vel], axis=1)  # 1154

        np.save(f"{DATASET_DIR}/{word}/sample_{s}.npy", seq)
        print("Saved:", seq.shape)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    word = input("Enter word name: ")
    record_word(word, 30)
