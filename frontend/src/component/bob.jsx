import React, { useState, useEffect, useRef } from 'react';
import * as THREE from 'three';

import { useAssistantConfig } from '../context/AssistantConfigContext';

// --- GLSL NOISE FUNCTIONS (shared by vertex + fragment shaders) ---
const noiseFunctions = `
    vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
    vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
    vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
    vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }
 
    float snoise(vec3 v) {
        const vec2  C = vec2(1.0/6.0, 1.0/3.0) ;
        const vec4  D = vec4(0.0, 0.5, 1.0, 2.0);
        vec3 i  = floor(v + dot(v, C.yyy) );
        vec3 x0 = v - i + dot(i, C.xxx) ;
        vec3 g = step(x0.yzx, x0.xyz);
        vec3 l = 1.0 - g;
        vec3 i1 = min( g.xyz, l.zxy );
        vec3 i2 = max( g.xyz, l.zxy );
        vec3 x1 = x0 - i1 + C.xxx;
        vec3 x2 = x0 - i2 + C.yyy;
        vec3 x3 = x0 - D.yyy;
        i = mod289(i);
        vec4 p = permute( permute( permute(
                    i.z + vec4(0.0, i1.z, i2.z, 1.0 ))
                + i.y + vec4(0.0, i1.y, i2.y, 1.0 ))
                + i.x + vec4(0.0, i1.x, i2.x, 1.0 ));
        float n_ = 0.142857142857;
        vec3  ns = n_ * D.wyz - D.xzx;
        vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
        vec4 x_ = floor(j * ns.z);
        vec4 y_ = floor(j - 7.0 * x_ );
        vec4 x = x_ *ns.x + ns.yyyy;
        vec4 y = y_ *ns.x + ns.yyyy;
        vec4 h = 1.0 - abs(x) - abs(y);
        vec4 b0 = vec4( x.xy, y.xy );
        vec4 b1 = vec4( x.zw, y.zw );
        vec4 s0 = floor(b0)*2.0 + 1.0;
        vec4 s1 = floor(b1)*2.0 + 1.0;
        vec4 sh = -step(h, vec4(0.0));
        vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy ;
        vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww ;
        vec3 p0 = vec3(a0.xy,h.x);
        vec3 p1 = vec3(a0.zw,h.y);
        vec3 p2 = vec3(a1.xy,h.z);
        vec3 p3 = vec3(a1.zw,h.w);
        vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
        p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
        vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
        m = m * m;
        return 42.0 * dot( m*m, vec4( dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3) ) );
    }
 
    float fbm(vec3 p) {
        float total = 0.0;
        float amplitude = 0.5;
        float frequency = 1.0;
        for (int i = 0; i < 3; i++) {
            total += snoise(p * frequency) * amplitude;
            amplitude *= 0.5;
            frequency *= 2.0;
        }
        return total;
    }
`;

// --- FIXED PARAMS (no manual GUI, tuned to preserve the original look) ---
const PARAMS = {
  // Colors (unchanged from source)
  colorDeep: 0x001433,
  colorMid: 0x0084ff,
  colorBright: 0x00ffe1,
  shellColor: 0x0066ff,
  shellOpacity: 0.41,
  plasmaScale: 0.2,
  plasmaBrightness: 1.31,
  voidThreshold: 0.09,

  // Idle breathing (always animating, never frozen)
  breatheSpeed: 0.45,
  breatheAmount: 0.012,
  idleDisplacement: 0.018,

  // Noise-driven organic deformation
  noiseScale1: 1.8,
  noiseScale2: 3.1,
  flowSpeed1: 0.16,
  flowSpeed2: 0.24,
  maxAudioDisplacement: 0.16,

  // Shell
  shellDisplacement: 0.012,

  // Plasma turbulence/flow reacting to voice
  baseFlowSpeed: 1.1,
  flowSpeedBoost: 1.6,
  turbulenceBoost: 0.9, // added multiplier on noise sampling frequency
  brightnessBoost: 1.35,

  // Particles
  swirlBaseSpeed: 0.06,
  swirlAudioBoost: 0.9,

  // Audio envelope follower
  noiseGate: 0.035,
  rmsGain: 3.6,
  attack: 0.4,   // fast rise
  release: 0.06, // slow fall

  // Pointer / tap interaction ("go big and small")
  tapImpulse: 7.0,
  moveImpulseScale: 18.0,
  maxMoveImpulse: 2.2,
  springStiffness: 70,
  springDamping: 6.5,
  interactionMaxScale: 0.22,
};

