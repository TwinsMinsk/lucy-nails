"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

import { adminGetPurchases, adminRevokeAccess, AdminPurchaseResponse } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const formatMoney = (kopecks: number) => `${(kopecks / 100).toLocaleString("ru-RU")} ₽`;
const formatDate = (date: string | null | undefined) => (
    date ? new Date(date).toLocaleDateString("ru-RU") : "—"
);

const isActive = (purchase: AdminPurchaseResponse) =>
    purchase.payment_status === "success" && new Date(purchase.expires_at) > new Date();

export default function AdminPurchasesPage() {
    const [purchases, setPurchases] = useState<AdminPurchaseResponse[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [revokingId, setRevokingId] = useState<string | null>(null);

    useEffect(() => {
        const loadPurchases = async () => {
            try {
                setPurchases(await adminGetPurchases());
            } catch (error) {
                toast.error("Не удалось загрузить покупки", {
                    description: error instanceof Error ? error.message : "Попробуйте обновить страницу",
                });
            } finally {
                setIsLoading(false);
            }
        };

        loadPurchases();
    }, []);

    const handleRevoke = async (purchase: AdminPurchaseResponse) => {
        if (!window.confirm(`Отозвать доступ у ${purchase.user_email || "пользователя"} к «${purchase.course_title || "курсу"}»?`)) {
            return;
        }
        setRevokingId(purchase.id);
        try {
            const result = await adminRevokeAccess(purchase.id);
            setPurchases((prev) =>
                prev.map((p) =>
                    p.id === purchase.id
                        ? { ...p, payment_status: result.payment_status as AdminPurchaseResponse["payment_status"], expires_at: new Date().toISOString() }
                        : p
                )
            );
            toast.success("Доступ отозван");
        } catch (error) {
            toast.error("Не удалось отозвать доступ", {
                description: error instanceof Error ? error.message : "Попробуйте ещё раз",
            });
        } finally {
            setRevokingId(null);
        }
    };

    return (
        <div className="container px-6 py-8 space-y-6">
            <div>
                <h1 className="text-3xl font-bold mb-2">Управление покупками</h1>
                <p className="text-text-secondary">
                    Последние 200 записей: оплаты Prodamus, ручные выдачи доступа и сроки окончания.
                </p>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Покупки и доступы</CardTitle>
                </CardHeader>
                <CardContent>
                    {isLoading ? (
                        <div className="flex items-center justify-center py-16">
                            <Loader2 className="h-8 w-8 animate-spin text-primary" />
                        </div>
                    ) : purchases.length === 0 ? (
                        <p className="py-10 text-center text-text-secondary">Покупок пока нет.</p>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b text-left text-text-secondary">
                                        <th className="py-3 pr-4 font-medium">Пользователь</th>
                                        <th className="py-3 pr-4 font-medium">Курс</th>
                                        <th className="py-3 pr-4 font-medium">Тариф</th>
                                        <th className="py-3 pr-4 font-medium">Сумма</th>
                                        <th className="py-3 pr-4 font-medium">Статус</th>
                                        <th className="py-3 pr-4 font-medium">ID платежа</th>
                                        <th className="py-3 pr-4 font-medium">Оплачено</th>
                                        <th className="py-3 pr-4 font-medium">Доступ до</th>
                                        <th className="py-3 pr-4 font-medium text-right">Действия</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {purchases.map((purchase) => (
                                        <tr key={purchase.id} className="border-b last:border-0">
                                            <td className="py-3 pr-4">
                                                <div className="font-medium">{purchase.user_email || "—"}</div>
                                                {purchase.customer_phone && (
                                                    <div className="text-xs text-text-secondary">{purchase.customer_phone}</div>
                                                )}
                                            </td>
                                            <td className="py-3 pr-4">{purchase.course_title || "—"}</td>
                                            <td className="py-3 pr-4">
                                                {purchase.tariff === "support" ? "С поддержкой" : "Самостоятельный"}
                                            </td>
                                            <td className="py-3 pr-4">{formatMoney(purchase.amount_kopecks)}</td>
                                            <td className="py-3 pr-4">
                                                <Badge variant={purchase.payment_status === "success" ? "default" : "secondary"}>
                                                    {purchase.payment_status}
                                                </Badge>
                                            </td>
                                            <td className="max-w-52 truncate py-3 pr-4 font-mono text-xs text-text-secondary" title={purchase.payment_id || undefined}>
                                                {purchase.payment_id || "—"}
                                            </td>
                                            <td className="py-3 pr-4">{formatDate(purchase.paid_at)}</td>
                                            <td className="py-3 pr-4">{formatDate(purchase.expires_at)}</td>
                                            <td className="py-3 pr-4 text-right">
                                                {isActive(purchase) ? (
                                                    <Button
                                                        variant="outline"
                                                        size="sm"
                                                        onClick={() => handleRevoke(purchase)}
                                                        disabled={revokingId === purchase.id}
                                                    >
                                                        {revokingId === purchase.id && (
                                                            <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                                                        )}
                                                        Отозвать
                                                    </Button>
                                                ) : (
                                                    <span className="text-text-secondary">—</span>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
