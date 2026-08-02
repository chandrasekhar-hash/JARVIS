import React, { useEffect, useRef } from 'react';

/**
 * JarvisParticleCanvas Component
 * Renders an autonomous particle field of dots without network lines.
 * High density particle field (1400 dots) with clean central safe zone.
 * Adds interactive cursor proximity: nearby dots move faster and exhibit an energetic up-and-down wave motion.
 */
export default function JarvisParticleCanvas({ isActivating = false }) {
  const canvasRef = useRef(null);
  const animFrameIdRef = useRef(null);
  const pulseRadiusRef = useRef(0);
  const mouseRef = useRef({ x: -9999, y: -9999, active: false });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    let width = 0;
    let height = 0;
    let dpr = 1;
    let particles = [];

    // JARVIS Color Palette
    const COLOR_PALETTE = [
      'rgba(0, 255, 225, ',   // Vibrant Cyan
      'rgba(0, 160, 180, ',   // Soft Teal
      'rgba(0, 90, 220, ',    // Deep Electric Blue
      'rgba(0, 240, 255, '    // Bright Aqua
    ];

    const isInsideSafeZone = (x, y, w, h) => {
      const cX = w / 2;
      const cY = h / 2;
      const safeW = Math.min(w * 0.50, 520);
      const safeH = Math.min(h * 0.40, 340);
      return Math.abs(x - cX) < safeW / 2 && Math.abs(y - cY) < safeH / 2;
    };

    const handleMouseMove = (e) => {
      mouseRef.current = {
        x: e.clientX,
        y: e.clientY,
        active: true
      };
    };

    const handleMouseLeave = () => {
      mouseRef.current.active = false;
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseleave', handleMouseLeave);

    const initCanvasSize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = window.innerWidth;
      height = window.innerHeight;

      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      ctx.scale(dpr, dpr);
      createParticles();
    };

    const createParticles = () => {
      particles = [];

      // High density: 1200 dots on desktop, 650 on tablet, 350 on mobile
      const totalParticles = width < 768 ? 350 : (width < 1024 ? 650 : 1200);

      for (let i = 0; i < totalParticles; i++) {
        let px, py;
        let attempts = 0;

        do {
          px = Math.random() * width;
          py = Math.random() * height;
          attempts++;
        } while (isInsideSafeZone(px, py, width, height) && attempts < 60);

        // Fallback positioning outside safe radius
        if (isInsideSafeZone(px, py, width, height)) {
          const angle = Math.random() * Math.PI * 2;
          const safeRadius = Math.max(width * 0.28, 280);
          px = width / 2 + Math.cos(angle) * (safeRadius + Math.random() * 140);
          py = height / 2 + Math.sin(angle) * (safeRadius + Math.random() * 140);
        }

        const isGlowNode = Math.random() < 0.06;
        const isMediumNode = !isGlowNode && Math.random() < 0.18;

        let size = Math.random() * 1.0 + 0.8; // 0.8 - 1.8px small dots
        if (isGlowNode) size = Math.random() * 1.0 + 2.8; // 2.8 - 3.8px glowing nodes
        else if (isMediumNode) size = Math.random() * 0.7 + 1.9; // 1.9 - 2.6px medium dots

        const baseAlpha = isGlowNode
          ? (Math.random() * 0.25 + 0.55)
          : (isMediumNode ? (Math.random() * 0.25 + 0.38) : (Math.random() * 0.25 + 0.22));

        const colorBase = COLOR_PALETTE[Math.floor(Math.random() * COLOR_PALETTE.length)];

        particles.push({
          id: i,
          originX: px,
          originY: py,
          dispX: 0,
          dispY: 0,
          size,
          isGlowNode,
          colorBase,
          baseAlpha,
          pulseSpeed: Math.random() * 0.005 + 0.002,
          pulseOffset: Math.random() * Math.PI * 2,
          floatPhaseX: Math.random() * Math.PI * 2,
          floatPhaseY: Math.random() * Math.PI * 2
        });
      }
    };

    window.addEventListener('resize', initCanvasSize);
    initCanvasSize();

    let time = 0;

    const render = () => {
      time += 1;
      ctx.clearRect(0, 0, width, height);

      const centerX = width / 2;
      const centerY = height / 2;
      const safeHalfW = Math.min(width * 0.50, 520) / 2;
      const safeHalfH = Math.min(height * 0.40, 340) / 2;
      const mouse = mouseRef.current;

      // 1. INITIALIZE Click Radial Pulse
      if (isActivating) {
        pulseRadiusRef.current += 14;
        const radius = pulseRadiusRef.current;
        const maxRadius = Math.max(width, height) * 0.85;
        const pulseAlpha = Math.max(0, 0.38 * (1 - radius / maxRadius));

        if (pulseAlpha > 0) {
          const grad = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, radius);
          grad.addColorStop(0, `rgba(0, 255, 225, ${pulseAlpha})`);
          grad.addColorStop(0.4, `rgba(0, 80, 200, ${pulseAlpha * 0.55})`);
          grad.addColorStop(1, 'rgba(0, 0, 0, 0)');

          ctx.fillStyle = grad;
          ctx.beginPath();
          ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
          ctx.fill();
        }
      } else {
        pulseRadiusRef.current = 0;
      }

      // 2. Motion & Rendering of Dots with Smooth Spring Return & Controlled Up/Down Wave
      const influenceRadius = 150;

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        // Ambient fluid floating motion around home anchor
        const ambientFloatX = Math.sin(time * 0.010 + p.floatPhaseX) * 7;
        const ambientFloatY = Math.cos(time * 0.008 + p.floatPhaseY) * 7;

        let targetDispX = 0;
        let targetDispY = 0;

        if (!reducedMotion && mouse.active) {
          const currentX = p.originX + ambientFloatX + p.dispX;
          const currentY = p.originY + ambientFloatY + p.dispY;

          const dxM = currentX - mouse.x;
          const dyM = currentY - mouse.y;
          const distM = Math.hypot(dxM, dyM);

          if (distM < influenceRadius && distM > 0.1) {
            const factor = (1 - distM / influenceRadius);
            const pushDist = factor * 18; // Max 18px smooth displacement

            targetDispX = (dxM / distM) * pushDist;
            // Fluid up/down wave reaction on hover
            const upDownWave = Math.sin(time * 0.09 + p.id * 0.4) * factor * 11;
            targetDispY = (dyM / distM) * pushDist + upDownWave;
          }
        }

        // Smooth spring interpolation back to original home position (0.05 ease)
        p.dispX += (targetDispX - p.dispX) * 0.05;
        p.dispY += (targetDispY - p.dispY) * 0.05;

        let drawX = p.originX + ambientFloatX + p.dispX;
        let drawY = p.originY + ambientFloatY + p.dispY;

        // Keep dots strictly outside the central safe area
        const dxCenter = drawX - centerX;
        const dyCenter = drawY - centerY;

        if (Math.abs(dxCenter) < safeHalfW && Math.abs(dyCenter) < safeHalfH) {
          if (Math.abs(dxCenter) / safeHalfW > Math.abs(dyCenter) / safeHalfH) {
            drawX = centerX + Math.sign(dxCenter) * (safeHalfW + 5);
          } else {
            drawY = centerY + Math.sign(dyCenter) * (safeHalfH + 5);
          }
        }

        // Sinusoidal opacity pulse
        const currentAlpha = Math.max(
          0.08,
          Math.min(0.92, p.baseAlpha + Math.sin(time * p.pulseSpeed + p.pulseOffset) * 0.12)
        );

        if (p.isGlowNode) {
          const haloRadius = p.size * 2.8;
          const haloGrad = ctx.createRadialGradient(drawX, drawY, 0, drawX, drawY, haloRadius);
          haloGrad.addColorStop(0, `rgba(0, 255, 225, ${(currentAlpha * 0.65).toFixed(3)})`);
          haloGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');

          ctx.fillStyle = haloGrad;
          ctx.beginPath();
          ctx.arc(drawX, drawY, haloRadius, 0, Math.PI * 2);
          ctx.fill();

          ctx.fillStyle = `${p.colorBase}${currentAlpha.toFixed(3)})`;
          ctx.beginPath();
          ctx.arc(drawX, drawY, p.size * 0.6, 0, Math.PI * 2);
          ctx.fill();
        } else {
          ctx.fillStyle = `${p.colorBase}${currentAlpha.toFixed(3)})`;
          ctx.beginPath();
          ctx.arc(drawX, drawY, p.size, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      animFrameIdRef.current = requestAnimationFrame(render);
    };

    animFrameIdRef.current = requestAnimationFrame(render);

    return () => {
      if (animFrameIdRef.current) {
        cancelAnimationFrame(animFrameIdRef.current);
      }
      window.removeEventListener('resize', initCanvasSize);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [isActivating]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 1
      }}
    />
  );
}
