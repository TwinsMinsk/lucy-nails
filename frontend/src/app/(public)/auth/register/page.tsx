"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { useState } from "react"
import { z } from "zod"
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
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form"
import {
    type ConsentState,
    focusFirstMissingConsent,
    hasFullConsent,
    NO_CONSENT,
    PersonalDataConsent,
} from "@/components/legal/PersonalDataConsent"
import { RegisterSchema } from "@/lib/schemas"
import { register, login } from "@/lib/api"
import { CONSENT_VERSION } from "@/lib/legal"
import { safeNextPath } from "@/lib/navigation"

const CONSENT_ID = "register-consent"

export default function RegisterPage() {
    const [isLoading, setIsLoading] = useState(false)
    const [consent, setConsent] = useState<ConsentState>(NO_CONSENT)
    const [consentError, setConsentError] = useState(false)
    const router = useRouter()

    const form = useForm<z.infer<typeof RegisterSchema>>({
        resolver: zodResolver(RegisterSchema),
        defaultValues: {
            email: "",
            password: "",
            confirmPassword: "",
        },
    })

    const consentGiven = hasFullConsent(consent)

    function handleConsentChange(value: ConsentState) {
        setConsent(value)
        if (hasFullConsent(value)) setConsentError(false)
    }

    async function onSubmit(values: z.infer<typeof RegisterSchema>) {
        if (!consentGiven) {
            setConsentError(true)
            focusFirstMissingConsent(CONSENT_ID, consent)
            return
        }
        setIsLoading(true)

        try {
            const email = values.email.trim()

            // 1. Регистрация
            await register({
                email,
                password: values.password,
                offer_accepted: consent.offer,
                personal_data_consent: consent.personalData,
                consent_version: CONSENT_VERSION,
            })

            toast.success("Регистрация успешна!", {
                description: "Аккаунт создан. Выполняется вход..."
            })

            // 2. Auto-login после успешной регистрации
            await login({
                email,
                password: values.password,
            })

            toast.success("Добро пожаловать!", {
                description: "Вход выполнен автоматически."
            })

            const next = new URLSearchParams(window.location.search).get("next")
            router.push(safeNextPath(next))
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Ошибка регистрации"
            toast.error("Ошибка", {
                description: errorMessage
            })
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="flex flex-col items-center justify-center min-h-[calc(100vh-200px)] py-12 px-4">
            <Card className="w-full max-w-md">
                <CardHeader className="space-y-1">
                    <CardTitle className="text-2xl font-bold text-center">Регистрация</CardTitle>
                    <CardDescription className="text-center">
                        Создайте аккаунт для покупки и просмотра курсов
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <Form {...form}>
                        <form
                            onSubmit={form.handleSubmit(onSubmit, () => {
                                if (!consentGiven) setConsentError(true)
                            })}
                            className="space-y-4"
                        >
                            <FormField
                                control={form.control}
                                name="email"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Email</FormLabel>
                                        <FormControl>
                                            <Input
                                                type="email"
                                                autoComplete="email"
                                                autoCapitalize="none"
                                                autoCorrect="off"
                                                spellCheck={false}
                                                placeholder="name@example.com"
                                                {...field}
                                            />
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
                                            <Input type="password" placeholder="••••••••" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <FormField
                                control={form.control}
                                name="confirmPassword"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Подтвердите пароль</FormLabel>
                                        <FormControl>
                                            <Input type="password" placeholder="••••••••" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <PersonalDataConsent
                                id={CONSENT_ID}
                                value={consent}
                                onChange={handleConsentChange}
                                showError={consentError}
                                disabled={isLoading}
                            />
                            {/* aria-disabled (not disabled) keeps the click alive so we can explain why it is blocked */}
                            <Button
                                type="submit"
                                className="w-full aria-disabled:opacity-50 aria-disabled:cursor-not-allowed"
                                disabled={isLoading}
                                aria-disabled={!consentGiven}
                            >
                                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Зарегистрироваться
                            </Button>
                        </form>
                    </Form>
                </CardContent>
                <CardFooter className="flex justify-center">
                    <p className="text-sm text-muted-foreground">
                        Уже есть аккаунт?{" "}
                        <Link href="/auth/login" className="text-primary hover:underline font-medium">
                            Войти
                        </Link>
                    </p>
                </CardFooter>
            </Card>
        </div>
    )
}
