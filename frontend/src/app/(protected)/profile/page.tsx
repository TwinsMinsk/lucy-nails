"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getMe, isAuthError, logout, UserResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { BookOpen, Loader2, LogOut, User } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";

export default function ProfilePage() {
    const router = useRouter();
    const [user, setUser] = useState<UserResponse | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchProfile = async () => {
            try {
                const userData = await getMe();
                setUser(userData);
            } catch (error) {
                if (!isAuthError(error)) {
                    toast.error("Ошибка загрузки профиля");
                }
                router.push("/auth/login");
            } finally {
                setIsLoading(false);
            }
        };

        fetchProfile();
    }, [router]);

    const handleLogout = async () => {
        try {
            await logout();
            router.push("/");
            router.refresh();
        } catch {
            toast.error("Ошибка при выходе");
        }
    };

    if (isLoading) {
        return (
            <div className="flex justify-center items-center min-h-[50vh]">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    if (!user) return null;

    return (
        <div className="container max-w-lg py-12">
            <Card className="w-full shadow-lg border-primary/10">
                <CardHeader className="text-center pb-2">
                    <div className="mx-auto bg-primary/10 p-4 rounded-full w-fit mb-4">
                        <User className="w-10 h-10 text-primary" />
                    </div>
                    <CardTitle className="text-2xl font-serif text-text-primary">Профиль пользователя</CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                    <div className="space-y-2">
                        <Label htmlFor="email" className="text-text-secondary">Email</Label>
                        <Input
                            id="email"
                            value={user.email}
                            readOnly
                            disabled
                            className="bg-muted/30 border-primary/20 text-text-primary h-12"
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="role" className="text-text-secondary">Роль</Label>
                        <Input
                            id="role"
                            value={user.role === 'admin' ? 'Администратор' : 'Студент'}
                            readOnly
                            disabled
                            className="bg-muted/30 border-primary/20 text-text-primary h-12"
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="created_at" className="text-text-secondary">Дата регистрации</Label>
                        <Input
                            id="created_at"
                            value={new Date(user.created_at).toLocaleDateString('ru-RU')}
                            readOnly
                            disabled
                            className="bg-muted/30 border-primary/20 text-text-primary h-12"
                        />
                    </div>
                </CardContent>
                <CardFooter className="pt-2 flex flex-col gap-3">
                    <Button asChild className="w-full gap-2 h-12 text-base rounded-full bg-gradient-to-r from-[#db3f6e] to-[#b02a52] text-white">
                        <Link href="/dashboard">
                            <BookOpen className="w-5 h-5" />
                            Перейти к моим курсам
                        </Link>
                    </Button>
                    <div className="rounded-2xl bg-[#fff1f4] p-4 text-sm text-text-secondary leading-relaxed">
                        Если вы оплатили курс без регистрации, используйте email и пароль из письма.
                        Доступ обычно появляется в кабинете в течение пары минут после оплаты.
                    </div>
                    <Button
                        variant="destructive"
                        className="w-full gap-2 h-12 text-base"
                        onClick={handleLogout}
                    >
                        <LogOut className="w-5 h-5" />
                        Выйти
                    </Button>
                </CardFooter>
            </Card>
        </div>
    );
}
