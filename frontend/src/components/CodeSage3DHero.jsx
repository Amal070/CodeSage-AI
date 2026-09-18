import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import heroImg from '../assets/hero.png';

/**
 * CodeSage3DHero - Professional lightweight 3D interactive hero centerpiece.
 * Combines a WebGL Three.js rotating holographic emblem, orbital cyber rings,
 * neural wireframe matrix, and floating 3D developer tokens.
 */
export default function CodeSage3DHero() {
  const mountRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    const container = mountRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    let animationFrameId;
    let isVisible = true;

    // Dimensions
    const width = container.clientWidth || 480;
    const height = container.clientHeight || 480;

    // Scene, Camera, Renderer
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
    camera.position.set(0, 0, 8.5);

    const renderer = new THREE.WebGLRenderer({
      canvas,
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Master group for smooth mouse parallax
    const masterGroup = new THREE.Group();
    scene.add(masterGroup);

    // 1. Central CodeSage Logo Disc
    const textureLoader = new THREE.TextureLoader();
    const logoTexture = textureLoader.load(heroImg);
    logoTexture.colorSpace = THREE.SRGBColorSpace;
    logoTexture.generateMipmaps = true;
    logoTexture.minFilter = THREE.LinearMipmapLinearFilter;

    // Circular emblem geometry for perfect aspect ratio & crisp rendering
    const emblemGeo = new THREE.CircleGeometry(1.65, 64);
    const emblemMat = new THREE.MeshBasicMaterial({
      map: logoTexture,
      transparent: true,
      side: THREE.DoubleSide,
    });
    const emblemMesh = new THREE.Mesh(emblemGeo, emblemMat);
    masterGroup.add(emblemMesh);

    // Subtle dark backing disc to prevent reverse see-through
    const backingGeo = new THREE.CircleGeometry(1.66, 64);
    const backingMat = new THREE.MeshBasicMaterial({
      color: 0x070b14,
      side: THREE.BackSide,
    });
    const backingMesh = new THREE.Mesh(backingGeo, backingMat);
    backingMesh.position.z = -0.01;
    masterGroup.add(backingMesh);

    // 2. Glowing Inner Cyan Halo Ring
    const innerHaloGeo = new THREE.RingGeometry(1.64, 1.78, 64);
    const innerHaloMat = new THREE.MeshBasicMaterial({
      color: 0x06b6d4,
      transparent: true,
      opacity: 0.7,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending,
    });
    const innerHalo = new THREE.Mesh(innerHaloGeo, innerHaloMat);
    innerHalo.position.z = 0.02;
    masterGroup.add(innerHalo);

    // 3. Gyroscopic Cyber Ring 1 (Cyan)
    const ring1Geo = new THREE.TorusGeometry(2.35, 0.022, 16, 120);
    const ring1Mat = new THREE.MeshBasicMaterial({
      color: 0x06b6d4,
      transparent: true,
      opacity: 0.6,
      blending: THREE.AdditiveBlending,
    });
    const ring1 = new THREE.Mesh(ring1Geo, ring1Mat);
    ring1.rotation.x = Math.PI / 3;
    masterGroup.add(ring1);

    // 4. Gyroscopic Cyber Ring 2 (Purple)
    const ring2Geo = new THREE.TorusGeometry(2.7, 0.02, 16, 120);
    const ring2Mat = new THREE.MeshBasicMaterial({
      color: 0xa855f7,
      transparent: true,
      opacity: 0.65,
      blending: THREE.AdditiveBlending,
    });
    const ring2 = new THREE.Mesh(ring2Geo, ring2Mat);
    ring2.rotation.y = Math.PI / 4;
    ring2.rotation.x = -Math.PI / 5;
    masterGroup.add(ring2);

    // 5. Neural Geodesic Wireframe Sphere (AI Code Intelligence Lattice)
    const neuralGeo = new THREE.IcosahedronGeometry(2.1, 2);
    const neuralMat = new THREE.MeshBasicMaterial({
      color: 0x818cf8,
      wireframe: true,
      transparent: true,
      opacity: 0.18,
      blending: THREE.AdditiveBlending,
    });
    const neuralMesh = new THREE.Mesh(neuralGeo, neuralMat);
    masterGroup.add(neuralMesh);

    // 6. Orbiting Data Node Points (Particle Cloud)
    const particleCount = 90;
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);

    const c1 = new THREE.Color(0x06b6d4); // Cyan
    const c2 = new THREE.Color(0xa855f7); // Purple
    const c3 = new THREE.Color(0x10b981); // Emerald

    for (let i = 0; i < particleCount; i++) {
      // Golden spiral distribution on a sphere
      const phi = Math.acos(-1 + (2 * i) / particleCount);
      const theta = Math.sqrt(particleCount * Math.PI) * phi;
      const radius = 2.1 + (Math.random() - 0.5) * 1.8;

      positions[i * 3] = radius * Math.cos(theta) * Math.sin(phi);
      positions[i * 3 + 1] = radius * Math.sin(theta) * Math.sin(phi);
      positions[i * 3 + 2] = radius * Math.cos(phi);

      const pickColor = i % 3 === 0 ? c1 : i % 3 === 1 ? c2 : c3;
      colors[i * 3] = pickColor.r;
      colors[i * 3 + 1] = pickColor.g;
      colors[i * 3 + 2] = pickColor.b;
    }

    const particleGeo = new THREE.BufferGeometry();
    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    particleGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const particleMat = new THREE.PointsMaterial({
      size: 0.08,
      vertexColors: true,
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending,
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    masterGroup.add(particles);

    // 7. Emissive Orbiting Satellite Beads
    const satellites = [];
    const satelliteConfigs = [
      { color: 0x06b6d4, radius: 2.35, speed: 1.2, offset: 0, tilt: Math.PI / 3 },
      { color: 0xc084fc, radius: 2.7, speed: -0.9, offset: Math.PI / 2, tilt: -Math.PI / 5 },
      { color: 0x34d399, radius: 2.05, speed: 1.6, offset: Math.PI, tilt: Math.PI / 6 },
    ];

    satelliteConfigs.forEach((cfg) => {
      const beadGeo = new THREE.SphereGeometry(0.065, 16, 16);
      const beadMat = new THREE.MeshBasicMaterial({
        color: cfg.color,
        blending: THREE.AdditiveBlending,
      });
      const beadMesh = new THREE.Mesh(beadGeo, beadMat);
      masterGroup.add(beadMesh);
      satellites.push({ mesh: beadMesh, ...cfg });
    });

    // Interaction state: smooth mouse tracking
    let targetRotY = 0;
    let targetRotX = 0;
    let currentRotY = 0;
    let currentRotX = 0;

    const handleMouseMove = (e) => {
      const rect = container.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      targetRotY = x * 0.7; // Max tilt Y
      targetRotX = -y * 0.5; // Max tilt X
    };

    const handleMouseLeave = () => {
      targetRotY = 0;
      targetRotX = 0;
    };

    window.addEventListener('mousemove', handleMouseMove);
    container.addEventListener('mouseleave', handleMouseLeave);

    // Resize observer
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width: w, height: h } = entry.contentRect;
        if (w > 0 && h > 0) {
          camera.aspect = w / h;
          camera.updateProjectionMatrix();
          renderer.setSize(w, h);
        }
      }
    });
    resizeObserver.observe(container);

    // Intersection observer to pause rendering when out of viewport
    const intersectionObserver = new IntersectionObserver(([entry]) => {
      isVisible = entry.isIntersecting;
    });
    intersectionObserver.observe(container);

    // Page visibility change
    const handleVisibilityChange = () => {
      isVisible = !document.hidden;
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Clock
    const clock = new THREE.Clock();

    // Render loop
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      if (!isVisible) return;

      const elapsedTime = clock.getElapsedTime();

      // Smooth camera / group rotation via lerp
      currentRotY += (targetRotY - currentRotY) * 0.06;
      currentRotX += (targetRotX - currentRotX) * 0.06;

      masterGroup.rotation.y = currentRotY + Math.sin(elapsedTime * 0.4) * 0.08;
      masterGroup.rotation.x = currentRotX + Math.cos(elapsedTime * 0.3) * 0.05;

      // Gentle vertical levitation float
      masterGroup.position.y = Math.sin(elapsedTime * 1.6) * 0.12;

      // Rotate cyber rings on distinct 3D axes
      ring1.rotation.z = elapsedTime * 0.25;
      ring1.rotation.y = elapsedTime * 0.15;

      ring2.rotation.z = -elapsedTime * 0.2;
      ring2.rotation.x = -Math.PI / 5 + Math.sin(elapsedTime * 0.3) * 0.1;

      // Rotate neural lattice & particle cloud slowly
      neuralMesh.rotation.y = elapsedTime * 0.12;
      neuralMesh.rotation.x = elapsedTime * 0.08;
      particles.rotation.y = -elapsedTime * 0.06;

      // Inner halo breathing pulse
      const haloScale = 1 + Math.sin(elapsedTime * 2.5) * 0.03;
      innerHalo.scale.set(haloScale, haloScale, 1);
      innerHaloMat.opacity = 0.6 + Math.sin(elapsedTime * 3) * 0.2;

      // Animate orbiting satellites along tilted orbits
      satellites.forEach((sat) => {
        const angle = elapsedTime * sat.speed + sat.offset;
        const x = sat.radius * Math.cos(angle);
        const y = sat.radius * Math.sin(angle) * Math.cos(sat.tilt);
        const z = sat.radius * Math.sin(angle) * Math.sin(sat.tilt);
        sat.mesh.position.set(x, y, z);
      });

      renderer.render(scene, camera);
    };

    animate();

    // Cleanup
    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('mousemove', handleMouseMove);
      container.removeEventListener('mouseleave', handleMouseLeave);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      resizeObserver.disconnect();
      intersectionObserver.disconnect();

      // Dispose Three.js objects
      [
        emblemGeo,
        emblemMat,
        backingGeo,
        backingMat,
        innerHaloGeo,
        innerHaloMat,
        ring1Geo,
        ring1Mat,
        ring2Geo,
        ring2Mat,
        neuralGeo,
        neuralMat,
        particleGeo,
        particleMat,
      ].forEach((obj) => obj?.dispose?.());

      satellites.forEach((s) => {
        s.mesh.geometry?.dispose?.();
        s.mesh.material?.dispose?.();
      });

      logoTexture?.dispose?.();
      renderer?.dispose?.();
    };
  }, []);

  return (
    <div className="hero-3d-container" ref={mountRef}>
      {/* 3D WebGL Canvas */}
      <canvas ref={canvasRef} className="hero-3d-canvas" />

      {/* Floating 3D Micro-Badges orbiting in perspective depth */}
      <div className="hero-3d-badge-cluster" aria-hidden="true">
        <div className="hero-3d-floating-chip chip-ast">
          <span className="chip-indicator"></span>
          <span className="chip-text">Code Understanding</span>
        </div>

        <div className="hero-3d-floating-chip chip-jwt">
          <span className="chip-indicator cyan"></span>
          <span className="chip-text">AI Powered</span>
        </div>

        <div className="hero-3d-floating-chip chip-sql">
          <span className="chip-indicator emerald"></span>
          <span className="chip-text">Smart Search</span>
        </div>

        <div className="hero-3d-floating-chip chip-latency">
          <span className="chip-indicator glow"></span>
          <span className="chip-text">Instant Insights</span>
        </div>
      </div>

      {/* Background ambient radial glow matching the official brand colors */}
      <div className="hero-3d-glow-backdrop"></div>
    </div>
  );
}