export default function Bob({
  blobColor,
  blobSize,
  isDraggable,
  setIsDraggable,
  blobPosition,
  setBlobPosition,
  jarvisFont,
  jarvisColor,
  jarvisFontSize,
  jarvisTextPosition,
  setJarvisTextPosition,
  isTextDraggable,
  setIsTextDraggable,
  blobSensitivity
}) {
  const { assistantName, voiceStatus, visualizerMode } = useAssistantConfig();
  const mountRef = useRef(null);

  // Audio refs (no React state — avoids re-renders during animation)
  const analyserRef = useRef(null);
  const timeDomainRef = useRef(null);
  const audioCtxRef = useRef(null);
  const streamRef = useRef(null);
  const audioLevelRef = useRef(0); // smoothed 0..1

  // Interaction refs (spring physics for tap/move "big and small" pulse)
  const pulseValueRef = useRef(0);
  const pulseVelocityRef = useRef(0);
  const lastPointerRef = useRef(null);

  // Drag and drop states for the orb
  const [dragStart, setDragStart] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  // Drag and drop states for J.A.R.V.I.S text
  const [textDragStart, setTextDragStart] = useState(null);
  const [isTextDragging, setIsTextDragging] = useState(false);

  // Drag handlers for J.A.R.V.I.S text
  const handleTextPointerDown = (e) => {
    if (!isTextDraggable) return;
    e.stopPropagation();
    setIsTextDragging(true);
    e.currentTarget.setPointerCapture(e.pointerId);

    const currentOrbPos = blobPosition || {
      x: window.innerWidth - blobSize - 20,
      y: window.innerHeight - blobSize - 20
    };
    const initialX = jarvisTextPosition ? jarvisTextPosition.x : (currentOrbPos.x + blobSize / 2 - 100);
    const initialY = jarvisTextPosition ? jarvisTextPosition.y : (currentOrbPos.y + blobSize + 20);

    setTextDragStart({
      offsetX: e.clientX - initialX,
      offsetY: e.clientY - initialY
    });
  };

  const handleTextPointerMove = (e) => {
    if (!isTextDragging || !textDragStart) return;
    e.stopPropagation();
    let newX = e.clientX - textDragStart.offsetX;
    let newY = e.clientY - textDragStart.offsetY;

    const margin = 10;
    newX = Math.max(margin, Math.min(window.innerWidth - 200 - margin, newX));
    newY = Math.max(margin, Math.min(window.innerHeight - 80 - margin, newY));

    setJarvisTextPosition({ x: newX, y: newY });
  };

  const handleTextPointerUp = (e) => {
    if (!isTextDragging) return;
    e.stopPropagation();
    setIsTextDragging(false);
    e.currentTarget.releasePointerCapture(e.pointerId);

    if (jarvisTextPosition) {
      localStorage.setItem('jarvis-text-position', JSON.stringify(jarvisTextPosition));
    }
  };

  // Sync settings ref to avoid stale closures in the animation loop
  const settingsRef = useRef({
    color: blobColor,
    size: blobSize,
    isDraggable: isDraggable,
    sensitivity: blobSensitivity,
    voiceStatus,
    visualizerMode
  });

  useEffect(() => {
    settingsRef.current = {
      color: blobColor,
      size: blobSize,
      isDraggable: isDraggable,
      sensitivity: blobSensitivity,
      voiceStatus,
      visualizerMode
    };
  }, [blobColor, blobSize, isDraggable, blobSensitivity, voiceStatus, visualizerMode]);

  // Handle position initialization relative to viewport on mount
  useEffect(() => {
    if (!blobPosition) {
      setBlobPosition({
        x: window.innerWidth - blobSize - 20,
        y: window.innerHeight - blobSize - 20
      });
    }
  }, [blobSize, blobPosition, setBlobPosition]);

  const handlePointerDownDrag = (e) => {
    if (!isDraggable) return;
    setIsDragging(true);
    e.currentTarget.setPointerCapture(e.pointerId);
    const posX = blobPosition ? blobPosition.x : (window.innerWidth - blobSize - 20);
    const posY = blobPosition ? blobPosition.y : (window.innerHeight - blobSize - 20);
    setDragStart({
      offsetX: e.clientX - posX,
      offsetY: e.clientY - posY
    });
  };

  const handlePointerMoveDrag = (e) => {
    if (!isDragging || !dragStart) return;
    let newX = e.clientX - dragStart.offsetX;
    let newY = e.clientY - dragStart.offsetY;

    // Constrain position boundaries
    const margin = 10;
    newX = Math.max(margin, Math.min(window.innerWidth - blobSize - margin, newX));
    newY = Math.max(margin, Math.min(window.innerHeight - blobSize - margin, newY));

    setBlobPosition({ x: newX, y: newY });
  };

  const handlePointerUpDrag = (e) => {
    if (!isDragging) return;
    setIsDragging(false);
    e.currentTarget.releasePointerCapture(e.pointerId);

    // Save position automatically to localStorage on drag release!
    if (blobPosition) {
      localStorage.setItem('jarvis-blob-position', JSON.stringify(blobPosition));
    }
  };

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    // Prevent body scrolling
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    // 1. SCENE SETUP (fixed camera, no OrbitControls)
    const scene = new THREE.Scene();

    const camera = new THREE.PerspectiveCamera(
      75,
      mount.clientWidth / mount.clientHeight,
      0.1,
      100
    );
    camera.position.z = 2.4;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.9;
    mount.appendChild(renderer.domElement);

    const mainGroup = new THREE.Group();
    scene.add(mainGroup);

    // 2. LIGHTS
    const pointLight = new THREE.PointLight(0x0088ff, 2.0, 10);
    mainGroup.add(pointLight);

    // 3. OUTER SHELL (glass, softly deforming + shimmering)
    const shellGeo = new THREE.SphereGeometry(1.0, 64, 64);

    const shellVertexShader = `
            uniform float uTime;
            uniform float uAudioLevel;
            uniform float uDisplacementAmount;
 
            varying vec3 vNormal;
            varying vec3 vViewPosition;
 
            ${noiseFunctions}
 
            void main() {
                vec3 nrm = normalize(normal);
                float n = fbm(position * 1.4 + vec3(0.0, uTime * 0.1, 0.0));
                float displacement = n * uDisplacementAmount * (0.5 + uAudioLevel);
                vec3 displaced = position + nrm * displacement;
 
                vNormal = normalize(normalMatrix * nrm);
                vec4 mvPosition = modelViewMatrix * vec4(displaced, 1.0);
                vViewPosition = -mvPosition.xyz;
                gl_Position = projectionMatrix * mvPosition;
            }
        `;

    const shellFragmentShader = `
            varying vec3 vNormal;
            varying vec3 vViewPosition;
            uniform vec3 uColor;
            uniform float uOpacity;
            uniform float uAudioLevel;
            uniform float uTime;
 
            void main() {
                float fresnel = pow(1.0 - dot(normalize(vNormal), normalize(vViewPosition)), 2.5);
                float shimmer = 0.9 + 0.1 * sin(uTime * 2.2 + fresnel * 6.0);
                float glow = uOpacity * (1.0 + uAudioLevel * 0.9);
                gl_FragColor = vec4(uColor, fresnel * glow * shimmer);
            }
        `;

    const shellBackMat = new THREE.ShaderMaterial({
      vertexShader: shellVertexShader,
      fragmentShader: shellFragmentShader,
      uniforms: {
        uTime: { value: 0 },
        uAudioLevel: { value: 0 },
        uDisplacementAmount: { value: PARAMS.shellDisplacement },
        uColor: { value: new THREE.Color(0x000055) },
        uOpacity: { value: 0.3 },
      },
      transparent: true,
      blending: THREE.AdditiveBlending,
      side: THREE.BackSide,
      depthWrite: false,
    });

    const shellFrontMat = new THREE.ShaderMaterial({
      vertexShader: shellVertexShader,
      fragmentShader: shellFragmentShader,
      uniforms: {
        uTime: { value: 0 },
        uAudioLevel: { value: 0 },
        uDisplacementAmount: { value: PARAMS.shellDisplacement },
        uColor: { value: new THREE.Color(PARAMS.shellColor) },
        uOpacity: { value: PARAMS.shellOpacity },
      },
      transparent: true,
      blending: THREE.AdditiveBlending,
      side: THREE.FrontSide,
      depthWrite: false,
    });

    mainGroup.add(new THREE.Mesh(shellGeo, shellBackMat));
    mainGroup.add(new THREE.Mesh(shellGeo, shellFrontMat));

    // 4. PLASMA (organic noise-displaced surface, same color palette)
    const plasmaGeo = new THREE.SphereGeometry(0.998, 128, 128);
    const plasmaMat = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uAudioLevel: { value: 0 },
        uIdleAmount: { value: PARAMS.idleDisplacement },
        uMaxAudioDisplacement: { value: PARAMS.maxAudioDisplacement },
        uNoiseScale1: { value: PARAMS.noiseScale1 },
        uNoiseScale2: { value: PARAMS.noiseScale2 },
        uFlowSpeed1: { value: PARAMS.flowSpeed1 },
        uFlowSpeed2: { value: PARAMS.flowSpeed2 },
        uScale: { value: PARAMS.plasmaScale },
        uBrightness: { value: PARAMS.plasmaBrightness },
        uThreshold: { value: PARAMS.voidThreshold },
        uTurbulence: { value: 1.0 },
        uFlowSpeed: { value: PARAMS.baseFlowSpeed },
        uColorDeep: { value: new THREE.Color(PARAMS.colorDeep) },
        uColorMid: { value: new THREE.Color(PARAMS.colorMid) },
        uColorBright: { value: new THREE.Color(PARAMS.colorBright) },
      },
      vertexShader: `
                uniform float uTime;
                uniform float uAudioLevel;
                uniform float uIdleAmount;
                uniform float uMaxAudioDisplacement;
                uniform float uNoiseScale1;
                uniform float uNoiseScale2;
                uniform float uFlowSpeed1;
                uniform float uFlowSpeed2;
 
                varying vec3 vPosition;
                varying vec3 vNormal;
                varying vec3 vViewPosition;
                varying float vDisplacement;
 
                ${noiseFunctions}
 
                void main() {
                    vPosition = position;
                    vec3 nrm = normalize(normal);
 
                    float n1 = fbm(position * uNoiseScale1 + vec3(0.0, uTime * uFlowSpeed1, 0.0));
                    float n2 = fbm(position * uNoiseScale2 - vec3(uTime * uFlowSpeed2, 0.0, uTime * uFlowSpeed2 * 0.5));
                    float noiseVal = mix(n1, n2, 0.5);
 
                    float displacementAmount = uIdleAmount + uAudioLevel * uMaxAudioDisplacement;
                    float displacement = noiseVal * displacementAmount;
                    vDisplacement = displacement;
 
                    vec3 displaced = position + nrm * displacement;
 
                    vNormal = normalize(normalMatrix * nrm);
                    vec4 mvPosition = modelViewMatrix * vec4(displaced, 1.0);
                    vViewPosition = -mvPosition.xyz;
                    gl_Position = projectionMatrix * mvPosition;
                }
            `,
      fragmentShader: `
                uniform float uTime;
                uniform float uScale;
                uniform float uBrightness;
                uniform float uThreshold;
                uniform float uTurbulence;
                uniform float uFlowSpeed;
                uniform vec3 uColorDeep;
                uniform vec3 uColorMid;
                uniform vec3 uColorBright;
 
                varying vec3 vPosition;
                varying vec3 vNormal;
                varying vec3 vViewPosition;
                varying float vDisplacement;
 
                ${noiseFunctions}
 
                void main() {
                    vec3 p = vPosition * uScale * uTurbulence;
                    float t0 = uTime * uFlowSpeed;
 
                    vec3 q = vec3(
                        fbm(p + vec3(0.0, t0 * 0.05, 0.0)),
                        fbm(p + vec3(5.2, 1.3, 2.8) + t0 * 0.05),
                        fbm(p + vec3(2.2, 8.4, 0.5) - t0 * 0.02)
                    );
 
                    float density = fbm(p + 2.0 * q);
                    float t = (density + 0.4) * 0.8;
                    float alpha = smoothstep(uThreshold, 0.7, t);
 
                    vec3 cWhite = vec3(1.0, 1.0, 1.0);
 
                    vec3 color = mix(uColorDeep, uColorMid, smoothstep(uThreshold, 0.5, t));
                    color = mix(color, uColorBright, smoothstep(0.5, 0.8, t));
                    color = mix(color, cWhite, smoothstep(0.8, 1.0, t));
 
                    // subtle extra glow where the surface bulges outward
                    color += clamp(vDisplacement, 0.0, 1.0) * 0.6 * uColorBright;
 
                    float facing = dot(normalize(vNormal), normalize(vViewPosition));
                    float depthFactor = (facing + 1.0) * 0.5;
                    float finalAlpha = alpha * (0.02 + 0.98 * depthFactor);
 
                    gl_FragColor = vec4(color * uBrightness, finalAlpha);
                }
            `,
      transparent: true,
      blending: THREE.AdditiveBlending,
      side: THREE.DoubleSide,
      depthWrite: false,
    });

    const plasmaMesh = new THREE.Mesh(plasmaGeo, plasmaMat);
    mainGroup.add(plasmaMesh);

    // 5. PARTICLES (swirl around the core, speed/brightness react to voice)
    const pCount = 600;
    const pPos = new Float32Array(pCount * 3);
    const pSizes = new Float32Array(pCount);
    const sphereRadius = 0.95;

    for (let i = 0; i < pCount; i++) {
      const r = sphereRadius * Math.cbrt(Math.random());
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);

      pPos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      pPos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      pPos[i * 3 + 2] = r * Math.cos(phi);

      pSizes[i] = Math.random();
    }

    const pGeo = new THREE.BufferGeometry();
    pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
    pGeo.setAttribute('aSize', new THREE.BufferAttribute(pSizes, 1));

    const pMat = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uAngle: { value: 0 },
        uAudioLevel: { value: 0 },
        uColor: { value: new THREE.Color(0xffffff) },
      },
      vertexShader: `
                uniform float uTime;
                uniform float uAngle;
                uniform float uAudioLevel;
                attribute float aSize;
                varying float vAlpha;
 
                void main() {
                    vec3 pos = position;
 
                    float radius = length(pos.xz);
                    float baseAngle = atan(pos.z, pos.x);
                    float phaseOffset = aSize * 6.2831853;
                    float newAngle = baseAngle + uAngle + phaseOffset * 0.15;
 
                    pos.x = radius * cos(newAngle);
                    pos.z = radius * sin(newAngle);
 
                    pos.y += sin(uTime * 0.3 + pos.x * 3.0) * 0.015 * (1.0 + uAudioLevel);
                    pos.x += cos(uTime * 0.2 + pos.z * 3.0) * 0.01;
 
                    vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
                    gl_Position = projectionMatrix * mvPosition;
 
                    float baseSize = 8.0 * aSize + 4.0;
                    gl_PointSize = baseSize * (1.0 + uAudioLevel * 0.5) * (1.0 / -mvPosition.z);
 
                    vAlpha = (0.7 + 0.3 * sin(uTime * 1.5 + aSize * 10.0)) * (0.8 + uAudioLevel * 0.6);
                }
            `,
      fragmentShader: `
                uniform vec3 uColor;
                varying float vAlpha;
                void main() {
                    vec2 uv = gl_PointCoord - vec2(0.5);
                    float dist = length(uv);
                    if(dist > 0.5) discard;
 
                    float glow = 1.0 - (dist * 2.0);
                    glow = pow(glow, 1.8);
 
                    gl_FragColor = vec4(uColor, glow * vAlpha);
                }
            `,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    const particles = new THREE.Points(pGeo, pMat);
    mainGroup.add(particles);

    // 6. AUDIO ENVELOPE FOLLOWER (RMS + noise gate + attack/release + simulation fallback)
    const readAudioLevel = () => {
      const mode = settingsRef.current.visualizerMode;
      const status = settingsRef.current.voiceStatus;
      const analyser = analyserRef.current;
      const data = timeDomainRef.current;

      if (mode === 'simulated' || !analyser || !data) {
        // MICROPHONE BYPASSED OR UNAVAILABLE: ANIMATE ARTIFICIALLY BASED ON VOICE STATUS
        if (status === 'responding') {
          const t = clock.getElapsedTime();
          const baseWave = Math.sin(t * 14.0) * 0.35 + Math.sin(t * 6.0) * 0.25;
          const noise = (Math.random() - 0.5) * 0.15;
          return Math.max(0, baseWave + noise + 0.3) * 0.4;
        }
        if (status === 'processing') {
          const t = clock.getElapsedTime();
          return 0.18 + Math.sin(t * 30.0) * 0.06 + (Math.random() * 0.04);
        }
        if (status === 'active') {
          const t = clock.getElapsedTime();
          return Math.max(0, Math.sin(t * 8.0) * 0.12);
        }
        return 0; // standard idle breathing
      }

      analyser.getByteTimeDomainData(data);
      let sumSquares = 0;
      for (let i = 0; i < data.length; i++) {
        const v = (data[i] - 128) / 128;
        sumSquares += v * v;
      }
      const rms = Math.sqrt(sumSquares / data.length);
      return rms > PARAMS.noiseGate ? rms : 0;
    };

    // 7. ANIMATION LOOP
    const clock = new THREE.Clock();
    let frameId;
    let angleAccum = 0;

    function animate() {
      frameId = requestAnimationFrame(animate);
      const dt = Math.min(clock.getDelta(), 0.05);
      const t = clock.getElapsedTime();

      // --- Audio envelope (smoothed, no jitter) ---
      const rawRms = readAudioLevel();
      const sensitivityVal = settingsRef.current.sensitivity !== undefined ? settingsRef.current.sensitivity : PARAMS.rmsGain;
      const target = Math.min(rawRms * sensitivityVal, 1.0);
      const rate = target > audioLevelRef.current ? PARAMS.attack : PARAMS.release;
      audioLevelRef.current += (target - audioLevelRef.current) * rate;
      const level = audioLevelRef.current;

      // --- Idle breathing (always alive, even with silence) ---
      const breathe =
        PARAMS.idleDisplacement + Math.sin(t * PARAMS.breatheSpeed) * PARAMS.breatheAmount;

      // --- Plasma uniforms ---
      plasmaMat.uniforms.uTime.value = t;
      plasmaMat.uniforms.uAudioLevel.value = level;
      plasmaMat.uniforms.uIdleAmount.value = breathe;
      plasmaMat.uniforms.uTurbulence.value = 1.0 + level * PARAMS.turbulenceBoost;
      plasmaMat.uniforms.uFlowSpeed.value = PARAMS.baseFlowSpeed + level * PARAMS.flowSpeedBoost;
      plasmaMat.uniforms.uBrightness.value = PARAMS.plasmaBrightness + level * PARAMS.brightnessBoost;

      plasmaMesh.rotation.y = t * 0.06;

      // --- Shell uniforms ---
      shellFrontMat.uniforms.uTime.value = t;
      shellFrontMat.uniforms.uAudioLevel.value = level;
      shellBackMat.uniforms.uTime.value = t;
      shellBackMat.uniforms.uAudioLevel.value = level * 0.6;

      // --- Dynamic colors sync ---
      const curColors = settingsRef.current.color;
      plasmaMat.uniforms.uColorDeep.value.set(curColors.deep);
      plasmaMat.uniforms.uColorMid.value.set(curColors.mid);
      plasmaMat.uniforms.uColorBright.value.set(curColors.bright);
      shellFrontMat.uniforms.uColor.value.set(curColors.shell);

      // --- Particle swirl (accelerates with voice, slows at idle) ---
      angleAccum += dt * (PARAMS.swirlBaseSpeed + level * PARAMS.swirlAudioBoost);
      angleAccum %= Math.PI * 2;
      pMat.uniforms.uTime.value = t;
      pMat.uniforms.uAngle.value = angleAccum;
      pMat.uniforms.uAudioLevel.value = level;

      // --- Gentle internal rotation (replaces manual rotation controls) ---
      mainGroup.rotation.x = Math.sin(t * 0.05) * 0.06;
      mainGroup.rotation.y += dt * 0.03;

      // --- Pointer/tap interaction spring ("big and small") ---
      pulseVelocityRef.current += -pulseValueRef.current * PARAMS.springStiffness * dt;
      pulseVelocityRef.current *= Math.max(0, 1 - PARAMS.springDamping * dt);
      pulseValueRef.current += pulseVelocityRef.current * dt;

      const interactionScale = 1 + pulseValueRef.current * PARAMS.interactionMaxScale;
      mainGroup.scale.setScalar(Math.max(0.4, interactionScale));

      renderer.render(scene, camera);
    }
    animate();

    // 8. AUTOMATIC MICROPHONE (handled dynamically in dedicated useEffect)
    let cancelled = false;

    // 9. RESIZE
    const handleResize = () => {
      if (!mount) return;
      camera.aspect = mount.clientWidth / mount.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(mount.clientWidth, mount.clientHeight);
    };
    window.addEventListener('resize', handleResize);
    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(mount);

    // 10. POINTER / TAP INTERACTION ("go big and small")
    const applyImpulse = (amount) => {
      pulseVelocityRef.current += amount;
    };

    const handlePointerDown = (e) => {
      applyImpulse(PARAMS.tapImpulse);
      lastPointerRef.current = { x: e.clientX, y: e.clientY };
    };

    const handlePointerMove = (e) => {
      if (!lastPointerRef.current) {
        lastPointerRef.current = { x: e.clientX, y: e.clientY };
        return;
      }
      const dx = e.clientX - lastPointerRef.current.x;
      const dy = e.clientY - lastPointerRef.current.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      lastPointerRef.current = { x: e.clientX, y: e.clientY };

      const impulse = Math.min(dist * (PARAMS.moveImpulseScale / 1000), PARAMS.maxMoveImpulse);
      if (impulse > 0.01) applyImpulse(impulse);
    };

    mount.addEventListener('pointerdown', handlePointerDown);
    mount.addEventListener('pointermove', handlePointerMove);

    // 11. CLEANUP
    return () => {
      cancelled = true;
      cancelAnimationFrame(frameId);
      window.removeEventListener('resize', handleResize);
      resizeObserver.disconnect();
      mount.removeEventListener('pointerdown', handlePointerDown);
      mount.removeEventListener('pointermove', handlePointerMove);

      renderer.dispose();
      shellGeo.dispose();
      plasmaGeo.dispose();
      pGeo.dispose();
      shellBackMat.dispose();
      shellFrontMat.dispose();
      plasmaMat.dispose();
      pMat.dispose();

      if (mount.contains(renderer.domElement)) {
        mount.removeChild(renderer.domElement);
      }

      // Restore body scrolling
      document.body.style.overflow = originalOverflow;
    };
  }, []);

  // 8. DYNAMIC MICROPHONE STREAM MANAGEMENT (OBS/YouTube compatible)
  useEffect(() => {
    if (visualizerMode === 'simulated') {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((tr) => tr.stop());
        streamRef.current = null;
      }
      if (audioCtxRef.current) {
        audioCtxRef.current.close().catch(() => {});
        audioCtxRef.current = null;
      }
      analyserRef.current = null;
      timeDomainRef.current = null;
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });
        if (cancelled) {
          stream.getTracks().forEach((tr) => tr.stop());
          return;
        }
        streamRef.current = stream;

        const AudioContext = window.AudioContext || window.webkitAudioContext;
        const audioCtx = new AudioContext();
        audioCtxRef.current = audioCtx;

        const source = audioCtx.createMediaStreamSource(stream);
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 1024;
        analyser.smoothingTimeConstant = 0.2;
        source.connect(analyser);

        analyserRef.current = analyser;
        timeDomainRef.current = new Uint8Array(analyser.fftSize);
      } catch (err) {
        console.warn('Microphone unavailable for visualizer, running in simulated mode.', err);
      }
    })();

    return () => {
      cancelled = true;
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((tr) => tr.stop());
        streamRef.current = null;
      }
      if (audioCtxRef.current) {
        audioCtxRef.current.close().catch(() => {});
        audioCtxRef.current = null;
      }
      analyserRef.current = null;
      timeDomainRef.current = null;
    };
  }, [visualizerMode]);

  const textColor = jarvisColor || blobColor.bright;
  
  const textStyles = jarvisTextPosition
    ? {
        position: 'fixed',
        left: `${jarvisTextPosition.x}px`,
        top: `${jarvisTextPosition.y}px`,
        transform: 'none',
        zIndex: 10000,
        transition: isTextDragging ? 'none' : 'left 0.1s ease-out, top 0.1s ease-out'
      }
    : {
        position: 'absolute',
        bottom: '-52px',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 1
      };

  const textElement = (
    <div
      onPointerDown={handleTextPointerDown}
      onPointerMove={handleTextPointerMove}
      onPointerUp={handleTextPointerUp}
      style={{
        ...textStyles,
        color: textColor,
        fontFamily: jarvisFont,
        fontSize: `${jarvisFontSize}px`,
        fontWeight: '800',
        letterSpacing: jarvisFontSize > 100 ? '10px' : '4px',
        textShadow: `0 0 10px ${textColor}, 0 0 20px ${textColor}55`,
        animation: 'jarvisTextPulse 3s infinite ease-in-out',
        cursor: isTextDraggable ? (isTextDragging ? 'grabbing' : 'grab') : 'pointer',
        touchAction: 'none',
        userSelect: 'none',
        whiteSpace: 'nowrap',
        outline: isTextDraggable ? '1.5px dashed rgba(0, 229, 255, 0.75)' : 'none',
        outlineOffset: '4px',
        padding: isTextDraggable ? '4px 10px' : '0',
        borderRadius: '8px',
        boxSizing: 'border-box'
      }}
    >
      {assistantName}
      {isTextDraggable && (
        <span style={{
          position: 'absolute',
          top: '-18px',
          left: '50%',
          transform: 'translateX(-50%)',
          background: 'rgba(20, 21, 26, 0.8)',
          border: '1px solid rgba(0, 229, 255, 0.4)',
          color: '#00e5ff',
          fontSize: '8px',
          fontWeight: '700',
          padding: '2px 6px',
          borderRadius: '8px',
          letterSpacing: '1px',
          pointerEvents: 'none'
        }}>
          DRAG TEXT
        </span>
      )}
    </div>
  );

  return (
    <>
      <div
        ref={mountRef}
        onPointerDown={handlePointerDownDrag}
        onPointerMove={handlePointerMoveDrag}
        onPointerUp={handlePointerUpDrag}
        style={{
          position: 'fixed',
          left: blobPosition ? `${blobPosition.x}px` : 'auto',
          top: blobPosition ? `${blobPosition.y}px` : 'auto',
          bottom: blobPosition ? 'auto' : '20px',
          right: blobPosition ? 'auto' : '20px',
          width: `${blobSize}px`,
          height: `${blobSize}px`,
          background: 'transparent',
          touchAction: 'none',
          cursor: isDraggable ? (isDragging ? 'grabbing' : 'grab') : 'pointer',
          zIndex: 9999,
          transition: isDragging ? 'none' : 'left 0.1s ease-out, top 0.1s ease-out',
          borderRadius: '50%',
          boxSizing: 'border-box',
          outline: isDraggable ? '2.5px dashed rgba(0, 229, 255, 0.75)' : 'none',
          outlineOffset: '6px',
          boxShadow: isDraggable ? '0 0 30px rgba(0, 229, 255, 0.2)' : 'none'
        }}
      >
        {/* Render attached text if position is relative */}
        {!jarvisTextPosition && textElement}

        {isDraggable && (
          <div style={{
            position: 'absolute',
            top: '-40px',
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'rgba(20, 21, 26, 0.8)',
            border: '1.5px solid rgba(0, 229, 255, 0.4)',
            color: '#00e5ff',
            fontSize: '10px',
            fontWeight: '700',
            padding: '4px 10px',
            borderRadius: '12px',
            whiteSpace: 'nowrap',
            pointerEvents: 'none',
            boxShadow: '0 4px 10px rgba(0, 0, 0, 0.2)'
          }}>
            DRAG ME
          </div>
        )}
      </div>

      {/* Render independent text if position is absolute */}
      {jarvisTextPosition && textElement}

      <style>{`
        @keyframes jarvisTextPulse {
          0%, 100% { opacity: 0.65; transform: ${jarvisTextPosition ? 'none' : 'translateX(-50%)'} scale(0.98); text-shadow: 0 0 8px ${textColor}; }
          50% { opacity: 1; transform: ${jarvisTextPosition ? 'none' : 'translateX(-50%)'} scale(1.02); text-shadow: 0 0 15px ${textColor}, 0 0 25px ${textColor}; }
        }
      `}</style>
    </>
  );
}
