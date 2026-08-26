"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { zodResolver } from "@hookform/resolvers/zod"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { QRCodeSVG } from "qrcode.react"
import { z } from "zod"
import { toast } from "sonner"
import { Copy, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form"
import {
    ApiError,
    confirmMfa,
    login,
    LoginCredentials,
    MfaSetupResponse,
    setupMfa,
} from "@/lib/api"
import { safeNextPath } from "@/lib/navigation"
import { LoginSchema } from "@/lib/schemas"

type LoginStep = "credentials" | "mfa" | "setup" | "backup"

function errorCode(error: unknown): string | null {
    if (!(error instanceof ApiError) || !error.detail || typeof error.detail !== "object") {
        return null
    }
    const code = (error.detail as { code?: unknown }).code
    return typeof code === "string" ? code : null
}

function setupTokenFrom(error: unknown): string | null {
    if (!(error instanceof ApiError) || !error.detail || typeof error.detail !== "object") {
        return null
    }
    const token = (error.detail as { setup_token?: unknown }).setup_token
    return typeof token === "string" ? token : null
}

export default function LoginPage() {
    const [isLoading, setIsLoading] = useState(false)
    const [step, setStep] = useState<LoginStep>("credentials")
    const [credentials, setCredentials] = useState<LoginCredentials | null>(null)
    const [mfaCode, setMfaCode] = useState("")
    const [setupToken, setSetupToken] = useState("")
    const [setupData, setSetupData] = useState<MfaSetupResponse | null>(null)
    const [backupCodes, setBackupCodes] = useState<string[]>([])
    const router = useRouter()

    const form = useForm<z.infer<typeof LoginSchema>>({
        resolver: zodResolver(LoginSchema),
        defaultValues: { email: "", password: "" },
    })

    function finishLogin() {
        toast.success("Вход выполнен", { description: "Добро пожаловать обратно." })
        const next = new URLSearchParams(window.location.search).get("next")
        router.push(safeNextPath(next))
        router.refresh()
    }

    async function handleLoginError(error: unknown) {
        const code = errorCode(error)
        if (code === "mfa_code_required" || code === "mfa_code_invalid") {
            setStep("mfa")
            if (code === "mfa_code_invalid") {
                toast.error("Неверный одноразовый или резервный код")
            }
            return
        }
        if (code === "mfa_setup_required") {
            const token = setupTokenFrom(error)
            if (!token) throw error
            const data = await setupMfa(token)
            setSetupToken(token)
            setSetupData(data)
            setStep("setup")
            return
        }
        throw error
    }

    async function onSubmit(values: z.infer<typeof LoginSchema>) {
        setIsLoading(true)
        const pending = { email: values.email, password: values.password }
        setCredentials(pending)
        try {
            await login(pending)
            finishLogin()
        } catch (error) {
            try {
                await handleLoginError(error)
            } catch (unhandled) {
                toast.error("Ошибка входа", {
                    description: unhandled instanceof Error ? unhandled.message : "Попробуйте ещё раз",
                })
            }
        } finally {
            setIsLoading(false)
        }
    }

    async function submitMfa() {
        if (!credentials || mfaCode.trim().length < 6) return
        setIsLoading(true)
        try {
            await login({ ...credentials, mfa_code: mfaCode.trim() })
            finishLogin()
        } catch (error) {
            await handleLoginError(error).catch((unhandled) => {
                toast.error("Ошибка входа", {
                    description: unhandled instanceof Error ? unhandled.message : "Попробуйте ещё раз",
                })
            })
        } finally {
            setIsLoading(false)
        }
    }

    async function confirmSetup() {
        if (!setupToken || mfaCode.trim().length !== 6) return
        setIsLoading(true)
        try {
            const result = await confirmMfa(setupToken, mfaCode.trim())
            setBackupCodes(result.backup_codes)
            setStep("backup")
        } catch (error) {
            toast.error("Не удалось подтвердить MFA", {
                description: error instanceof Error ? error.message : "Проверьте код и попробуйте ещё раз",
            })
        } finally {
            setIsLoading(false)
        }
    }

    async function copyBackupCodes() {
        await navigator.clipboard.writeText(backupCodes.join("\n"))
        toast.success("Резервные коды скопированы")
    }

    const titles: Record<LoginStep, [string, string]> = {
        credentials: ["Вход в аккаунт", "Введите email и пароль для доступа к курсам"],
        mfa: ["Подтверждение входа", "Введите код из приложения-аутентификатора или резервный код"],
        setup: ["Защитите аккаунт", "Для владельцев и администраторов двухфакторная защита обязательна"],
        backup: ["Сохраните резервные коды", "Каждый код работает один раз. Храните их отдельно от пароля"],
    }

    return (
        <div className="flex min-h-[calc(100vh-200px)] flex-col items-center justify-center px-4 py-12">
            <Card className="w-full max-w-md">
                <CardHeader className="space-y-1">
                    <h1 className="text-center text-2xl font-bold leading-none">{titles[step][0]}</h1>
                    <CardDescription className="text-center">{titles[step][1]}</CardDescription>
                </CardHeader>
                <CardContent>
                    {step === "credentials" && (
                        <Form {...form}>
                            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                                <FormField
                                    control={form.control}
                                    name="email"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Email</FormLabel>
                                            <FormControl>
                                                <Input autoComplete="email" placeholder="name@example.com" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                <FormField
                                    control={form.control}
                                    name="password"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Пароль</FormLabel>
                                            <FormControl>
                                                <Input autoComplete="current-password" type="password" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                <div className="text-right">
                                    <Link href="/auth/forgot-password" className="text-sm text-muted-foreground hover:text-primary hover:underline">
                                        Забыли пароль?
                                    </Link>
                                </div>
                                <Button type="submit" className="w-full" disabled={isLoading}>
                                    {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                    Войти
                                </Button>
                            </form>
                        </Form>
                    )}

                    {step === "mfa" && (
                        <div className="space-y-4">
                            <label className="space-y-2 text-sm font-medium">
                                Код подтверждения
                                <Input
                                    autoFocus
                                    autoComplete="one-time-code"
                                    inputMode="numeric"
                                    value={mfaCode}
                                    onChange={(event) => setMfaCode(event.target.value)}
                                    placeholder="000000 или резервный код"
                                />
                            </label>
                            <Button className="w-full" disabled={isLoading || mfaCode.trim().length < 6} onClick={submitMfa}>
                                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Подтвердить
                            </Button>
                            <Button variant="ghost" className="w-full" onClick={() => { setStep("credentials"); setMfaCode("") }}>
                                Назад
                            </Button>
                        </div>
                    )}

                    {step === "setup" && setupData && (
                        <div className="space-y-5">
                            <div className="mx-auto w-fit rounded-xl bg-white p-3">
                                <QRCodeSVG value={setupData.provisioning_uri} size={190} level="M" />
                            </div>
                            <div className="space-y-1 text-sm">
                                <p>Отсканируйте QR-код в Google Authenticator, 1Password или другом TOTP-приложении.</p>
                                <p className="break-all rounded-md bg-muted p-2 font-mono text-xs">{setupData.secret}</p>
                            </div>
                            <Input
                                autoComplete="one-time-code"
                                inputMode="numeric"
                                maxLength={6}
                                value={mfaCode}
                                onChange={(event) => setMfaCode(event.target.value.replace(/\D/g, ""))}
                                placeholder="Код из приложения"
                            />
                            <Button className="w-full" disabled={isLoading || mfaCode.length !== 6} onClick={confirmSetup}>
                                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Включить двухфакторную защиту
                            </Button>
                        </div>
                    )}

                    {step === "backup" && (
                        <div className="space-y-5">
                            <div className="grid grid-cols-2 gap-2 rounded-lg bg-muted p-4 font-mono text-sm">
                                {backupCodes.map((code) => <span key={code}>{code}</span>)}
                            </div>
                            <Button variant="outline" className="w-full" onClick={copyBackupCodes}>
                                <Copy className="mr-2 h-4 w-4" />
                                Скопировать коды
                            </Button>
                            <Button className="w-full" onClick={finishLogin}>Я сохранил(а) коды</Button>
                        </div>
                    )}
                </CardContent>
                {step === "credentials" && (
                    <CardFooter className="flex justify-center">
                        <p className="text-sm text-muted-foreground">
                            Нет аккаунта?{" "}
                            <Link href="/auth/register" className="font-medium text-primary hover:underline">Зарегистрироваться</Link>
                        </p>
                    </CardFooter>
                )}
            </Card>
        </div>
    )
}
