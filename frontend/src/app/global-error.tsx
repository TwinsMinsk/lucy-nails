"use client";

// Root error boundary: catches errors in the root layout itself, so it must
// render its own <html>/<body> and cannot rely on the app's layout or CSS.
export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="ru">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#FDFBF9",
          fontFamily: "system-ui, -apple-system, Segoe UI, Arial, sans-serif",
          color: "#2D2D2D",
          padding: "1rem",
        }}
      >
        <div style={{ maxWidth: 480, textAlign: "center" }}>
          <h1 style={{ fontSize: "1.75rem", margin: "0 0 0.75rem" }}>
            Что-то пошло не так
          </h1>
          <p style={{ color: "#666666", margin: "0 0 1.5rem", lineHeight: 1.6 }}>
            Произошла непредвиденная ошибка. Попробуйте обновить страницу.
          </p>
          <button
            onClick={() => reset()}
            style={{
              background: "linear-gradient(to right, #db3f6e, #b02a52)",
              color: "#ffffff",
              border: "none",
              borderRadius: 9999,
              padding: "0.85rem 2rem",
              fontSize: "0.95rem",
              cursor: "pointer",
            }}
          >
            Обновить страницу
          </button>
        </div>
      </body>
    </html>
  );
}
