import { useRef, useState, useEffect, useCallback } from 'react';
import Webcam from 'react-webcam';
import { motion, AnimatePresence } from 'framer-motion';
import { Camera, Wifi, WifiOff, Loader2, AlertCircle, Trash2 } from 'lucide-react';

const WS_URL = 'ws://localhost:8000/ws/predict';
const CAPTURE_INTERVAL_MS = 75; // ~13 FPS — avoids overloading backend
const CONFIDENCE_THRESHOLD = 0.70;

const STATUS_CONFIG = {
  connecting: { color: 'bg-yellow-400', label: 'Connecting…', Icon: Loader2, spin: true },
  connected: { color: 'bg-mint-400', label: 'Connected', Icon: Wifi, spin: false },
  disconnected: { color: 'bg-slate-500', label: 'Disconnected', Icon: WifiOff, spin: false },
  error: { color: 'bg-red-400', label: 'Error', Icon: AlertCircle, spin: false },
};

export default function Cam() {
  const webcamRef = useRef(null);
  const wsRef = useRef(null);
  const intervalRef = useRef(null);

  const [status, setStatus] = useState('disconnected');
  const [currentWord, setCurrentWord] = useState(null);
  const [confidence, setConfidence] = useState(0);
  const [sentence, setSentence] = useState([]);
  const [bufferInfo, setBufferInfo] = useState(null);

  // Track the last word added to avoid duplicates
  const lastWordRef = useRef(null);

  /* ── WebSocket Lifecycle ──────────────────────────────────────────────── */

  const connect = useCallback(() => {
    if (wsRef.current) return;

    setStatus('connecting');
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      setStatus('connected');
      wsRef.current = ws;

      // Start capturing frames at throttled rate
      intervalRef.current = setInterval(() => {
        if (
          webcamRef.current &&
          ws.readyState === WebSocket.OPEN
        ) {
          const screenshot = webcamRef.current.getScreenshot();
          if (screenshot) {
            // Send full data URL — backend handles stripping the header
            ws.send(screenshot);
          }
        }
      }, CAPTURE_INTERVAL_MS);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.error) {
        console.warn('[WS]', data.error);
        return;
      }

      // Update current word and confidence
      if (data.word != null) {
        setCurrentWord(data.word);
        setConfidence(data.confidence);

        // Sentence generation: confidence > threshold AND different from last word
        if (data.word && data.confidence > CONFIDENCE_THRESHOLD) {
          if (data.word !== lastWordRef.current) {
            lastWordRef.current = data.word;
            setSentence((prev) => [...prev, data.word]);
          }
        }
      } else if (data.buffering != null) {
        setBufferInfo({ current: data.buffering, target: data.buffer_target });
      }
    };

    ws.onerror = () => setStatus('error');

    ws.onclose = () => {
      setStatus('disconnected');
      wsRef.current = null;
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const disconnect = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (wsRef.current) wsRef.current.close();
    wsRef.current = null;
  }, []);

  const clearSentence = useCallback(() => {
    setSentence([]);
    lastWordRef.current = null;
  }, []);

  /* ── Mount / Unmount ──────────────────────────────────────────────────── */

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  /* ── Render ───────────────────────────────────────────────────────────── */

  const { color, label, Icon, spin } = STATUS_CONFIG[status];
  const confidencePct = (confidence * 100).toFixed(1);

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Camera size={20} className="text-accent-400" />
          <h2 className="text-lg font-semibold text-white">Live Inference</h2>
        </div>

        {/* Connection status badge */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-700 border border-glass-border text-xs font-medium">
          <span className={`w-2 h-2 rounded-full ${color}`} />
          <Icon size={13} className={`text-slate-400 ${spin ? 'animate-spin' : ''}`} />
          <span className="text-slate-300">{label}</span>
        </div>
      </div>

      {/* Video + overlay container */}
      <div className="relative flex-1 rounded-2xl overflow-hidden border border-glass-border bg-black">
        <Webcam
          ref={webcamRef}
          audio={false}
          mirrored
          screenshotFormat="image/jpeg"
          screenshotQuality={0.6}
          videoConstraints={{ facingMode: 'user', width: 1280, height: 720 }}
          className="w-full h-full object-cover"
        />

        {/* ── Sentence overlay (bottom) ─────────────────────────────────── */}
        <div className="absolute bottom-0 left-0 right-0 px-6 py-4 bg-gradient-to-t from-black/80 via-black/50 to-transparent">
          <div className="flex items-end justify-between gap-4">
            <div className="flex-1 min-w-0">
              {sentence.length > 0 ? (
                <motion.p
                  key={sentence.length}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-2xl font-bold text-white tracking-wide leading-tight"
                >
                  {sentence.join(' ')}
                </motion.p>
              ) : (
                <p className="text-sm text-slate-500 italic">
                  Sentence will appear here…
                </p>
              )}
            </div>

            {/* Clear sentence button */}
            {sentence.length > 0 && (
              <motion.button
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                onClick={clearSentence}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-surface-700/80 backdrop-blur-sm border border-glass-border text-xs text-slate-300 hover:bg-red-500/20 hover:text-red-300 hover:border-red-500/30 transition-all cursor-pointer shrink-0"
              >
                <Trash2 size={12} />
                Clear
              </motion.button>
            )}
          </div>
        </div>

        {/* ── Current word + confidence overlay (top-right corner) ────── */}
        <AnimatePresence mode="wait">
          {currentWord && (
            <motion.div
              key={currentWord}
              initial={{ opacity: 0, x: 20, scale: 0.9 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 20, scale: 0.9 }}
              transition={{ type: 'spring', stiffness: 300, damping: 25 }}
              className="absolute top-4 right-4 flex items-center gap-3 px-4 py-3 rounded-2xl bg-surface-800/80 backdrop-blur-xl border border-glass-border shadow-2xl"
            >
              <div>
                <p className="text-lg font-bold text-white tracking-wide">
                  {currentWord}
                </p>
                <p className="text-[10px] text-slate-500 uppercase tracking-widest mt-0.5">
                  Detected
                </p>
              </div>
              {/* Confidence bar */}
              <div className="flex flex-col items-end gap-1">
                <span className="text-sm font-semibold text-mint-400">
                  {confidencePct}%
                </span>
                <div className="w-20 h-1.5 rounded-full bg-surface-600 overflow-hidden">
                  <motion.div
                    className="h-full rounded-full bg-gradient-to-r from-accent-400 to-mint-400"
                    initial={{ width: 0 }}
                    animate={{ width: `${confidencePct}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Buffer progress (while filling) */}
        <AnimatePresence>
          {bufferInfo && !currentWord && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute top-4 right-4 flex items-center gap-2 px-3 py-2 rounded-xl bg-surface-800/70 backdrop-blur-md border border-glass-border text-xs text-slate-400"
            >
              <Loader2 size={12} className="animate-spin" />
              Buffering {bufferInfo.current}/{bufferInfo.target}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Disconnected overlay */}
        {status === 'disconnected' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/60 backdrop-blur-sm">
            <WifiOff size={40} className="text-slate-500 mb-3" />
            <p className="text-slate-400 text-sm mb-4">Backend disconnected</p>
            <button
              onClick={connect}
              className="px-5 py-2 rounded-xl bg-accent-500 text-white text-sm font-medium hover:bg-accent-600 transition-colors shadow-lg shadow-accent-500/25 cursor-pointer"
            >
              Reconnect
            </button>
          </div>
        )}

        {/* Error overlay */}
        {status === 'error' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/60 backdrop-blur-sm">
            <AlertCircle size={40} className="text-red-400 mb-3" />
            <p className="text-red-300 text-sm mb-4">Connection error</p>
            <button
              onClick={() => { disconnect(); connect(); }}
              className="px-5 py-2 rounded-xl bg-accent-500 text-white text-sm font-medium hover:bg-accent-600 transition-colors shadow-lg shadow-accent-500/25 cursor-pointer"
            >
              Retry
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
