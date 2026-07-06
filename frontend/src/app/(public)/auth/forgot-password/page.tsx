"use client"

import Link from "next/link"
import { useState } from "react"
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
import { forgotPassword } from "@/lib/api"

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState("")
    const [isLoading, setIsLoading] = useState(false)
    const [sent, setSent] = useState(false)

    async function onSubmit(event: React.FormEvent) {
        event.preventDefault()
        setIsLoading(true)
        try {
            await forgotPassword(email)
        } catch {
            // Не раскрываем, существует ли аккаунт — показываем тот же результат.
        } finally {
            setSent(true)
            setIsLoading(false)
        }
    }

    return (
        <div className="flex flex-col items-center justify-center min-h-[calc(100vh-200px)] py-12 px-4">
            <Card className="w-full max-w-md">
                <CardHeader className="space-y-1">
                    <CardTitle className="text-2xl font-bold text-center">Сброс пароля</CardTitle>
                    <CardDescription className="text-center">
                        Укажите email — вышлем ссылку для установки нового пароля
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {sent ? (
                        <p className="text-center text-sm text-muted-foreground">
                            Если аккаунт с таким email существует, мы отправили на него ссылку для
                            сброса пароля. Проверьте почту, в том числе папку «Спам».
                        </p>
                    ) : (
                        <form onSubmit={onSubmit} className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="email">Email</Label>
                                <Input
                                    id="email"
                                    type="email"
                                    placeholder="name@example.com"
                                    value={email}
                                    onChange={(event) => setEmail(event.target.value)}
                                    required
                                />
                            </div>
                            <Button type="submit" className="w-full" disabled={isLoading}>
                                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Отправить ссылку
                            </Button>
                        </form>
                    )}
                </CardContent>
                <CardFooter className="flex justify-center">
                    <p className="text-sm text-muted-foreground">
                        Вспомнили пароль?{" "}
                        <Link href="/auth/login" className="text-primary hover:underline font-medium">
                            Войти
                        </Link>
                    </p>
                </CardFooter>
            </Card>
        </div>
    )
}
