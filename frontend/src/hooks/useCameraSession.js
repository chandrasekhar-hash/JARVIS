import { useState, useEffect, useRef, useCallback } from 'react';
import { cameraController } from '../services/CameraController';

export function useCameraSession(backendUrl = '') {
  const [isSessionActive, setIsSessionActive] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [activeFocus, setActiveFocus] = useState(null);
  const [statusText, setStatusText] = useState('Camera idle');
  const [sceneChanged, setSceneChanged] = useState(false);
  const [latestAnalysis, setLatestAnalysis] = useState(null);
  const [error, setError] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const timerRef = useRef(null);
  const isInteractingRef = useRef(false);

  // Generate UUID for session tracking
  const generateSessionId = () => {
    return 'session_' + Math.random().toString(36).substring(2, 9) + '_' + Date.now();
  };

  /**
   * Starts a new Camera Vision Session.
   */
  const startSession = useCallback(async () => {
    setError(null);
    try {
      setStatusText('Requesting camera permission...');
      await cameraController.startCamera();

      const newSessionId = generateSessionId();
      setStatusText('Initializing session backend...');

      const formData = new FormData();
      formData.append('session_id', newSessionId);

      const res = await fetch(`${backendUrl}/api/vision/camera/session/start`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Failed to start session: ${res.statusText}`);
      }

      const data = await res.json();
      setSessionId(newSessionId);
      setIsSessionActive(true);
      setActiveFocus(data.active_focus || null);
      setStatusText('Camera Vision Session active');
      return newSessionId;
    } catch (err) {
      console.error('[useCameraSession] Error starting session:', err);
      setError(err.message);
      cameraController.stopCamera();
      setIsSessionActive(false);
      setStatusText('Session start failed');
      return null;
    }
  }, [backendUrl]);

  /**
   * Sends a compressed camera frame + optional user prompt to backend.
   */
  const sendFrame = useCallback(async (userPrompt = null) => {
    if (!isSessionActive || !sessionId || isProcessing) {
      return null;
    }

    try {
      setIsProcessing(true);
      const frameData = await cameraController.captureCompressedFrame(1280, 0.8);
      if (!frameData || !frameData.blob) {
        setIsProcessing(false);
        return null;
      }

      const formData = new FormData();
      formData.append('session_id', sessionId);
      formData.append('file', frameData.blob, `frame_${frameData.timestamp}.jpg`);
      if (userPrompt) {
        formData.append('prompt', userPrompt);
        isInteractingRef.current = true;
      }

      const res = await fetch(`${backendUrl}/api/vision/camera/session/frame`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Frame analysis error: ${res.statusText}`);
      }

      const data = await res.json();
      setSceneChanged(Boolean(data.scene_changed));

      if (data.active_focus) {
        setActiveFocus(data.active_focus);
      }

      if (data.text) {
        setLatestAnalysis(data);
      }

      setStatusText(data.scene_changed ? 'Scene update detected' : 'Scene stable');
      setIsProcessing(false);
      return data;
    } catch (err) {
      console.error('[useCameraSession] Error sending frame:', err);
      setError(err.message);
      setIsProcessing(false);
      return null;
    }
  }, [isSessionActive, sessionId, isProcessing, backendUrl]);

  /**
   * Ends current session and purges hardware & backend memory.
   */
  const endSession = useCallback(async () => {
    if (sessionId) {
      try {
        const formData = new FormData();
        formData.append('session_id', sessionId);
        await fetch(`${backendUrl}/api/vision/camera/session/end`, {
          method: 'POST',
          body: formData,
        });
      } catch (_) {}
    }

    cameraController.stopCamera();
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    setIsSessionActive(false);
    setSessionId(null);
    setActiveFocus(null);
    setLatestAnalysis(null);
    setStatusText('Session ended');
  }, [sessionId, backendUrl]);

  // Adaptive capture scheduler (1000ms active vs 5000ms idle)
  useEffect(() => {
    if (!isSessionActive) {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      return;
    }

    const interval = isInteractingRef.current ? 1000 : 5000;
    timerRef.current = setInterval(() => {
      sendFrame();
      // Decay interaction frequency back to idle after frame check
      isInteractingRef.current = false;
    }, interval);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [isSessionActive, sendFrame]);

  // Auto cleanup on unmount
  useEffect(() => {
    return () => {
      cameraController.stopCamera();
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  return {
    isSessionActive,
    sessionId,
    activeFocus,
    statusText,
    sceneChanged,
    latestAnalysis,
    error,
    isProcessing,
    startSession,
    sendFrame,
    endSession,
  };
}
