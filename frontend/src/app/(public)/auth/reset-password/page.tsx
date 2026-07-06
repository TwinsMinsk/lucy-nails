"use client"

import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { Suspense, useState } from "react"
import { toast } from "sonner"
import { Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { resetPassword } from "@/lib/api"

function ResetPasswordForm() {
    const router = useRouter()
    const searchParams = useSearchParams()
    const token = searchParams.get("token") ?? ""

    const [password, setPassword] = useState("")
    const [confirm, setConfirm] = useState("")
    const [isLoading, setIsLoading] = useState(false)

    async function onSubmit(event: React.FormEvent) {
        event.preventDefault()
        if (password.length < 6) {
            toast.error("Пароль должен быть не короче 6 символов")
            return
        }
        if (password !== confirm) {
            toast.error("Пароли не совпадают")
            return
        }
        if (!token) {
            toast.error("Некорректная ссылка сброса пароля")
            return
        }
        setIsLoading(true)
        try {
            await resetPassword(token, password)
            toast.success("Пароль обновлён", { description: "Войдите с новым паролем." })
            router.push("/auth/login")
        } catch (error) {
            const message = error instanceof Error ? error.message : "Ссылка недействительна или истекла"
            toast.error("Ошибка", { description: message })
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <Card className="w-full max-w-md">
            <CardHeader className="space-y-1">
                <CardTitle className="text-2xl font-bold text-center">Новый пароль</CardTitle>
                <CardDescription className="text-center">
                    Придумайте новый пароль для входа в кабинет
                </CardDescription>
            </CardHeader>
            <CardContent>
                <form onSubmit={onSubmit} className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="password">Новый пароль</Label>
                        <Input
                            id="password"
                            type="password"
                            placeholder="••••••••"
                            value={password}
                            onChange={(event) => setPassword(event.target.value)}
                            required
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="confirm">Повторите пароль</Label>
                        <Input
                            id="confirm"
                            type="password"
                            placeholder="••••••••"
                            value={confirm}
                            onChange={(event) => setConfirm(event.target.value)}
                            required
                        />
                    </div>
                    <Button type="submit" className="w-full" disabled={isLoading}>
                        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Сохранить пароль
                    </Button>
                </form>
            </CardContent>
            <CardFooter className="flex justify-center">
                <p className="text-sm text-muted-foreground">
                    <Link href="/auth/login" className="text-primary hover:underline font-medium">
                        Вернуться ко входу
                    </Link>
                </p>
            </CardFooter>
        </Card>
    )
}

export default function ResetPasswordPage() {
    return (
        <div className="flex flex-col items-center justify-center min-h-[calc(100vh-200px)] py-12 px-4">
            <Suspense
                fallback={
                    <div className="flex justify-center">
                        <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    </div>
                }
            >
                <ResetPasswordForm />
            </Suspense>
        </div>
    )
}
