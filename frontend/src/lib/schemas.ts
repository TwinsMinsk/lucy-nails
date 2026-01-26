import * as z from "zod"

export const LoginSchema = z.object({
    email: z.string().email({ message: "Некорректный email адрес" }),
    password: z.string().min(6, { message: "Пароль должен содержать минимум 6 символов" }),
})

export const RegisterSchema = z.object({
    email: z.string().email({ message: "Некорректный email адрес" }),
    password: z.string().min(6, { message: "Пароль должен содержать минимум 6 символов" }),
    confirmPassword: z.string().min(6, { message: "Пароль должен содержать минимум 6 символов" }),
}).refine((data) => data.password === data.confirmPassword, {
    message: "Пароли не совпадают",
    path: ["confirmPassword"],
})
