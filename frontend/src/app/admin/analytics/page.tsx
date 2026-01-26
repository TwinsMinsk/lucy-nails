"use client"

import { useEffect, useState } from "react";
import { Loader2, Users, BookOpen, ShoppingCart, TrendingUp, DollarSign, UserPlus } from "lucide-react";
import { adminGetAnalytics, AnalyticsResponse } from "@/lib/api";
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function AdminAnalyticsPage() {
    const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchAnalytics = async () => {
            try {
                const data = await adminGetAnalytics();
                setAnalytics(data);
            } catch (error) {
                const errorMessage = error instanceof Error ? error.message : "Ошибка загрузки";
                toast.error("Ошибка", { description: errorMessage });
            } finally {
                setIsLoading(false);
            }
        };

        fetchAnalytics();
    }, []);

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <Loader2 className="w-8 h-8 text-primary animate-spin" />
            </div>
        );
    }

    if (!analytics) {
        return (
            <div className="container px-6 py-8 text-center">
                <p className="text-text-secondary">Ошибка загрузки аналитики</p>
            </div>
        );
    }

    const stats = [
        {
            title: "Всего пользователей",
            value: analytics.total_users,
            icon: Users,
            description: `+${analytics.recent_registrations} за 30 дней`,
            color: "text-blue-500",
            bgColor: "bg-blue-500/10",
        },
        {
            title: "Курсов",
            value: analytics.total_courses,
            icon: BookOpen,
            description: "Активных курсов",
            color: "text-purple-500",
            bgColor: "bg-purple-500/10",
        },
        {
            title: "Покупок",
            value: analytics.total_purchases,
            icon: ShoppingCart,
            description: `+${analytics.recent_purchases} за 30 дней`,
            color: "text-green-500",
            bgColor: "bg-green-500/10",
        },
        {
            title: "Выручка",
            value: `${analytics.total_revenue.toLocaleString('ru-RU')} ₽`,
            icon: DollarSign,
            description: "Общая сумма",
            color: "text-amber-500",
            bgColor: "bg-amber-500/10",
        },
    ];

    return (
        <div className="container px-6 py-8 max-w-6xl">
            <div className="space-y-6">
                {/* Header */}
                <div>
                    <h1 className="text-3xl font-bold text-text-primary flex items-center gap-2">
                        <TrendingUp className="w-8 h-8 text-primary" />
                        Аналитика
                    </h1>
                    <p className="text-text-secondary mt-2">
                        Обзор ключевых показателей платформы
                    </p>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {stats.map((stat, index) => (
                        <Card key={index} className="relative overflow-hidden">
                            <CardHeader className="flex flex-row items-center justify-between pb-2">
                                <CardTitle className="text-sm font-medium text-text-secondary">
                                    {stat.title}
                                </CardTitle>
                                <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                                    <stat.icon className={`w-4 h-4 ${stat.color}`} />
                                </div>
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{stat.value}</div>
                                <p className="text-xs text-text-secondary mt-1">
                                    {stat.description}
                                </p>
                            </CardContent>
                        </Card>
                    ))}
                </div>

                {/* Recent Activity */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <UserPlus className="w-5 h-5 text-primary" />
                                Регистрации (30 дней)
                            </CardTitle>
                            <CardDescription>
                                Новые пользователи за последний месяц
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="text-4xl font-bold text-primary">
                                {analytics.recent_registrations}
                            </div>
                            <p className="text-sm text-text-secondary mt-2">
                                {analytics.total_users > 0
                                    ? `${Math.round((analytics.recent_registrations / analytics.total_users) * 100)}% от общего числа`
                                    : "Нет данных"}
                            </p>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <ShoppingCart className="w-5 h-5 text-primary" />
                                Покупки (30 дней)
                            </CardTitle>
                            <CardDescription>
                                Успешные покупки за последний месяц
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="text-4xl font-bold text-green-500">
                                {analytics.recent_purchases}
                            </div>
                            <p className="text-sm text-text-secondary mt-2">
                                {analytics.total_purchases > 0
                                    ? `${Math.round((analytics.recent_purchases / analytics.total_purchases) * 100)}% от всех покупок`
                                    : "Нет данных"}
                            </p>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
