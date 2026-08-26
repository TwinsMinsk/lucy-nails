/**
 * API Client для взаимодействия с Backend
 */
import { getPublicApiUrl } from "@/lib/env";
import type { CheckoutAttribution } from "@/lib/attribution";

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

export class ApiError extends Error {
    constructor(
        public readonly status: number,
        public readonly detail: unknown,
        fallback: string,
    ) {
        super(parseErrorDetail(detail, fallback));
        this.name = "ApiError";
    }
}

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
        throw new ApiError(response.status, errorData.detail, `HTTP ${response.status}`);
    }

    if (response.status === 204) {
        return undefined as T;
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
    mfa_code?: string;
}

export interface MfaSetupResponse {
    secret: string;
    provisioning_uri: string;
}

export interface MfaConfirmResponse extends TokenResponse {
    backup_codes: string[];
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

export const setupMfa = async (setupToken: string): Promise<MfaSetupResponse> => {
    return apiFetch<MfaSetupResponse>("/auth/mfa/setup", {
        method: "POST",
        body: JSON.stringify({ setup_token: setupToken }),
    });
};

export const confirmMfa = async (
    setupToken: string,
    code: string,
): Promise<MfaConfirmResponse> => {
    const response = await apiFetch<MfaConfirmResponse>("/auth/mfa/confirm", {
        method: "POST",
        body: JSON.stringify({ setup_token: setupToken, code }),
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

export interface TelegramStatusResponse {
    connected: boolean;
    username?: string | null;
}

export interface TelegramLinkResponse extends TelegramStatusResponse {
    url: string;
    expires_at: string;
}

export const getTelegramStatus = async (): Promise<TelegramStatusResponse> => {
    return apiFetch<TelegramStatusResponse>("/telegram/status");
};

export const createTelegramLink = async (): Promise<TelegramLinkResponse> => {
    return apiFetch<TelegramLinkResponse>("/telegram/link", { method: "POST" });
};

export const disconnectTelegram = async (): Promise<void> => {
    await apiFetch<void>("/telegram/link", { method: "DELETE" });
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
 * Сменить пароль (требуется авторизация)
 */
export const changePassword = async (
    currentPassword: string,
    newPassword: string
): Promise<{ message: string }> => {
    return apiFetch<{ message: string }>("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
};

/**
 * Запросить ссылку на сброс пароля (отправляется на email)
 */
export const forgotPassword = async (email: string): Promise<{ message: string }> => {
    return apiFetch<{ message: string }>("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
    });
};

/**
 * Установить новый пароль по токену из письма
 */
export const resetPassword = async (
    token: string,
    newPassword: string
): Promise<{ message: string }> => {
    return apiFetch<{ message: string }>("/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, new_password: newPassword }),
    });
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
    access_days: number;
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
    certificate_number?: string | null;
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

export interface ProgressResponse {
    id: string;
    user_id: string;
    lesson_id: string;
    watched_seconds: number;
    is_completed: boolean;
    completed_at: string | null;
    updated_at: string;
}

/**
 * Обновить прогресс урока (например, пометить как завершенный)
 */
export const updateLessonProgress = async (lessonId: string, data: { is_completed: boolean; watched_seconds?: number }): Promise<ProgressResponse> => {
    return apiFetch<ProgressResponse>(`/lessons/${lessonId}/progress`, {
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
    access_days: number;
}

export interface VideoHealthItem {
    lesson_id: string;
    lesson_title: string;
    module_title: string;
    course_id: string;
    course_title: string;
    video_id?: string | null;
    expected_duration_seconds: number;
    provider_duration_seconds?: number | null;
    provider_status?: string | null;
    progress?: number | null;
    privacy_type?: string | null;
    status: "ready" | "missing_video_id" | "duration_mismatch" | "processing" | "provider_error";
    detail?: string | null;
}

export interface VideoHealthResponse {
    total: number;
    ready: number;
    problems: number;
    items: VideoHealthItem[];
}

export interface GrantAccessRequest {
    user_id: string;
    course_id: string;
    tariff?: "self" | "support";
    access_days?: number;
    reason: string;
}

export interface GrantAccessResponse {
    message: string;
    entitlement_id: string;
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
    tariff: "self" | "support" = "self",
    reason: string,
    accessDays?: number,
): Promise<GrantAccessResponse> => {
    return apiFetch<GrantAccessResponse>("/admin/grant-access", {
        method: "POST",
        body: JSON.stringify({
            user_id: userId,
            course_id: courseId,
            tariff,
            reason,
            access_days: accessDays,
        }),
    });
};

export interface RevokeAccessResponse {
    message: string;
    purchase_id: string;
    payment_status: string;
}

/**
 * Отозвать доступ по покупке (возврат/chargeback) — только для админов
 */
export const adminRevokeAccess = async (
    purchaseId: string
): Promise<RevokeAccessResponse> => {
    return apiFetch<RevokeAccessResponse>("/admin/revoke-access", {
        method: "POST",
        body: JSON.stringify({ purchase_id: purchaseId }),
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
    access_days: number;
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
    promo_kinescope_video_id?: string | null;
    promo_poster_url?: string | null;
    promo_description?: string | null;
    promo_highlights?: { bullets?: string[] } | null;
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
    access_days?: number;
}

export interface CourseUpdateRequest {
    title?: string;
    description?: string;
    cover_image_url?: string;
    price_self?: number;
    price_support?: number;
    is_published?: boolean;
    access_days?: number;
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
    promo_kinescope_video_id?: string;
    promo_poster_url?: string;
    promo_description?: string;
    promo_highlights?: { bullets?: string[] };
}

export interface LessonUpdateRequest {
    title?: string;
    description?: string;
    content?: string;
    kinescope_video_id?: string;
    duration_seconds?: number;
    order_index?: number;
    is_preview?: boolean;
    promo_kinescope_video_id?: string;
    promo_poster_url?: string;
    promo_description?: string;
    promo_highlights?: { bullets?: string[] };
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

export const adminCheckVideoHealth = async (courseId?: string): Promise<VideoHealthResponse> => {
    const query = courseId ? `?course_id=${encodeURIComponent(courseId)}` : "";
    return apiFetch<VideoHealthResponse>(`/admin/content/video-health${query}`, {
        method: "POST",
    });
};

// --- Operational CRM ---

export interface AdminDashboardResponse {
    total_students: number;
    active_entitlements: number;
    gross_revenue_kopecks: number;
    refunded_kopecks: number;
    net_revenue_kopecks: number;
    pending_orders: number;
    payment_errors: number;
    notification_dead_letters: number;
    expiring_entitlements_7d: number;
}

export interface PageResponse<T> {
    items: T[];
    total: number;
    limit: number;
    offset: number;
}

export interface AdminStudentListItem {
    id: string;
    email: string;
    full_name?: string | null;
    phone?: string | null;
    role: string;
    created_at: string;
    active_entitlements: number;
}

export interface AdminEntitlement {
    id: string;
    user_id?: string;
    user_email?: string;
    course_id: string;
    course_title: string;
    source: string;
    tariff: string;
    status: string;
    starts_at: string;
    expires_at: string;
    reason?: string | null;
    revoked_at?: string | null;
}

export interface AdminStudentDetail {
    id: string;
    email: string;
    full_name?: string | null;
    phone?: string | null;
    role: string;
    created_at: string;
    telegram_id?: number | null;
    telegram_username?: string | null;
    completed_lessons: number;
    tracked_lessons: number;
    last_activity_at?: string | null;
    purchases: AdminPurchaseResponse[];
    entitlements: AdminEntitlement[];
    certificates: Array<{
        id: string;
        course_id: string;
        certificate_number: string;
        student_name: string;
        issued_at: string;
    }>;
    notes: Array<{ id: string; author_id: string; body: string; created_at: string }>;
    tags: string[];
}

export interface AdminOrder {
    id: string;
    customer_email: string;
    customer_phone?: string | null;
    course_id: string;
    course_title: string;
    tariff: string;
    amount_kopecks: number;
    currency: string;
    access_days: number;
    status: string;
    purchase_id?: string | null;
    paid_at?: string | null;
    created_at: string;
    updated_at: string;
}

export interface AdminNotification {
    id: string;
    kind: string;
    channel: string;
    recipient: string;
    status: string;
    attempts: number;
    max_attempts: number;
    next_attempt_at: string;
    sent_at?: string | null;
    last_error?: string | null;
    created_at: string;
    updated_at: string;
}

export interface AdminPaymentEvent {
    id: string;
    external_event_id?: string | null;
    order_reference?: string | null;
    order_id?: string | null;
    purchase_id?: string | null;
    event_type: string;
    processing_status: string;
    amount_kopecks?: number | null;
    currency?: string | null;
    error_code?: string | null;
    error_detail?: string | null;
    received_at: string;
    processed_at?: string | null;
}

export interface AdminReconciliation {
    stale_pending_orders: number;
    processed_payment_errors: number;
    successful_purchases_without_active_entitlement: number;
    dead_letter_notifications: number;
}

export interface AdminRefund {
    id: string;
    purchase_id: string;
    amount_kopecks: number;
    reason: string;
    status: "requested" | "submitted" | "processed" | "rejected";
    provider_reference?: string | null;
    note?: string | null;
    created_by_id: string;
    processed_by_id?: string | null;
    processed_at?: string | null;
    created_at: string;
    updated_at: string;
}

export interface AdminCapabilities {
    roles: string[];
    permissions: string[];
}

export interface AdminRole {
    id: string;
    name: string;
    description: string;
    permissions: string[];
}

export interface AdminTeamUser {
    id: string;
    email: string;
    full_name?: string | null;
    roles: string[];
    mfa_enabled: boolean;
    active_sessions: number;
}

export interface AdminAuditLog {
    id: string;
    actor_user_id?: string | null;
    action: string;
    object_type: string;
    object_id?: string | null;
    old_value?: Record<string, unknown> | null;
    new_value?: Record<string, unknown> | null;
    reason?: string | null;
    correlation_id: string;
    created_at: string;
}

export interface AdminSystemStatus {
    checkout_enabled: boolean;
    environment: string;
    integrations: Record<string, boolean>;
    outbox_pending: number;
    outbox_dead_letter: number;
    last_payment_event_at?: string | null;
}

export interface AdminCertificate {
    id: string;
    user_id: string;
    student_email: string;
    course_id: string;
    course_title: string;
    certificate_number: string;
    student_name: string;
    pdf_url?: string | null;
    png_url?: string | null;
    status: string;
    revoke_reason?: string | null;
    revoked_at?: string | null;
    issued_at: string;
}

export interface ReportOverview {
    date_from: string;
    date_to: string;
    gross_revenue_kopecks: number;
    refunded_kopecks: number;
    net_revenue_kopecks: number;
    paid_orders: number;
    pending_orders: number;
    new_students: number;
}

export interface ReportTimeseriesPoint {
    date: string;
    orders: number;
    gross_revenue_kopecks: number;
    refunded_kopecks: number;
    net_revenue_kopecks: number;
}

export interface ReportFunnelStage {
    event_name: string;
    label: string;
    count: number;
    conversion_from_previous_pct?: number | null;
}

export interface ReportSource {
    source: string;
    orders: number;
    paid_orders: number;
    gross_revenue_kopecks: number;
    conversion_pct: number;
}

export interface ReportTariff {
    tariff: string;
    paid_orders: number;
    gross_revenue_kopecks: number;
}

export interface ReportCohort {
    cohort: string;
    students: number;
    purchasers: number;
    certified_students: number;
}

export interface ReportProgress {
    active_students: number;
    completed_lessons: number;
    certificates_issued: number;
}

export interface ReportRefund {
    status: string;
    requests: number;
    amount_kopecks: number;
}

export interface ReportDelivery {
    total: number;
    sent: number;
    pending: number;
    retry: number;
    dead_letter: number;
    success_rate_pct: number;
}

const queryString = (params: Record<string, string | number | boolean | undefined | null>) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
    });
    const suffix = query.toString();
    return suffix ? `?${suffix}` : "";
};

export const adminGetDashboard = () => apiFetch<AdminDashboardResponse>("/admin/dashboard");
export const adminGetCapabilities = () => apiFetch<AdminCapabilities>("/admin/team/me");
export const adminGetRoles = () => apiFetch<AdminRole[]>("/admin/team/roles");
export const adminGetTeamUsers = () => apiFetch<AdminTeamUser[]>("/admin/team/users");
export const adminUpdateTeamRoles = (userId: string, roles: string[], reason: string) =>
    apiFetch<{ user_id: string; roles: string[] }>(`/admin/team/users/${userId}/roles`, {
        method: "PUT",
        body: JSON.stringify({ roles, reason }),
    });
export const adminGetAuditLogs = (params: { limit?: number; offset?: number; action?: string } = {}) =>
    apiFetch<AdminAuditLog[]>(`/admin/audit-logs${queryString(params)}`);
export const adminGetSystemStatus = () => apiFetch<AdminSystemStatus>("/admin/system/status");
export const adminGetCertificates = (params: {
    search?: string; status?: string; limit?: number; offset?: number;
} = {}) => apiFetch<PageResponse<AdminCertificate>>(`/admin/certificates${queryString(params)}`);
export const adminReissueCertificate = (certificateId: string, reason: string) =>
    apiFetch<AdminCertificate>(`/admin/certificates/${certificateId}/reissue`, {
        method: "POST", body: JSON.stringify({ reason }),
    });
export const adminRevokeCertificate = (certificateId: string, reason: string) =>
    apiFetch<AdminCertificate>(`/admin/certificates/${certificateId}/revoke`, {
        method: "POST", body: JSON.stringify({ reason }),
    });

export const adminGetReportOverview = (params: { date_from?: string; date_to?: string } = {}) =>
    apiFetch<ReportOverview>(`/admin/reports/overview${queryString(params)}`);
export const adminGetReportTimeseries = (params: { date_from?: string; date_to?: string } = {}) =>
    apiFetch<ReportTimeseriesPoint[]>(`/admin/reports/timeseries${queryString(params)}`);
export const adminGetReportFunnel = (params: { date_from?: string; date_to?: string } = {}) =>
    apiFetch<{ stages: ReportFunnelStage[] }>(`/admin/reports/funnel${queryString(params)}`);
export const adminGetReportSources = (params: { date_from?: string; date_to?: string } = {}) =>
    apiFetch<ReportSource[]>(`/admin/reports/sources${queryString(params)}`);
export const adminGetReportTariffs = (params: { date_from?: string; date_to?: string } = {}) =>
    apiFetch<ReportTariff[]>(`/admin/reports/tariffs${queryString(params)}`);
export const adminGetReportCohorts = (params: { date_from?: string; date_to?: string } = {}) =>
    apiFetch<ReportCohort[]>(`/admin/reports/cohorts${queryString(params)}`);
export const adminGetReportProgress = (params: { date_from?: string; date_to?: string } = {}) =>
    apiFetch<ReportProgress>(`/admin/reports/progress${queryString(params)}`);
export const adminGetReportRefunds = (params: { date_from?: string; date_to?: string } = {}) =>
    apiFetch<ReportRefund[]>(`/admin/reports/refunds${queryString(params)}`);
export const adminGetReportDelivery = (params: { date_from?: string; date_to?: string } = {}) =>
    apiFetch<ReportDelivery>(`/admin/reports/delivery${queryString(params)}`);
export const adminReportSourcesCsvUrl = (params: { date_from?: string; date_to?: string } = {}) =>
    `${API_BASE_URL}/admin/reports/sources${queryString({ ...params, format: "csv" })}`;

export const adminGetStudents = (params: {
    search?: string; active_access?: boolean; limit?: number; offset?: number;
} = {}) => apiFetch<PageResponse<AdminStudentListItem>>(`/admin/students${queryString(params)}`);

export const adminGetStudent = (userId: string) =>
    apiFetch<AdminStudentDetail>(`/admin/students/${userId}`);

export const adminCreateStudentNote = (userId: string, body: string) =>
    apiFetch(`/admin/students/${userId}/notes`, {
        method: "POST",
        body: JSON.stringify({ body }),
    });

export const adminUpdateStudentTags = (userId: string, tags: string[], reason: string) =>
    apiFetch<string[]>(`/admin/students/${userId}/tags`, {
        method: "PUT",
        body: JSON.stringify({ tags, reason }),
    });

export const adminGetEntitlements = (params: {
    search?: string; status?: string; expiring_days?: number; limit?: number; offset?: number;
} = {}) => apiFetch<PageResponse<AdminEntitlement>>(`/admin/entitlements${queryString(params)}`);

export const adminRevokeEntitlement = (entitlementId: string, reason: string) =>
    apiFetch<{ message: string; entitlement_id: string; status: string }>("/admin/revoke-entitlement", {
        method: "POST",
        body: JSON.stringify({ entitlement_id: entitlementId, reason }),
    });

export const adminGetOrders = (params: {
    search?: string; status?: string; limit?: number; offset?: number;
} = {}) => apiFetch<PageResponse<AdminOrder>>(`/admin/orders${queryString(params)}`);

export const adminGetNotifications = (params: {
    status?: string; channel?: string; limit?: number; offset?: number;
} = {}) => apiFetch<PageResponse<AdminNotification>>(`/admin/notifications${queryString(params)}`);

export const adminRetryNotification = (messageId: string, reason: string) =>
    apiFetch<AdminNotification>(`/admin/notifications/${messageId}/retry`, {
        method: "POST",
        body: JSON.stringify({ reason }),
    });

export const adminGetPaymentEvents = (params: {
    status?: string; limit?: number; offset?: number;
} = {}) => apiFetch<PageResponse<AdminPaymentEvent>>(`/admin/payment-events${queryString(params)}`);

export const adminGetReconciliation = () =>
    apiFetch<AdminReconciliation>("/admin/reconciliation");

export const adminGetRefunds = () => apiFetch<AdminRefund[]>("/admin/refunds");

export const adminCreateRefund = (data: {
    purchase_id: string; amount_kopecks: number; reason: string;
}) => apiFetch<AdminRefund>("/admin/refunds", { method: "POST", body: JSON.stringify(data) });

export const adminUpdateRefund = (
    refundId: string,
    data: { status: AdminRefund["status"]; provider_reference?: string; note?: string },
) => apiFetch<AdminRefund>(`/admin/refunds/${refundId}`, { method: "PUT", body: JSON.stringify(data) });

// --- File Upload ---

export const adminUploadFile = uploadFile;


/**
 * ============================================
 * LANDING (hero / program / gallery) METHODS
 * ============================================
 */

export interface HeroStat {
    label: string;
    value: string;
}

export interface LandingHeroPayload {
    landing_title?: string | null;
    landing_subtitle?: string | null;
    landing_description?: string | null;
    landing_audience?: string | null;
    landing_support_note?: string | null;
    landing_hero_stats?: HeroStat[] | null;
    landing_benefits?: string[] | null;
    landing_instructor_image_url?: string | null;
}

export interface LandingModulePayload {
    id: string;
    title: string;
    order_index: number;
    landing_description?: string | null;
    landing_outcome?: string | null;
    landing_bullets?: string[] | null;
    landing_mistakes?: string[] | null;
    landing_duration_label?: string | null;
}

export interface LandingModuleUpdate {
    landing_description?: string | null;
    landing_outcome?: string | null;
    landing_bullets?: string[] | null;
    landing_mistakes?: string[] | null;
    landing_duration_label?: string | null;
}

export interface GalleryItem {
    id: string;
    order_index: number;
    image_url: string;
    title: string;
    caption?: string | null;
    alt?: string | null;
    is_published: boolean;
    created_at: string;
    updated_at: string;
}

export interface GalleryItemCreate {
    image_url: string;
    title: string;
    caption?: string | null;
    alt?: string | null;
    is_published?: boolean;
    order_index?: number;
}

export interface GalleryItemUpdate {
    image_url?: string;
    title?: string;
    caption?: string | null;
    alt?: string | null;
    is_published?: boolean;
    order_index?: number;
}

export interface LandingPayload {
    course_id: string | null;
    hero: LandingHeroPayload;
    modules: LandingModulePayload[];
    gallery: GalleryItem[];
}

export const getLandingPayload = async (): Promise<LandingPayload> => {
    const base = getBaseUrl();
    const res = await fetch(`${base}/landing`, { next: { revalidate: 120 } });
    if (!res.ok) {
        throw new Error(`Failed to load landing payload: ${res.status}`);
    }
    return res.json();
};

export const adminGetCourseLandingHero = async (courseId: string): Promise<LandingHeroPayload> => {
    return apiFetch<LandingHeroPayload>(`/admin/courses/${courseId}/landing-hero`);
};

export const adminUpdateCourseLandingHero = async (
    courseId: string,
    data: LandingHeroPayload,
): Promise<LandingHeroPayload> => {
    return apiFetch<LandingHeroPayload>(`/admin/courses/${courseId}/landing-hero`, {
        method: "PUT",
        body: JSON.stringify(data),
    });
};

export const adminGetCourseLandingModules = async (
    courseId: string,
): Promise<LandingModulePayload[]> => {
    return apiFetch<LandingModulePayload[]>(`/admin/courses/${courseId}/landing-modules`);
};

export const adminUpdateModuleLanding = async (
    moduleId: string,
    data: LandingModuleUpdate,
): Promise<LandingModulePayload> => {
    return apiFetch<LandingModulePayload>(`/admin/modules/${moduleId}/landing`, {
        method: "PUT",
        body: JSON.stringify(data),
    });
};

export const adminGetGallery = async (): Promise<GalleryItem[]> => {
    return apiFetch<GalleryItem[]>("/admin/gallery");
};

export const adminCreateGalleryItem = async (data: GalleryItemCreate): Promise<GalleryItem> => {
    return apiFetch<GalleryItem>("/admin/gallery", {
        method: "POST",
        body: JSON.stringify(data),
    });
};

export const adminUpdateGalleryItem = async (
    itemId: string,
    data: GalleryItemUpdate,
): Promise<GalleryItem> => {
    return apiFetch<GalleryItem>(`/admin/gallery/${itemId}`, {
        method: "PUT",
        body: JSON.stringify(data),
    });
};

export const adminDeleteGalleryItem = async (itemId: string): Promise<void> => {
    await apiFetch(`/admin/gallery/${itemId}`, { method: "DELETE" });
};

export const adminReorderGallery = async (
    items: { id: string; order_index: number }[],
): Promise<GalleryItem[]> => {
    return apiFetch<GalleryItem[]>("/admin/gallery/reorder", {
        method: "PUT",
        body: JSON.stringify(items),
    });
};


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
    attribution?: CheckoutAttribution;
}

export interface PaymentLinkResponse {
    url: string;
    order_id: string;
    status_token: string;
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
    attribution?: CheckoutAttribution;
}

export interface PublicAnalyticsEvent {
    event_id: string;
    event_name: "landing_view" | "cta_click";
    source: "web";
    happened_at?: string;
    anonymous_id: string;
    course_id?: string;
    utm_source?: string;
    utm_medium?: string;
    utm_campaign?: string;
    utm_content?: string;
    utm_term?: string;
    properties?: Record<string, string | number | boolean | null>;
}

export const postAnalyticsEvent = (event: PublicAnalyticsEvent) =>
    apiFetch<{ accepted: boolean; duplicate: boolean }>("/analytics/events", {
        method: "POST",
        body: JSON.stringify(event),
    });

/**
 * Ссылка на оплату без регистрации (email в форме; после оплаты придёт пароль на почту).
 */
export const getGuestPaymentLink = async (data: GuestPaymentLinkRequest): Promise<PaymentLinkResponse> => {
    return apiFetch<PaymentLinkResponse>("/payments/guest-link", {
        method: "POST",
        body: JSON.stringify(data),
    });
};

/**
 * ============================================
 * CERTIFICATES
 * ============================================
 */

export interface CertificateResponse {
    id: string;
    certificate_number: string;
    course_id: string;
    course_title: string;
    student_name: string;
    png_url: string | null;
    pdf_url: string | null;
    issued_at: string;
}

export interface CertificateStatusResponse {
    status: "not_available" | "available" | "issued";
    progress_percent: number;
    certificate: CertificateResponse | null;
}

export interface CertificateVerifyResponse {
    certificate_number: string;
    student_name: string;
    course_id: string;
    course_title: string;
    issued_at: string;
    png_url: string | null;
    pdf_url: string | null;
}

/**
 * Получить сертификат за прохождение курса (идемпотентно — повторный вызов вернёт тот же сертификат)
 */
export const claimCertificate = async (courseId: string, fullName: string): Promise<CertificateResponse> => {
    return apiFetch<CertificateResponse>(`/courses/${courseId}/certificate`, {
        method: "POST",
        body: JSON.stringify({ full_name: fullName }),
    });
};

/**
 * Получить статус сертификата по курсу (доступность, прогресс, сам сертификат если выдан)
 */
export const getCertificateStatus = async (courseId: string): Promise<CertificateStatusResponse> => {
    return apiFetch<CertificateStatusResponse>(`/courses/${courseId}/certificate`);
};

/**
 * Публичная проверка сертификата по номеру (без авторизации). Для SSR на странице проверки.
 */
export async function verifyCertificate(number: string): Promise<CertificateVerifyResponse | null> {
    const base = getBaseUrl();
    const res = await fetch(`${base}/certificates/verify/${encodeURIComponent(number)}`, { cache: "no-store" });
    if (res.status === 404) {
        return null;
    }
    if (!res.ok) {
        throw new Error(`Failed to verify certificate: ${res.status}`);
    }
    return res.json();
}

/**
 * Абсолютный URL на файл сертификата (PDF/PNG) — публичный эндпоинт со скачиванием
 */
export function certificateFileUrl(number: string, format: "pdf" | "png"): string {
    return `${API_BASE_URL}/certificates/${encodeURIComponent(number)}/file?format=${format}`;
}
