import cv2
import numpy as np
import torch
import torch.nn as nn
import mediapipe as mp
from collections import deque

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MAX_LEN = 40
DOMINANT = "Right"

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils


# ---------------- MODEL ----------------

class BiLSTM(nn.Module):
    def __init__(self,input_size,nc):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size,
            128,
            num_layers=2,
            batch_first=True,
            bidirectional=True
        )
        self.fc = nn.Linear(256,nc)

    def forward(self,x):
        out,_ = self.lstm(x)
        out = out[:,-1,:]
        return self.fc(out)


# ---------------- HAND FEATURES ----------------

def extract_hand_features(pts):

    pts = np.array(pts)

    wrist = pts[0]
    pts = pts - wrist

    scale = np.linalg.norm(pts[5]) + 1e-6
    pts = pts / scale

    joint_coords = pts.flatten()  # 63

    pairwise = []
    for i in range(21):
        for j in range(i+1,21):
            pairwise.append(np.linalg.norm(pts[i]-pts[j]))
    pairwise = np.array(pairwise)  # 210

    v1 = pts[5]
    v2 = pts[17]
    normal = np.cross(v1,v2)
    normal = normal/(np.linalg.norm(normal)+1e-6)

    return np.concatenate([joint_coords,pairwise,normal])  # 276


# ---------------- LOAD MODEL ----------------

checkpoint = torch.load("slr_model.pth", map_location=DEVICE)
class_names = checkpoint["classes"]

model = BiLSTM(1154,len(class_names)).to(DEVICE)
model.load_state_dict(checkpoint["model_state"])
model.eval()


# ---------------- LIVE LOOP ----------------

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

sequence_buffer = deque(maxlen=MAX_LEN)
pred_buffer = deque(maxlen=5)

cap = cv2.VideoCapture(0)

while True:

    ret, frame = cap.read()
    frame = cv2.flip(frame,1)
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

            pts = [[p.x,p.y,p.z] for p in hand_landmarks.landmark]

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

    # Cross-hand fingertip distances
    cross = np.zeros(25)
    if dom_pts is not None and nondom_pts is not None:
        tips = [4,8,12,16,20]
        idx = 0
        for i in tips:
            for j in tips:
                cross[idx] = np.linalg.norm(
                    dom_pts[i]-nondom_pts[j]
                )
                idx += 1

    full_frame = np.concatenate([dom,nondom,cross])  # 577

    sequence_buffer.append(full_frame)

    if len(sequence_buffer) == MAX_LEN:

        seq = np.array(sequence_buffer)

        vel = np.diff(seq,axis=0)
        vel = np.vstack([vel[0],vel])

        seq = np.concatenate([seq,vel],axis=1)  # 1154

        seq_tensor = torch.tensor(seq,
                                  dtype=torch.float32
                                  ).unsqueeze(0).to(DEVICE)

        with torch.no_grad():
            out = model(seq_tensor)
            probs = torch.softmax(out,1)
            pred = torch.argmax(probs).item()
            conf = probs[0][pred].item()

        if conf > 0.6:
            pred_buffer.append(pred)
            final = max(set(pred_buffer),
                        key=pred_buffer.count)

            text = f"{class_names[final]} ({conf:.2f})"
            cv2.putText(frame,text,(10,40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,(0,255,0),2)

    cv2.imshow("Live",frame)

    if cv2.waitKey(1)==27:
        break

cap.release()
cv2.destroyAllWindows()
