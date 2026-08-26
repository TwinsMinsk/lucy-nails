"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import {
    BarChart3,
    BookOpen,
    GraduationCap,
    Image as ImageIcon,
    KeyRound,
    LayoutDashboard,
    LogOut,
    ReceiptText,
    Send,
    ShieldCheck,
    Users,
} from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
    adminGetCapabilities,
    AdminCapabilities,
    getMe,
    isAuthError,
    logout,
    UserResponse,
} from "@/lib/api"
import { cn } from "@/lib/utils"

const adminNavItems = [
    { href: "/admin", icon: LayoutDashboard, label: "Главная", permissions: ["analytics.read"] },
    { href: "/admin/users", icon: Users, label: "Ученики", permissions: ["users.read"] },
    { href: "/admin/access", icon: KeyRound, label: "Доступы", permissions: ["users.read"] },
    { href: "/admin/orders", icon: ReceiptText, label: "Заказы и оплаты", permissions: ["commerce.read"] },
    { href: "/admin/courses", icon: BookOpen, label: "Курсы и контент", permissions: ["content.manage"] },
    { href: "/admin/landing", icon: ImageIcon, label: "Лендинг и медиа", permissions: ["content.manage"] },
    { href: "/admin/certificates", icon: GraduationCap, label: "Сертификаты", permissions: ["certificates.manage"] },
    { href: "/admin/notifications", icon: Send, label: "Уведомления", permissions: ["notifications.manage"] },
    { href: "/admin/analytics", icon: BarChart3, label: "Аналитика", permissions: ["analytics.read"] },
    { href: "/admin/system", icon: ShieldCheck, label: "Аудит и система", permissions: ["audit.read", "system.manage_roles"] },
]

const adminRouteRules = [
    ...adminNavItems.filter((item) => item.href !== "/admin").map((item) => ({
        matches: (pathname: string) => pathname.startsWith(item.href),
        permissions: item.permissions,
    })),
    {
        matches: (pathname: string) => pathname.startsWith("/admin/purchases"),
        permissions: ["commerce.read"],
    },
    {
        matches: (pathname: string) => pathname === "/admin",
        permissions: ["analytics.read"],
    },
]

const hasAnyPermission = (granted: string[], required: string[]) => (
    granted.includes("*") || required.some((permission) => granted.includes(permission))
)

export default function AdminLayout({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<UserResponse | null>(null)
    const [capabilities, setCapabilities] = useState<AdminCapabilities | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const pathname = usePathname()
    const router = useRouter()

    useEffect(() => {
        const checkAccess = async () => {
            try {
                const [userData, capabilityData] = await Promise.all([getMe(), adminGetCapabilities()])
                if (capabilityData.roles.length === 0 || capabilityData.permissions.length === 0) {
                    router.replace("/dashboard")
                    return
                }
                setUser(userData)
                setCapabilities(capabilityData)
            } catch (error) {
                if (!isAuthError(error)) toast.error("Не удалось проверить права доступа")
                router.replace("/auth/login")
            } finally {
                setIsLoading(false)
            }
        }
        void checkAccess()
    }, [router])

    const hasPermission = (permissions: string[]) => {
        const granted = capabilities?.permissions ?? []
        return hasAnyPermission(granted, permissions)
    }
    const visibleItems = adminNavItems.filter((item) => hasPermission(item.permissions))
    const currentRoute = adminRouteRules.find((rule) => rule.matches(pathname))
    const routeAllowed = !currentRoute || hasPermission(currentRoute.permissions)

    useEffect(() => {
        if (isLoading || !capabilities || routeAllowed) return
        const fallback = adminNavItems.find((item) => hasAnyPermission(capabilities.permissions, item.permissions))
        router.replace(fallback?.href ?? "/dashboard")
    }, [capabilities, isLoading, routeAllowed, router])

    const handleLogout = async () => {
        await logout()
        router.push("/auth/login")
    }

    if (isLoading || !routeAllowed) {
        return <div className="flex min-h-screen items-center justify-center">Проверка доступа…</div>
    }
    if (!user || !capabilities) return null

    const nav = (
        <nav className="flex gap-1 lg:flex-col">
            {visibleItems.map((item) => {
                const active = item.href === "/admin" ? pathname === item.href : pathname.startsWith(item.href)
                return (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={cn(
                            "flex shrink-0 items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                            active ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground",
                        )}
                    >
                        <item.icon className="h-4 w-4" />
                        {item.label}
                    </Link>
                )
            })}
        </nav>
    )

    return (
        <div className="min-h-screen bg-muted/30 lg:flex">
            <aside className="hidden w-72 shrink-0 border-r bg-background lg:flex lg:flex-col">
                <div className="border-b p-5">
                    <Link href="/admin" className="flex items-center gap-3 font-semibold">
                        <span className="rounded-lg bg-primary p-2 text-primary-foreground"><LayoutDashboard className="h-5 w-5" /></span>
                        Lucy Nails · Admin
                    </Link>
                </div>
                <div className="flex-1 overflow-y-auto p-3">{nav}</div>
                <Separator />
                <div className="space-y-3 p-4">
                    <div className="rounded-lg bg-muted p-3 text-sm">
                        <p className="truncate font-medium">{user.email}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{capabilities.roles.join(", ")}</p>
                    </div>
                    <Button variant="outline" className="w-full justify-start" onClick={handleLogout}>
                        <LogOut className="mr-2 h-4 w-4" />Выйти
                    </Button>
                </div>
            </aside>
            <div className="min-w-0 flex-1">
                <header className="sticky top-0 z-20 border-b bg-background/95 px-3 py-2 backdrop-blur lg:hidden">
                    <div className="overflow-x-auto">{nav}</div>
                </header>
                <main>{children}</main>
            </div>
        </div>
    )
}
