"use client"

import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { Suspense, useEffect, useState } from "react"
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
import { activateAccount, ApiError } from "@/lib/api"

const INVALID_LINK_MESSAGE = "Ссылка недействительна или устарела — запросите новую через «Забыли пароль?»"

function LinkHelp() {
    return (
        <p className="text-sm text-muted-foreground text-center">
            <Link href="/auth/forgot-password" className="text-primary hover:underline font-medium">
                Забыли пароль?
            </Link>
            {" · "}
            <Link href="/auth/login" className="text-primary hover:underline font-medium">
                Войти
            </Link>
        </p>
    )
}

function ActivateAccountForm() {
    const router = useRouter()
    const searchParams = useSearchParams()
    // Read the token once, then drop it from the address bar and history.
    const [token] = useState(() => searchParams.get("token") ?? "")

    useEffect(() => {
        if (token) window.history.replaceState({}, "", "/auth/activate")
    }, [token])

    const [password, setPassword] = useState("")
    const [confirm, setConfirm] = useState("")
    const [isLoading, setIsLoading] = useState(false)
    const [linkInvalid, setLinkInvalid] = useState(false)

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
        setIsLoading(true)
        try {
            await activateAccount(token, password)
            toast.success("Пароль сохранён. Войдите с вашим email и новым паролем")
            router.replace("/auth/login")
        } catch (error) {
            // 422 is a malformed token; never show raw validation text to the user.
            if (error instanceof ApiError && (error.status === 400 || error.status === 422)) {
                setLinkInvalid(true)
                toast.error(INVALID_LINK_MESSAGE)
                return
            }
            const message = error instanceof Error ? error.message : "Попробуйте ещё раз"
            toast.error("Не удалось сохранить пароль", { description: message })
        } finally {
            setIsLoading(false)
        }
    }

    if (!token) {
        return (
            <Card className="w-full max-w-md">
                <CardHeader className="space-y-1">
                    <CardTitle className="text-2xl font-bold text-center">Создайте пароль</CardTitle>
                    <CardDescription className="text-center">
                        Код активации не найден. Откройте ссылку из письма ещё раз
                        или запросите новую через «Забыли пароль?» — укажите email, на который оформлен курс.
                    </CardDescription>
                </CardHeader>
                <CardFooter className="flex justify-center">
                    <LinkHelp />
                </CardFooter>
            </Card>
        )
    }

    return (
        <Card className="w-full max-w-md">
            <CardHeader className="space-y-1">
                <CardTitle className="text-2xl font-bold text-center">Создайте пароль</CardTitle>
                <CardDescription className="text-center">
                    Задайте пароль для входа в личный кабинет Lucy Nails Academy
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                {linkInvalid && (
                    <div role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
                        {INVALID_LINK_MESSAGE}
                    </div>
                )}
                <form onSubmit={onSubmit} className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="password">Пароль</Label>
                        <Input
                            id="password"
                            type="password"
                            autoComplete="new-password"
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
                            autoComplete="new-password"
                            placeholder="••••••••"
                            value={confirm}
                            onChange={(event) => setConfirm(event.target.value)}
                            required
                        />
                    </div>
                    <Button type="submit" className="w-full" disabled={isLoading}>
                        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Сохранить пароль и продолжить
                    </Button>
                </form>
            </CardContent>
            <CardFooter className="flex justify-center">
                <LinkHelp />
            </CardFooter>
        </Card>
    )
}

export default function ActivateAccountPage() {
    return (
        <div className="flex flex-col items-center justify-center min-h-[calc(100vh-200px)] py-12 px-4">
            <Suspense
                fallback={
                    <div className="flex justify-center">
                        <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    </div>
                }
            >
                <ActivateAccountForm />
            </Suspense>
        </div>
    )
}
