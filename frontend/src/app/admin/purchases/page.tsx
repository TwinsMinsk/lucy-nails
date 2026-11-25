"use client";

import { formatApiDate, parseApiDate } from "@/lib/format";
import { useAdminPermission } from "@/app/admin/permissions";
import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

import { adminGetPurchases, adminRevokeAccess, AdminPurchaseKind, AdminPurchaseResponse, ApiError, PageResponse } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const PAGE_SIZE = 50;
const KIND_LABELS: Record<AdminPurchaseKind, string> = {
    paid: "Оплаты",
    manual: "Ручные выдачи",
    all: "Все записи",
};

const BACKEND_OUTDATED = "сервер ещё не обновлён до новой версии страницы покупок. Обновите страницу после завершения деплоя.";

const isPurchasePage = (value: unknown): value is PageResponse<AdminPurchaseResponse> => (
    typeof value === "object" && value !== null && !Array.isArray(value)
    && Array.isArray((value as { items?: unknown }).items)
    && typeof (value as { total?: unknown }).total === "number"
);

const formatMoney =(kopecks: number) => `${(kopecks / 100).toLocaleString("ru-RU")} ₽`;
const formatDate = formatApiDate;

const isActive = (purchase: AdminPurchaseResponse) =>
    purchase.access_status === "active"
    && Boolean(purchase.access_expires_at)
    && parseApiDate(purchase.access_expires_at as string) > new Date();

export default function AdminPurchasesPage() {
    // The revoke endpoint requires refunds.manage; commerce.read alone only reads.
    const canRevoke = useAdminPermission("refunds.manage");
    const [kind, setKind] = useState<AdminPurchaseKind>("paid");
    const [offset, setOffset] = useState(0);
    const [purchases, setPurchases] = useState<AdminPurchaseResponse[]>([]);
    const [total, setTotal] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    const [loadError, setLoadError] = useState<string | null>(null);
    const [revokingId, setRevokingId] = useState<string | null>(null);
    const generation = useRef(0);

    const load = useCallback(async () => {
        const request = ++generation.current;
        setIsLoading(true);
        setLoadError(null);
        try {
            const page: unknown = await adminGetPurchases({ kind, limit: PAGE_SIZE, offset });
            if (request !== generation.current) return;
            if (!isPurchasePage(page)) {
                setPurchases([]);
                setTotal(0);
                setLoadError(BACKEND_OUTDATED);
                return;
            }
            setPurchases(page.items);
            setTotal(page.total);
        } catch (error) {
            if (request !== generation.current) return;
            // A failed load must not look like "no purchases".
            setPurchases([]);
            setTotal(0);
            // The previous backend has no /admin/purchases/page yet.
            if (error instanceof ApiError && error.status === 404) setLoadError(BACKEND_OUTDATED);
            else setLoadError(error instanceof Error ? error.message : "Попробуйте обновить страницу");
        } finally {
            if (request === generation.current) setIsLoading(false);
        }
    }, [kind, offset]);

    useEffect(() => {
        void load();
        return () => { generation.current += 1; };
    }, [load]);

    const changeKind = (value: AdminPurchaseKind) => { setKind(value); setOffset(0); };

    const handleRevoke = async (purchase: AdminPurchaseResponse) => {
        if (!canRevoke || revokingId) return;
        if (!window.confirm(`Отозвать доступ у ${purchase.user_email || "пользователя"} к «${purchase.course_title || "курсу"}»?`)) {
            return;
        }
        const reason = window.prompt("Укажите причину отзыва доступа")?.trim();
        if (!reason || reason.length < 5) return;
        setRevokingId(purchase.id);
        try {
            await adminRevokeAccess(purchase.id, reason);
            toast.success("Доступ отозван");
            await load();
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
                    Финансовые покупки Prodamus и ручные выдачи с состоянием доступа.
                </p>
            </div>

            <Card>
                <CardHeader className="gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <CardTitle>Покупки и доступы ({total})</CardTitle>
                    <select
                        aria-label="Вид записей"
                        className="rounded-md border p-2 text-sm"
                        value={kind}
                        onChange={(event) => changeKind(event.target.value as AdminPurchaseKind)}
                    >
                        {(Object.keys(KIND_LABELS) as AdminPurchaseKind[]).map((value) => (
                            <option key={value} value={value}>{KIND_LABELS[value]}</option>
                        ))}
                    </select>
                </CardHeader>
                <CardContent>
                    {isLoading ? (
                        <div className="flex items-center justify-center py-16">
                            <Loader2 className="h-8 w-8 animate-spin text-primary" />
                        </div>
                    ) : loadError ? (
                        <div role="alert" className="flex flex-col items-center gap-3 py-10 text-center">
                            <p className="text-sm text-destructive">Не удалось загрузить покупки: {loadError}</p>
                            <Button variant="outline" onClick={() => void load()}>Повторить загрузку</Button>
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
                                        <th className="py-3 pr-4 font-medium">Доступ</th>
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
                                            <td className="py-3 pr-4">
                                                {formatMoney(purchase.amount_kopecks)}
                                                {purchase.kind === "manual" && (
                                                    <div className="text-xs text-text-secondary">ручная выдача</div>
                                                )}
                                            </td>
                                            <td className="py-3 pr-4">
                                                <Badge variant={purchase.payment_status === "success" ? "default" : "secondary"}>
                                                    {purchase.payment_status}
                                                </Badge>
                                            </td>
                                            <td className="py-3 pr-4">
                                                <Badge variant={purchase.access_status === "active" ? "default" : "secondary"}>
                                                    {purchase.access_status}
                                                </Badge>
                                            </td>
                                            <td className="max-w-52 truncate py-3 pr-4 font-mono text-xs text-text-secondary" title={purchase.payment_id || undefined}>
                                                {purchase.payment_id || "—"}
                                            </td>
                                            <td className="py-3 pr-4">{formatDate(purchase.paid_at)}</td>
                                            <td className="py-3 pr-4">{formatDate(purchase.access_expires_at)}</td>
                                            <td className="py-3 pr-4 text-right">
                                                {canRevoke && isActive(purchase) ? (
                                                    <Button
                                                        variant="outline"
                                                        size="sm"
                                                        onClick={() => handleRevoke(purchase)}
                                                        disabled={revokingId !== null}
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
                    <div className="mt-4 flex items-center gap-3">
                        <Button variant="outline" disabled={isLoading || offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>Назад</Button>
                        <span className="text-sm">{total ? offset + 1 : 0}–{Math.min(offset + purchases.length, total)} из {total}</span>
                        <Button variant="outline" disabled={isLoading || offset + PAGE_SIZE >= total} onClick={() => setOffset(offset + PAGE_SIZE)}>Далее</Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
