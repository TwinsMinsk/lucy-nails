"use client"

import { useEffect, useRef, useState } from "react";
import { AlertCircle, Loader2, Lock } from "lucide-react";
import { ApiError, getLessonPlayUrl, VideoPlayResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

interface VideoPlayerProps {
    lessonId: string;
    title: string;
    className?: string;
}

type LoadingState = "idle" | "loading" | "success" | "error";

export function VideoPlayer({ lessonId, title, className }: VideoPlayerProps) {
    const [state, setState] = useState<LoadingState>("idle");
    const [videoData, setVideoData] = useState<VideoPlayResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [denied, setDenied] = useState(false);
    const [retry, setRetry] = useState(0);
    const resumeRef = useRef<() => void>(() => {});

    useEffect(() => {
        let cancelled = false;
        let pending = false;
        let ready = false;
        let expiresAt = 0;
        const fetchVideoUrl = async () => {
            if (pending || cancelled) return;
            pending = true;
            ready = false;
            setState("loading");
            setVideoData(null);
            setError(null);
            setDenied(false);
            const startedAt = Date.now();
            try {
                const data = await getLessonPlayUrl(lessonId);
                if (cancelled) return;
                const ttl = data.expires_in_seconds || 300;
                expiresAt = startedAt + Math.max(1, ttl - 15) * 1000;
                setVideoData(data);
                setState("success");
                ready = true;
            } catch (err) {
                if (cancelled) return;
                setError(err instanceof Error ? err.message : "Не удалось загрузить видео");
                setDenied(err instanceof ApiError && [401, 403].includes(err.status));
                setState("error");
            } finally { pending = false; }
        };
        const resume = () => {
            if (ready && Date.now() >= expiresAt && document.visibilityState !== "hidden") void fetchVideoUrl();
        };
        resumeRef.current = resume;
        window.addEventListener("focus", resume);
        window.addEventListener("pageshow", resume);
        document.addEventListener("visibilitychange", resume);
        void fetchVideoUrl();
        return () => {
            cancelled = true;
            resumeRef.current = () => {};
            window.removeEventListener("focus", resume);
            window.removeEventListener("pageshow", resume);
            document.removeEventListener("visibilitychange", resume);
        };
    }, [lessonId, retry]);

    // Loading State
    if (state === "loading") {
        return (
            <div
                className={cn(
                    "w-full aspect-video bg-black flex items-center justify-center",
                    className
                )}
            >
                <div className="text-center space-y-4">
                    <Loader2 className="w-12 h-12 text-primary animate-spin mx-auto" />
                    <p className="text-white text-sm font-medium">Загрузка видео...</p>
                </div>
            </div>
        );
    }

    // Error State
    if (state === "error") {
        const is403 = denied || error?.includes("403") || error?.includes("access required");

        return (
            <div
                className={cn(
                    "w-full aspect-video bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center",
                    className
                )}
            >
                <div className="text-center space-y-4 max-w-md px-6">
                    {is403 ? (
                        <>
                            <div className="w-16 h-16 bg-amber-500/20 rounded-full flex items-center justify-center mx-auto">
                                <Lock className="w-8 h-8 text-amber-500" />
                            </div>
                            <div className="space-y-2">
                                <h3 className="text-xl font-semibold text-white">
                                    Доступ ограничен
                                </h3>
                                <p className="text-slate-300 text-sm leading-relaxed">
                                    Для просмотра этого урока необходимо приобрести курс.
                                    Вернитесь на страницу курса, чтобы оформить доступ.
                                </p>
                            </div>
                        </>
                    ) : (
                        <>
                            <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto">
                                <AlertCircle className="w-8 h-8 text-red-500" />
                            </div>
                            <div className="space-y-2">
                                <h3 className="text-xl font-semibold text-white">
                                    Ошибка загрузки
                                </h3>
                                <p className="text-slate-300 text-sm leading-relaxed">
                                    {error || "Произошла неизвестная ошибка при загрузке видео"}
                                </p>
                                <button className="rounded-md border px-4 py-2 text-white" onClick={() => setRetry((value) => value + 1)}>Повторить</button>
                            </div>
                        </>
                    )}
                </div>
            </div>
        );
    }

    // Success State - Render iframe
    if (state === "success" && videoData) {
        return (
            <div className={cn("w-full aspect-video bg-black", className)} onPointerEnter={() => resumeRef.current()} onTouchStart={() => resumeRef.current()}>
                <iframe
                    onFocus={() => resumeRef.current()}
                    src={videoData.video_url}
                    title={videoData.title || title}
                    className="w-full h-full border-0"
                    allow="autoplay; fullscreen; picture-in-picture; encrypted-media"
                    allowFullScreen
                />
            </div>
        );
    }

    // Fallback
    return (
        <div
            className={cn(
                "w-full aspect-video bg-black flex items-center justify-center",
                className
            )}
        >
            <p className="text-white text-sm">Инициализация...</p>
        </div>
    );
}
