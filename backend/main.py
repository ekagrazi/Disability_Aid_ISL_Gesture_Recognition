"""
main.py — FastAPI server with WebSocket endpoint for real-time ISL inference.

The inference pipeline mirrors live_inference.py exactly:
  • 577-dim frame  = dom(276) + nondom(276) + cross(25)
  • 1154-dim input = seq(577) ∥ velocity(577)
  • Prediction smoothed with a 5-frame majority-vote buffer
"""

import base64
import os
from collections import deque

import cv2
import mediapipe as mp
import numpy as np
import torch
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from model import BiLSTM, extract_hand_features, load_model, DEVICE

# ── App Setup ────────────────────────────────────────────────────────────────

app = FastAPI(title="ISL Recognition API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Load Model at Startup ────────────────────────────────────────────────────

MODEL_PATH = os.path.join(os.path.dirname(__file__), "slr_model.pth")

# Only load if the weights file is non-empty (prevents crash with placeholder)
if os.path.exists(MODEL_PATH) and os.path.getsize(MODEL_PATH) > 0:
    model, class_names = load_model(MODEL_PATH)
else:
    model, class_names = None, []
    print("[WARN] slr_model.pth is missing or empty — inference disabled.")

# ── MediaPipe Hands (shared across connections) ──────────────────────────────

mp_hands = mp.solutions.hands


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": model is not None}


# ── WebSocket Inference Endpoint ─────────────────────────────────────────────

MAX_LEN = 40
DOMINANT = "Right"


@app.websocket("/ws/predict")
async def predict(websocket: WebSocket):
    await websocket.accept()

    # Per-connection state
    sequence_buffer: deque = deque(maxlen=MAX_LEN)
    pred_buffer: deque = deque(maxlen=5)

    # Per-connection MediaPipe instance
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    try:
        while True:
            # 1. Receive base64-encoded JPEG frame
            raw = await websocket.receive_text()

            if model is None:
                await websocket.send_json(
                    {"error": "Model not loaded. Place trained slr_model.pth in backend/."}
                )
                continue

            # 2. Strip data-URL header if present, then decode
            data = raw.split(",")[1] if "," in raw else raw
            np_data = np.frombuffer(base64.b64decode(data), np.uint8)
            frame = cv2.imdecode(np_data, cv2.IMREAD_COLOR)

            if frame is None:
                await websocket.send_json({"error": "Invalid image data"})
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # 3. MediaPipe hand detection
            results = hands.process(rgb)

            dom = np.zeros(276)
            nondom = np.zeros(276)
            dom_pts = None
            nondom_pts = None

            if results.multi_hand_landmarks:
                for hand_landmarks, handedness in zip(
                    results.multi_hand_landmarks,
                    results.multi_handedness,
                ):
                    pts = [[p.x, p.y, p.z] for p in hand_landmarks.landmark]

                    if handedness.classification[0].label == DOMINANT:
                        dom = extract_hand_features(pts)
                        dom_pts = np.array(pts)
                    else:
                        nondom = extract_hand_features(pts)
                        nondom_pts = np.array(pts)

            # 4. Cross-hand fingertip distances (5×5 = 25)
            cross = np.zeros(25)
            if dom_pts is not None and nondom_pts is not None:
                tips = [4, 8, 12, 16, 20]
                idx = 0
                for i in tips:
                    for j in tips:
                        cross[idx] = np.linalg.norm(dom_pts[i] - nondom_pts[j])
                        idx += 1

            # 5. Concatenate → 577-dim frame vector
            full_frame = np.concatenate([dom, nondom, cross])
            sequence_buffer.append(full_frame)

            # 6. Run inference when buffer is full
            if len(sequence_buffer) == MAX_LEN:
                seq = np.array(sequence_buffer)

                # Velocity (first-order diff, prepend first row)
                vel = np.diff(seq, axis=0)
                vel = np.vstack([vel[0], vel])

                seq = np.concatenate([seq, vel], axis=1)  # → 1154

                seq_tensor = (
                    torch.tensor(seq, dtype=torch.float32)
                    .unsqueeze(0)
                    .to(DEVICE)
                )

                with torch.no_grad():
                    out = model(seq_tensor)
                    probs = torch.softmax(out, 1)
                    pred = torch.argmax(probs).item()
                    conf = probs[0][pred].item()

                if conf > 0.6:
                    pred_buffer.append(pred)
                    final = max(set(pred_buffer), key=pred_buffer.count)

                    await websocket.send_json(
                        {
                            "word": class_names[final],
                            "confidence": round(conf, 4),
                        }
                    )
                else:
                    await websocket.send_json(
                        {"word": None, "confidence": round(conf, 4)}
                    )
            else:
                # Buffer still filling — send progress
                await websocket.send_json(
                    {
                        "word": None,
                        "confidence": 0.0,
                        "buffering": len(sequence_buffer),
                        "buffer_target": MAX_LEN,
                    }
                )

    except WebSocketDisconnect:
        pass
    finally:
        hands.close()


# ── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
