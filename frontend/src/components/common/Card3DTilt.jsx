import { useRef, useState, useCallback } from 'react';

/**
 * Card3DTilt - Lightweight interactive 3D perspective tilt container with dynamic specular glare.
 * Responds to mouse movements with smooth physical tilt and glassmorphic light reflection.
 */
export default function Card3DTilt({
  children,
  className = '',
  maxTilt = 10,
  scale = 1.02,
  glare = true,
  style = {},
  ...rest
}) {
  const cardRef = useRef(null);
  const [transformStyle, setTransformStyle] = useState({
    transform: 'perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)',
    transition: 'transform 0.4s cubic-bezier(0.2, 0.8, 0.2, 1)',
  });
  const [glareStyle, setGlareStyle] = useState({
    opacity: 0,
    background: 'radial-gradient(circle at 50% 50%, rgba(255,255,255,0.15) 0%, transparent 60%)',
  });

  const handleMouseMove = useCallback(
    (e) => {
      if (!cardRef.current) return;
      const rect = cardRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const normX = (x / rect.width) * 2 - 1; // -1 to 1
      const normY = (y / rect.height) * 2 - 1; // -1 to 1

      const rotateX = (-normY * maxTilt).toFixed(2);
      const rotateY = (normX * maxTilt).toFixed(2);

      setTransformStyle({
        transform: `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(${scale}, ${scale}, ${scale})`,
        transition: 'transform 0.1s ease-out',
      });

      if (glare) {
        const posX = ((x / rect.width) * 100).toFixed(1);
        const posY = ((y / rect.height) * 100).toFixed(1);
        setGlareStyle({
          opacity: 0.8,
          background: `radial-gradient(circle at ${posX}% ${posY}%, rgba(168, 85, 247, 0.25) 0%, rgba(6, 182, 212, 0.15) 30%, transparent 65%)`,
        });
      }
    },
    [maxTilt, scale, glare]
  );

  const handleMouseLeave = useCallback(() => {
    setTransformStyle({
      transform: 'perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)',
      transition: 'transform 0.5s cubic-bezier(0.25, 1, 0.5, 1)',
    });
    setGlareStyle((prev) => ({
      ...prev,
      opacity: 0,
      transition: 'opacity 0.4s ease-out',
    }));
  }, []);

  return (
    <div
      ref={cardRef}
      className={`card-3d-tilt-wrapper ${className}`}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        ...style,
        ...transformStyle,
        transformStyle: 'preserve-3d',
        willChange: 'transform',
        position: 'relative',
      }}
      {...rest}
    >
      {children}
      {glare && (
        <div
          className="card-3d-glare"
          style={{
            position: 'absolute',
            inset: 0,
            pointerEvents: 'none',
            borderRadius: 'inherit',
            mixBlendMode: 'screen',
            zIndex: 10,
            ...glareStyle,
          }}
          aria-hidden="true"
        />
      )}
    </div>
  );
}
