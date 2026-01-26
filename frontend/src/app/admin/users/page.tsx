"use client"

import { useEffect, useState } from "react";
import { Loader2, Users as UsersIcon, Key } from "lucide-react";
import { getUsers, getAllCourses, adminGrantAccess, UserResponse, AdminCourseResponse } from "@/lib/api";
import { toast } from "sonner";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

export default function AdminUsersPage() {
    const [users, setUsers] = useState<UserResponse[]>([]);
    const [courses, setCourses] = useState<AdminCourseResponse[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [selectedUser, setSelectedUser] = useState<UserResponse | null>(null);
    const [selectedCourseId, setSelectedCourseId] = useState<string>("");
    const [isGranting, setIsGranting] = useState(false);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [usersData, coursesData] = await Promise.all([
                    getUsers(),
                    getAllCourses(),
                ]);
                setUsers(usersData);
                setCourses(coursesData);
            } catch (error) {
                const errorMessage = error instanceof Error ? error.message : "Ошибка загрузки данных";
                toast.error("Ошибка", {
                    description: errorMessage,
                });
            } finally {
                setIsLoading(false);
            }
        };

        fetchData();
    }, []);

    const handleOpenDialog = (user: UserResponse) => {
        setSelectedUser(user);
        setSelectedCourseId("");
        setIsDialogOpen(true);
    };

    const handleGrantAccess = async () => {
        if (!selectedUser || !selectedCourseId) {
            toast.error("Ошибка", {
                description: "Выберите курс"
            });
            return;
        }

        setIsGranting(true);

        try {
            await adminGrantAccess(selectedUser.id, selectedCourseId);

            toast.success("Доступ выдан!", {
                description: `Пользователь ${selectedUser.email} получил доступ к курсу на 365 дней`
            });

            setIsDialogOpen(false);
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Ошибка выдачи доступа";
            toast.error("Ошибка", {
                description: errorMessage
            });
        } finally {
            setIsGranting(false);
        }
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString("ru-RU", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    };

    return (
        <div className="container px-6 py-8 max-w-7xl">
            <div className="space-y-6">
                {/* Header */}
                <div>
                    <h1 className="text-3xl font-bold text-text-primary flex items-center gap-2">
                        <UsersIcon className="w-8 h-8 text-primary" />
                        Управление пользователями
                    </h1>
                    <p className="text-text-secondary mt-2">
                        Просмотр и управление всеми зарегистрированными пользователями
                    </p>
                </div>

                {/* Content */}
                <Card>
                    <CardHeader>
                        <CardTitle>Все пользователи</CardTitle>
                        <CardDescription>
                            Всего пользователей: {users.length}
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {isLoading ? (
                            <div className="flex items-center justify-center py-12">
                                <div className="text-center space-y-3">
                                    <Loader2 className="w-8 h-8 text-primary animate-spin mx-auto" />
                                    <p className="text-text-secondary text-sm">Загрузка пользователей...</p>
                                </div>
                            </div>
                        ) : users.length > 0 ? (
                            <div className="rounded-md border">
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead className="w-[100px]">ID</TableHead>
                                            <TableHead>Email</TableHead>
                                            <TableHead className="w-[120px]">Роль</TableHead>
                                            <TableHead className="w-[180px]">Дата регистрации</TableHead>
                                            <TableHead className="w-[100px] text-right">Действия</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {users.map((user) => (
                                            <TableRow key={user.id}>
                                                <TableCell className="font-mono text-xs text-text-secondary">
                                                    {user.id.slice(0, 8)}...
                                                </TableCell>
                                                <TableCell className="font-medium">
                                                    {user.email}
                                                </TableCell>
                                                <TableCell>
                                                    <Badge
                                                        variant={user.role === "admin" ? "default" : "secondary"}
                                                    >
                                                        {user.role === "admin" ? "Админ" : "Студент"}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell className="text-text-secondary text-sm">
                                                    {formatDate(user.created_at)}
                                                </TableCell>
                                                <TableCell className="text-right">
                                                    <Dialog open={isDialogOpen && selectedUser?.id === user.id} onOpenChange={(open) => {
                                                        setIsDialogOpen(open);
                                                        if (!open) setSelectedUser(null);
                                                    }}>
                                                        <DialogTrigger asChild>
                                                            <Button
                                                                variant="outline"
                                                                size="sm"
                                                                onClick={() => handleOpenDialog(user)}
                                                                className="gap-2"
                                                            >
                                                                <Key className="w-4 h-4" />
                                                                Доступ
                                                            </Button>
                                                        </DialogTrigger>
                                                        <DialogContent>
                                                            <DialogHeader>
                                                                <DialogTitle>Выдать доступ к курсу</DialogTitle>
                                                                <DialogDescription>
                                                                    Пользователь: <span className="font-medium text-text-primary">{user.email}</span>
                                                                </DialogDescription>
                                                            </DialogHeader>

                                                            <div className="space-y-4 py-4">
                                                                <div className="space-y-2">
                                                                    <label className="text-sm font-medium">
                                                                        Выберите курс
                                                                    </label>
                                                                    <Select
                                                                        value={selectedCourseId}
                                                                        onValueChange={setSelectedCourseId}
                                                                    >
                                                                        <SelectTrigger>
                                                                            <SelectValue placeholder="Выберите курс..." />
                                                                        </SelectTrigger>
                                                                        <SelectContent>
                                                                            {courses.map((course) => (
                                                                                <SelectItem key={course.id} value={course.id}>
                                                                                    {course.title}
                                                                                </SelectItem>
                                                                            ))}
                                                                        </SelectContent>
                                                                    </Select>
                                                                </div>

                                                                <div className="text-sm text-text-secondary bg-primary/5 p-3 rounded-lg">
                                                                    <p className="font-medium text-text-primary mb-1">Условия:</p>
                                                                    <ul className="space-y-1 list-disc list-inside">
                                                                        <li>Доступ: 365 дней</li>
                                                                        <li>Тариф: Self (самостоятельный)</li>
                                                                        <li>Если доступ уже есть - срок будет продлён</li>
                                                                    </ul>
                                                                </div>
                                                            </div>

                                                            <DialogFooter>
                                                                <Button
                                                                    variant="outline"
                                                                    onClick={() => setIsDialogOpen(false)}
                                                                    disabled={isGranting}
                                                                >
                                                                    Отмена
                                                                </Button>
                                                                <Button
                                                                    onClick={handleGrantAccess}
                                                                    disabled={!selectedCourseId || isGranting}
                                                                    className="gap-2"
                                                                >
                                                                    {isGranting && <Loader2 className="w-4 h-4 animate-spin" />}
                                                                    Выдать доступ
                                                                </Button>
                                                            </DialogFooter>
                                                        </DialogContent>
                                                    </Dialog>
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                        ) : (
                            <div className="text-center py-12 text-text-secondary">
                                <UsersIcon className="w-12 h-12 mx-auto mb-3 opacity-20" />
                                <p>Пользователи не найдены</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
