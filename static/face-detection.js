import { FilesetResolver, FaceDetector } from '/static/vendor/mediapipe/vision_bundle.mjs';

let detector = null;
let running = false;
let rafId = null;
let lastRun = 0;
const TARGET_FPS = 12;
const FRAME_MS = 1000 / TARGET_FPS;

// Cached DOM refs — populated once at start() to avoid per-frame querySelector
let elOverlay = null;
let elBbox = null;
let elLabel = null;
let elBadge = null;

async function init() {
  if (detector) return detector;
  const fileset = await FilesetResolver.forVisionTasks('/static/vendor/mediapipe');
  const modelBytes = await fetch('/static/vendor/mediapipe/blaze_face_short_range.tflite')
    .then(r => r.arrayBuffer())
    .then(b => new Uint8Array(b));
  detector = await FaceDetector.createFromModelBuffer(fileset, modelBytes);
  await detector.setOptions({ runningMode: 'VIDEO', minDetectionConfidence: 0.4 });
  return detector;
}

function pickLargest(detections) {
  if (!detections || !detections.length) return null;
  let best = null, bestArea = 0;
  for (const d of detections) {
    const b = d.boundingBox;
    const area = b.width * b.height;
    if (area > bestArea) { bestArea = area; best = d; }
  }
  return best;
}

function render(detection, video) {
  if (!elOverlay || !elBbox || !elLabel || !elBadge) return;
  const btnCapture = document.getElementById('btnCapture');

  if (!detection) {
    elBbox.classList.add('hidden');
    elOverlay.classList.add('searching');
    elOverlay.classList.remove('low-conf');
    elBadge.textContent = 'PROCURANDO';
    if (btnCapture) btnCapture.disabled = true;
    return;
  }

  const b = detection.boundingBox;
  const conf = detection.categories?.[0]?.score || 0;
  const lowConf = conf < 0.6;

  const vw = video.videoWidth || 640;
  const vh = video.videoHeight || 480;
  const rect = video.getBoundingClientRect();
  const scaleX = rect.width / vw;
  const scaleY = rect.height / vh;

  elBbox.classList.remove('hidden');
  elOverlay.classList.remove('searching');
  elOverlay.classList.toggle('low-conf', lowConf);
  elBbox.style.left = `${b.originX * scaleX}px`;
  elBbox.style.top = `${b.originY * scaleY}px`;
  elBbox.style.width = `${b.width * scaleX}px`;
  elBbox.style.height = `${b.height * scaleY}px`;
  elLabel.textContent = lowConf ? 'FACE BAIXA QUALIDADE' : `FACE ${Math.round(conf * 100)}%`;
  elBadge.textContent = 'DETECTANDO';
  if (btnCapture) btnCapture.disabled = lowConf;
}

async function loop(video) {
  if (!running) return;
  const now = performance.now();
  if (now - lastRun >= FRAME_MS && video.readyState >= 2) {
    lastRun = now;
    try {
      const res = detector.detectForVideo(video, now);
      render(pickLargest(res.detections), video);
    } catch (e) { console.warn('[face-detect] frame error', e); }
  }
  rafId = requestAnimationFrame(() => loop(video));
}

export async function start() {
  if (running) return;
  try {
    await init();
  } catch (e) {
    console.warn('[face-detect] init failed', e);
    return;
  }
  const video = document.getElementById('webcam');
  if (!video) return;
  elOverlay = document.getElementById('faceOverlay');
  elBbox = document.getElementById('faceBbox');
  elLabel = document.getElementById('faceLabel');
  elBadge = document.getElementById('liveBadge');
  running = true;
  lastRun = 0;
  loop(video);
}

export function stop() {
  running = false;
  if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
  const btnCapture = document.getElementById('btnCapture');
  if (btnCapture) btnCapture.disabled = false;
  if (elBbox) elBbox.classList.add('hidden');
}

window.__faceDetect = { start, stop };
