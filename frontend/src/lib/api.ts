/**
 * API Client для взаимодействия с Backend
 */
import { getPublicApiUrl } from "@/lib/env";

const getBaseUrl = () => {
    return getPublicApiUrl();
};

const API_BASE_URL = getBaseUrl();
if (process.env.NODE_ENV === "development") {
    console.log(`🚀 API Base URL initialized as: ${API_BASE_URL}`);
}

/**
 * Получить токен из localStorage
 */
const getAuthToken = (): string | null => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token");
};

const getRefreshToken = (): string | null => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("refresh_token");
};

const setSessionCookie = () => {
    if (typeof document === "undefined") return;
    const secure = window.location.protocol === "https:" ? "; Secure" : "";
    document.cookie = `auth_session=1; Path=/; Max-Age=604800; SameSite=Lax${secure}`;
};

const clearSessionCookie = () => {
    if (typeof document === "undefined") return;
    document.cookie = "auth_session=; Path=/; Max-Age=0; SameSite=Lax";
};

const getCookie = (name: string): string | null => {
    if (typeof document === "undefined") return null;
    const prefix = `${name}=`;
    const cookie = document.cookie
        .split("; ")
        .find((item) => item.startsWith(prefix));
    return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null;
};

const isUnsafeMethod = (method: string | undefined): boolean => {
    const normalized = (method || "GET").toUpperCase();
    return !["GET", "HEAD", "OPTIONS", "TRACE"].includes(normalized);
};

const saveTokens = (tokens: TokenResponse) => {
    if (typeof window === "undefined") return;
    void tokens;
    // Tokens are set as httpOnly cookies by the backend. Remove legacy localStorage copies.
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setSessionCookie();
};

const clearTokens = () => {
    if (typeof window === "undefined") return;
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    clearSessionCookie();
};

const parseErrorDetail = (detail: unknown, fallback: string): string => {
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((item) => item?.msg ?? String(item)).join("; ");
    if (detail && typeof detail === "object") return JSON.stringify(detail);
    return fallback;
};

export const isAuthError = (error: unknown): boolean => (
    error instanceof Error && error.message === "Требуется вход в аккаунт"
);

async function refreshAccessToken(): Promise<string | null> {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(getRefreshToken() ? { refresh_token: getRefreshToken() } : {}),
    });

    if (!response.ok) {
        clearTokens();
        return null;
    }

    const tokens = await response.json() as TokenResponse;
    saveTokens(tokens);
    return tokens.access_token;
}

/**
 * Базовый fetch с авторизацией
 */
/**
 * Базовый fetch с авторизацией (экспортируется для прямого использования)
 */
export async function apiFetch<T>(endpoint: string, options?: RequestInit, retryOnUnauthorized = true): Promise<T> {
    const token = getAuthToken();

    const headers: Record<string, string> = {
        "Content-Type": "application/json",
        ...(token && { Authorization: `Bearer ${token}` }),
        ...(options?.headers as Record<string, string> | undefined),
    };
    const csrfToken = getCookie("csrf_token");
    if (csrfToken && isUnsafeMethod(options?.method)) {
        headers["X-CSRF-Token"] = csrfToken;
    }

    const fullUrl = `${API_BASE_URL}${endpoint}`;
    if (process.env.NODE_ENV === "development") {
        console.log(`🌐 Fetching: ${fullUrl}`);
    }

    const response = await fetch(fullUrl, {
        ...options,
        headers,
        credentials: "include",
    });

    if (!response.ok) {
        const isAuthEndpoint = endpoint.startsWith("/auth/login")
            || endpoint.startsWith("/auth/register")
            || endpoint.startsWith("/auth/refresh");

        if (response.status === 401 && retryOnUnauthorized && !isAuthEndpoint) {
            const newAccessToken = await refreshAccessToken();
            if (newAccessToken) {
                return apiFetch<T>(endpoint, options, false);
            }
            throw new Error("Требуется вход в аккаунт");
        }

        const errorData = await response.json().catch(() => ({ detail: `HTTP error ${response.status} at ${fullUrl}` }));
        console.error(`❌ API Error [${response.status}] ${fullUrl}:`, errorData);
        throw new Error(parseErrorDetail(errorData.detail, `HTTP ${response.status}`));
    }

    return response.json();
}

/**
 * Upload file with authorization
 */
export interface UploadResponse {
    url: string;
    filename: string;
}

