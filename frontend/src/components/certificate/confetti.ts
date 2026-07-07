const CERTIFICATE_COLORS = ["#db3f6e", "#b02a52", "#D4AF37", "#FFF3AD", "#fff1f4"];

/**
 * Fires a short celebratory confetti burst over a dedicated fixed canvas.
 *
 * CSP NOTE (do not deviate): next.config.ts script-src has no `blob:`, so the
 * canvas-confetti default worker path would violate CSP. useWorker MUST be false.
 */
export async function fireConfetti(): Promise<void> {
    if (typeof window === "undefined") return;

    const confetti = (await import("canvas-confetti")).default;

    const canvas = document.createElement("canvas");
    canvas.style.position = "fixed";
    canvas.style.inset = "0";
    canvas.style.pointerEvents = "none";
    canvas.style.zIndex = "100"; // must overlay the Radix dialog overlay at z-50
    document.body.appendChild(canvas);

    const instance = confetti.create(canvas, {
        resize: true,
        useWorker: false,
        disableForReducedMotion: true,
    });

    // Two side bursts angled inward
    instance({
        particleCount: 80,
        angle: 60,
        spread: 70,
        startVelocity: 55,
        origin: { x: 0.15, y: 0.9 },
        colors: CERTIFICATE_COLORS,
    });
    instance({
        particleCount: 80,
        angle: 120,
        spread: 70,
        startVelocity: 55,
        origin: { x: 0.85, y: 0.9 },
        colors: CERTIFICATE_COLORS,
    });

    // Center burst
    setTimeout(() => {
        instance({
            particleCount: 90,
            spread: 100,
            origin: { x: 0.5, y: 0.7 },
            colors: CERTIFICATE_COLORS,
        });
    }, 500);

    // Final small sprinkle
    setTimeout(() => {
        instance({
            particleCount: 30,
            spread: 60,
            startVelocity: 30,
            origin: { x: 0.5, y: 0.8 },
            colors: CERTIFICATE_COLORS,
        });
    }, 1500);

    // Always remove this exact canvas node — no shared module-level state to leak across calls
    setTimeout(() => {
        canvas.remove();
    }, 4000);
}
