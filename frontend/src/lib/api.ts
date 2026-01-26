/**
 * API Client для взаимодействия с Backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

/**
 * Получить токен из localStorage
 */
const getAuthToken = (): string | null => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token");
};

/**
 * Базовый fetch с авторизацией
 */
async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const token = getAuthToken();

    const headers: HeadersInit = {
        "Content-Type": "application/json",
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options?.headers,
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
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
        headers: {
            ...(token && { Authorization: `Bearer ${token}` }),
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

    // Сохраняем токен в localStorage
    if (typeof window !== "undefined") {
        localStorage.setItem("access_token", response.access_token);
        localStorage.setItem("refresh_token", response.refresh_token);
    }

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
        if (typeof window !== "undefined") {
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");
        }
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
    is_published: boolean;
    created_at: string;
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

// --- File Upload ---

export const adminUploadFile = uploadFile;


