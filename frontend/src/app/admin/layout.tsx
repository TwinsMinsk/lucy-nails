"use client"

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Users, BookOpen, ShoppingCart, LayoutDashboard, LogOut, BarChart3 } from "lucide-react";
import { getMe, isAuthError, UserResponse, logout } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

const adminNavItems = [
    { href: "/admin/users", icon: Users, label: "Пользователи" },
    { href: "/admin/courses", icon: BookOpen, label: "Курсы" },
    { href: "/admin/purchases", icon: ShoppingCart, label: "Покупки" },
    { href: "/admin/analytics", icon: BarChart3, label: "Аналитика" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<UserResponse | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        const checkAdminAccess = async () => {
            try {
                const userData = await getMe();

                if (userData.role !== "admin") {
                    toast.error("Доступ запрещён", {
                        description: "У вас нет прав для доступа к админ-панели"
                    });
                    router.push("/dashboard");
                    return;
                }

                setUser(userData);
            } catch (error) {
                if (!isAuthError(error)) {
                    toast.error("Ошибка", {
                        description: "Не удалось проверить права доступа"
                    });
                }
                router.push("/auth/login");
            } finally {
                setIsLoading(false);
            }
        };

        checkAdminAccess();
    }, [router]);

    const handleLogout = async () => {
        await logout();
        toast.success("Вы вышли из системы");
        router.push("/auth/login");
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
                    <p className="mt-4 text-text-secondary">Проверка доступа...</p>
                </div>
            </div>
        );
    }

    if (!user || user.role !== "admin") {
        return null;
    }

    return (
        <div className="flex min-h-screen">
            {/* Sidebar */}
            <aside className="w-64 bg-surface border-r border-border flex flex-col">
                {/* Header */}
                <div className="p-6 border-b border-border">
                    <Link href="/admin/users" className="flex items-center gap-2 group">
                        <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center group-hover:scale-105 transition-transform">
                            <LayoutDashboard className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h1 className="font-bold text-lg text-text-primary">Админ-панель</h1>
                            <p className="text-xs text-text-secondary">Управление</p>
                        </div>
                    </Link>
                </div>

                {/* Navigation */}
                <nav className="flex-1 p-4 space-y-1">
                    {adminNavItems.map((item) => (
                        <Link
                            key={item.href}
                            href={item.href}
                            className="flex items-center gap-3 px-4 py-3 rounded-lg text-text-secondary hover:bg-primary/10 hover:text-primary transition-colors"
                        >
                            <item.icon className="w-5 h-5" />
                            <span className="font-medium">{item.label}</span>
                        </Link>
                    ))}
                </nav>

                <Separator />

                {/* User Info & Logout */}
                <div className="p-4 space-y-3">
                    <div className="px-4 py-2 bg-primary/5 rounded-lg">
                        <p className="text-xs text-text-secondary uppercase tracking-wider mb-1">Администратор</p>
                        <p className="text-sm font-medium text-text-primary truncate">{user.email}</p>
                    </div>

                    <Button
                        variant="outline"
                        className="w-full justify-start gap-2"
                        onClick={handleLogout}
                    >
                        <LogOut className="w-4 h-4" />
                        Выйти
                    </Button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-y-auto bg-background">
                {children}
            </main>
        </div>
    );
}