async function uploadFile(file: File): Promise<UploadResponse> {
    const token = getAuthToken();

    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/admin/upload`, {
        method: 'POST',
        credentials: "include",
        headers: {
            ...(token && { Authorization: `Bearer ${token}` }),
            ...(getCookie("csrf_token") && { "X-CSRF-Token": getCookie("csrf_token") as string }),
        },
        body: formData,
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
    }

    return response.json();
}

/**
 * Типы ответов API
 */
export interface VideoPlayResponse {
    video_url: string;
    provider: string;
    title: string;
}

export interface LessonResponse {
    id: string;
    module_id: string;
    title: string;
    description?: string;
    content?: string;
    duration_seconds: number;
    order_index: number;
    is_preview: boolean;
    kinescope_video_id?: string;
}

export interface UserResponse {
    id: string;
    email: string;
    phone?: string | null;
    role: "student" | "admin";
    telegram_id?: number;
    created_at: string;
}

export interface TokenResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
}

export interface LoginCredentials {
    email: string;
    password: string;
}

export interface RegisterCredentials {
    email: string;
    password: string;
}

/**
 * ============================================
 * AUTH METHODS
 * ============================================
 */

/**
 * Вход в систему
 */
export const login = async (credentials: LoginCredentials): Promise<TokenResponse> => {
    const response = await apiFetch<TokenResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify(credentials),
    });

    saveTokens(response);

    return response;
};

/**
 * Регистрация нового пользователя
 */
export const register = async (credentials: RegisterCredentials): Promise<UserResponse> => {
    return apiFetch<UserResponse>("/auth/register", {
        method: "POST",
        body: JSON.stringify(credentials),
    });
};

/**
 * Получить профиль текущего пользователя
 */
export const getMe = async (): Promise<UserResponse> => {
    return apiFetch<UserResponse>("/auth/me");
};

/**
 * Выход из системы
 */
export const logout = async (): Promise<void> => {
    try {
        await apiFetch("/auth/logout", { method: "POST" });
    } finally {
        // Удаляем токены из localStorage в любом случае
        clearTokens();
    }
};

/**
 * ============================================
 * LESSONS METHODS
 * ============================================
 */

/**
 * Получить URL для воспроизведения урока
 */
export const getLessonPlayUrl = async (lessonId: string): Promise<VideoPlayResponse> => {
    return apiFetch<VideoPlayResponse>(`/lessons/${lessonId}/play`);
};

/**
 * Получить данные урока
 */
export const getLesson = async (lessonId: string): Promise<LessonResponse> => {
    return apiFetch<LessonResponse>(`/lessons/${lessonId}`);
};

/**
 * ============================================
 * COURSES METHODS
 * ============================================
 */

export interface CourseResponse {
    id: string;
    title: string;
    description: string;
    price_self: number;
    price_support: number;
    cover_image_url?: string | null;
    is_published: boolean;
    duration_seconds?: number;
    created_at?: string;
}

export interface CourseListResponse {
    courses: CourseResponse[];
    total: number;
}

/**
 * Публичный каталог курсов (без авторизации). Для SSR на лендинге.
 */
export async function getPublishedCourses(): Promise<CourseListResponse> {
    const base = getBaseUrl();
    const res = await fetch(`${base}/courses`, { next: { revalidate: 120 } });
    if (!res.ok) {
        throw new Error(`Failed to load courses: ${res.status}`);
    }
    return res.json();
}

export interface MyCourseResponse {
    id: string;
    title: string;
    description?: string;
    progress: number;
    total_lessons: number;
    completed_lessons: number;
    last_lesson_id?: string;
    last_lesson_title?: string;
    cover_image_url?: string;
    tariff?: string | null;
    expires_at?: string | null;
    support_chat_url?: string | null;
}

/**
 * Получить курсы текущего пользователя
 */
export const getMyCourses = async (): Promise<MyCourseResponse[]> => {
    return apiFetch<MyCourseResponse[]>("/purchases/my");
};

/**
 * Получить публичную информацию о курсе
 */
export const getPublicCourse = async (courseId: string): Promise<CourseResponse> => {
    return apiFetch<CourseResponse>(`/courses/${courseId}`);
};

/**
 * Получить публичные модули курса (с уроками)
 */
export const getPublicCourseModules = async (courseId: string): Promise<ModuleResponse[]> => {
    return apiFetch<ModuleResponse[]>(`/courses/${courseId}/modules`);
};

/**
 * Получить прогресс (список завершенных уроков) для курса
 */
export const getCourseProgress = async (courseId: string): Promise<{ completed_lesson_ids: string[]; progress_percent: number }> => {
    return apiFetch<{ completed_lesson_ids: string[]; progress_percent: number }>(`/courses/${courseId}/my-progress`);
};

/**
 * Обновить прогресс урока (например, пометить как завершенный)
 */
export const updateLessonProgress = async (lessonId: string, data: { is_completed: boolean; watched_seconds?: number }): Promise<any> => {
    return apiFetch(`/lessons/${lessonId}/progress`, {
        method: "POST",
        body: JSON.stringify(data),
    });
};


/**
 * ============================================
 * ADMIN METHODS
 * ============================================
 */

export interface AdminCourseResponse {
    id: string;
    title: string;
    description: string;
    price_self: number;
    price_support: number;
    is_published: boolean;
}

export interface GrantAccessRequest {
    user_id: string;
    course_id: string;
    tariff?: "self" | "support";
}

export interface GrantAccessResponse {
    message: string;
    purchase_id: string;
    expires_at: string;
}

/**
 * Получить всех пользователей (только для админов)
 */
export const getUsers = async (): Promise<UserResponse[]> => {
    return apiFetch<UserResponse[]>("/admin/users");
};

/**
 * Получить все курсы (только для админов)
 */
export const getAllCourses = async (): Promise<AdminCourseResponse[]> => {
    return apiFetch<AdminCourseResponse[]>("/admin/courses");
};

/**
 * Выдать доступ к курсу пользователю (только для админов)
 */
export const adminGrantAccess = async (
    userId: string,
    courseId: string,
    tariff: "self" | "support" = "self"
): Promise<GrantAccessResponse> => {
    return apiFetch<GrantAccessResponse>("/admin/grant-access", {
        method: "POST",
        body: JSON.stringify({
            user_id: userId,
            course_id: courseId,
            tariff,
        }),
    });
};


/**
 * ============================================
 * ADMIN CRUD METHODS
 * ============================================
 */

// --- Extended Types ---

export interface AdminCourseFullResponse {
    id: string;
    title: string;
    description: string;
    cover_image_url?: string;
    price_self: number;
    price_support: number;
    is_published: boolean;
    created_at: string;
    modules_count: number;
    lessons_count: number;
}

export interface ModuleResponse {
    id: string;
    course_id: string;
    title: string;
    description?: string;
    order_index: number;
    is_published: boolean;
    created_at: string;
    lessons_count: number;
    lessons: LessonBriefResponse[];
}

export interface LessonBriefResponse {
    id: string;
    title: string;
    order_index: number;
    duration_seconds: number;
    kinescope_video_id?: string;
    is_preview: boolean;
    promo_kinescope_video_id?: string | null;
    promo_poster_url?: string | null;
    promo_description?: string | null;
    promo_bullets?: string[];
}

export interface AdminLessonResponse {
    id: string;
    module_id: string;
    title: string;
    description?: string;
    content?: string;
    kinescope_video_id?: string;
    duration_seconds: number;
    order_index: number;
    is_preview: boolean;
    created_at: string;
}

export interface AnalyticsResponse {
    total_users: number;
    total_courses: number;
    total_purchases: number;
    total_revenue: number;
    recent_purchases: number;
    recent_registrations: number;
}

export interface AdminPurchaseResponse {
    id: string;
    payment_id?: string | null;
    user_email: string;
    course_title: string;
    tariff: "self" | "support";
    amount_kopecks: number;
    payment_status: "pending" | "success" | "failed";
    expires_at: string;
    paid_at?: string | null;
    created_at: string;
    customer_phone?: string | null;
}

// --- Course CRUD ---

export interface CourseCreateRequest {
    title: string;
    description?: string;
    cover_image_url?: string;
    price_self?: number;
    price_support?: number;
    is_published?: boolean;
}

export interface CourseUpdateRequest {
    title?: string;
    description?: string;
    cover_image_url?: string;
    price_self?: number;
    price_support?: number;
    is_published?: boolean;
}

export const adminGetCourses = async (): Promise<AdminCourseFullResponse[]> => {
    return apiFetch<AdminCourseFullResponse[]>("/admin/courses");
};

export const adminGetCourse = async (courseId: string): Promise<AdminCourseFullResponse> => {
    return apiFetch<AdminCourseFullResponse>(`/admin/courses/${courseId}`);
};

export const adminCreateCourse = async (data: CourseCreateRequest): Promise<AdminCourseFullResponse> => {
    return apiFetch<AdminCourseFullResponse>("/admin/courses", {
        method: "POST",
        body: JSON.stringify(data),
    });
};

export const adminUpdateCourse = async (courseId: string, data: CourseUpdateRequest): Promise<AdminCourseFullResponse> => {
    return apiFetch<AdminCourseFullResponse>(`/admin/courses/${courseId}`, {
        method: "PUT",
        body: JSON.stringify(data),
    });
};

export const adminDeleteCourse = async (courseId: string): Promise<void> => {
    await apiFetch(`/admin/courses/${courseId}`, { method: "DELETE" });
};

// --- Module CRUD ---

export interface ModuleCreateRequest {
    course_id: string;
    title: string;
    description?: string;
    order_index?: number;
    is_published?: boolean;
}

export interface ModuleUpdateRequest {
    title?: string;
    description?: string;
    order_index?: number;
    is_published?: boolean;
}

export const adminGetCourseModules = async (courseId: string): Promise<ModuleResponse[]> => {
    return apiFetch<ModuleResponse[]>(`/admin/courses/${courseId}/modules`);
};

export const adminCreateModule = async (data: ModuleCreateRequest): Promise<ModuleResponse> => {
    return apiFetch<ModuleResponse>("/admin/modules", {
        method: "POST",
        body: JSON.stringify(data),
    });
};

export const adminUpdateModule = async (moduleId: string, data: ModuleUpdateRequest): Promise<ModuleResponse> => {
    return apiFetch<ModuleResponse>(`/admin/modules/${moduleId}`, {
        method: "PUT",
        body: JSON.stringify(data),
    });
};

export const adminDeleteModule = async (moduleId: string): Promise<void> => {
    await apiFetch(`/admin/modules/${moduleId}`, { method: "DELETE" });
};

// --- Lesson CRUD ---

export interface LessonCreateRequest {
    module_id: string;
    title: string;
    description?: string;
    content?: string;
    kinescope_video_id?: string;
    duration_seconds?: number;
    order_index?: number;
    is_preview?: boolean;
}

export interface LessonUpdateRequest {
    title?: string;
    description?: string;
    content?: string;
    kinescope_video_id?: string;
    duration_seconds?: number;
    order_index?: number;
    is_preview?: boolean;
}

export const adminGetLesson = async (lessonId: string): Promise<AdminLessonResponse> => {
    return apiFetch<AdminLessonResponse>(`/admin/lessons/${lessonId}`);
};

export const adminCreateLesson = async (data: LessonCreateRequest): Promise<AdminLessonResponse> => {
    return apiFetch<AdminLessonResponse>("/admin/lessons", {
        method: "POST",
        body: JSON.stringify(data),
    });
};

export const adminUpdateLesson = async (lessonId: string, data: LessonUpdateRequest): Promise<AdminLessonResponse> => {
    return apiFetch<AdminLessonResponse>(`/admin/lessons/${lessonId}`, {
        method: "PUT",
        body: JSON.stringify(data),
    });
};

export const updateLesson = adminUpdateLesson;

export const adminDeleteLesson = async (lessonId: string): Promise<void> => {
    await apiFetch(`/admin/lessons/${lessonId}`, { method: "DELETE" });
};

// --- Analytics ---

export const adminGetAnalytics = async (): Promise<AnalyticsResponse> => {
    return apiFetch<AnalyticsResponse>("/admin/analytics");
};

export const adminGetPurchases = async (): Promise<AdminPurchaseResponse[]> => {
    return apiFetch<AdminPurchaseResponse[]>("/admin/purchases");
};

// --- File Upload ---

export const adminUploadFile = uploadFile;


/**
 * ============================================
 * PAYMENTS METHODS
 * ============================================
 */

export interface PaymentLinkRequest {
    course_id: string;
    tariff: "self" | "support";
    customer_email?: string;
    customer_phone?: string;
}

export interface PaymentLinkResponse {
    url: string;
}

/**
 * Получить ссылку на оплату Prodamus
 */
export const getPaymentLink = async (data: PaymentLinkRequest): Promise<PaymentLinkResponse> => {
    return apiFetch<PaymentLinkResponse>("/payments/link", {
        method: "POST",
        body: JSON.stringify(data),
    });
};

export interface GuestPaymentLinkRequest {
    course_id: string;
    tariff: "self" | "support";
    customer_email: string;
    customer_phone?: string;
}

/**
 * Ссылка на оплату без регистрации (email в форме; после оплаты придёт пароль на почту).
 */
export const getGuestPaymentLink = async (data: GuestPaymentLinkRequest): Promise<PaymentLinkResponse> => {
    return apiFetch<PaymentLinkResponse>("/payments/guest-link", {
        method: "POST",
        body: JSON.stringify(data),
    });
};
