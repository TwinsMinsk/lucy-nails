"use client"

import { useState, useEffect } from "react";
import Link from "next/link";
import { Menu, User, LogIn, LogOut, BookOpen } from "lucide-react"; // Import LogOut and BookOpen correct
import { Button } from "@/components/ui/button";
import {
    Sheet,
    SheetContent,
    SheetTrigger,
    SheetHeader,
    SheetTitle,
} from "@/components/ui/sheet";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { usePathname, useRouter } from "next/navigation";
import { getMe, logout, UserResponse } from "@/lib/api";

export function Header() {
    const pathname = usePathname();
    const router = useRouter();
    const [mounted, setMounted] = useState(false);
    const [user, setUser] = useState<UserResponse | null>(null);

    // Determines if we are on the landing page
    const isLanding = pathname === "/";

    // Define links based on context
    const landingLinks = [
        { href: "#about", label: "О курсе" },
        { href: "#modules", label: "Программа" },
        { href: "#pricing", label: "Тарифы" },
        { href: "#reviews", label: "Отзывы" },
    ];

    const dashboardLinks = [
        { href: "/dashboard", label: "Мои курсы" },
    ];

    const navLinks = isLanding ? landingLinks : (user ? dashboardLinks : landingLinks);

    // Hydration fix & Auth check
    useEffect(() => {
        setMounted(true);
        const checkAuth = async () => {
            try {
                const userData = await getMe();
                setUser(userData);
            } catch (e) {
                // Token invalid or expired
                setUser(null);
            }
        };
        checkAuth();
    }, [pathname]);

    const handleLogout = async () => {
        await logout();
        setUser(null);
        router.push("/");
        router.refresh();
    };

    // Smooth scroll handler for anchor links
    const handleScroll = (e: React.MouseEvent<HTMLAnchorElement, MouseEvent>, href: string) => {
        if (href.startsWith("#")) {
            e.preventDefault();
            const targetId = href.replace("#", "");
            const elem = document.getElementById(targetId);
            elem?.scrollIntoView({
                behavior: "smooth",
            });
            // Update URL hash without scroll jump (optional)
            window.history.pushState({}, "", href);
        }
    };

    return (
        <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="container flex h-16 items-center justify-between px-4 md:px-6">

                {/* Logo */}
                <div className="flex items-center gap-6">
                    <Link href="/" className="flex items-center gap-2">
                        <span className="text-xl font-bold text-[#db3f6e] tracking-tight font-serif">
                            Lucy Smirnova
                        </span>
                    </Link>
                </div>

                {/* Desktop Navigation (Centered) */}
                <nav className="hidden md:flex items-center gap-8 absolute left-1/2 -translate-x-1/2">
                    {navLinks.map((link) => (
                        <Link
                            key={link.href}
                            href={link.href}
                            onClick={(e) => isLanding ? handleScroll(e, link.href) : undefined}
                            className="text-sm font-medium text-text-secondary hover:text-primary transition-colors"
                        >
                            {link.label}
                        </Link>
                    ))}
                </nav>

                {/* Right Side: Auth/User */}
                <div className="flex items-center gap-4">
                    <div className="hidden md:flex">
                        {user ? (
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button variant="ghost" className="relative h-9 w-9 rounded-full">
                                        <Avatar className="h-9 w-9 border-2 border-[#D4AF37]">
                                            <AvatarFallback className="bg-white text-black font-bold">
                                                {user.email[0].toUpperCase()}
                                            </AvatarFallback>
                                        </Avatar>
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent className="w-56" align="end" forceMount>
                                    <DropdownMenuLabel className="font-normal">
                                        <div className="flex flex-col space-y-1">
                                            <p className="text-sm font-medium leading-none">{user.role === 'admin' ? 'Администратор' : 'Студент'}</p>
                                            <p className="text-xs leading-none text-muted-foreground">
                                                {user.email}
                                            </p>
                                        </div>
                                    </DropdownMenuLabel>
                                    <DropdownMenuSeparator />
                                    {user.role === 'admin' && (
                                        <DropdownMenuItem asChild>
                                            <Link href="/admin/courses" className="cursor-pointer">
                                                <User className="mr-2 h-4 w-4" />
                                                <span>Админ панель</span>
                                            </Link>
                                        </DropdownMenuItem>
                                    )}
                                    <DropdownMenuItem asChild>
                                        <Link href="/dashboard" className="cursor-pointer">
                                            <BookOpen className="mr-2 h-4 w-4" />
                                            <span>Мои курсы</span>
                                        </Link>
                                    </DropdownMenuItem>
                                    <DropdownMenuItem asChild>
                                        <Link href="/profile" className="cursor-pointer">
                                            <User className="mr-2 h-4 w-4" />
                                            <span>Профиль</span>
                                        </Link>
                                    </DropdownMenuItem>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem onClick={handleLogout} className="cursor-pointer text-destructive focus:text-destructive">
                                        <LogOut className="mr-2 h-4 w-4" />
                                        <span>Выйти</span>
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        ) : (
                            <div className="flex gap-2">
                                <Button asChild variant="ghost" size="sm">
                                    <Link href="/auth/login">
                                        Войти
                                    </Link>
                                </Button>
                                <Button asChild size="sm" className="rounded-full px-6 bg-[#db3f6e] hover:bg-[#db3f6e]/90 text-white border-none shadow-md transition-all hover:scale-105 active:scale-95">
                                    <Link href="/#pricing">
                                        Купить курс
                                    </Link>
                                </Button>
                            </div>
                        )}
                    </div>

                    {/* Mobile Menu */}
                    {mounted && (
                        <Sheet>
                            <SheetTrigger asChild>
                                <Button variant="ghost" size="icon" className="md:hidden">
                                    <Menu className="h-5 w-5" />
                                    <span className="sr-only">Меню</span>
                                </Button>
                            </SheetTrigger>
                            <SheetContent side="right">
                                <SheetHeader>
                                    <SheetTitle className="text-left font-serif text-xl text-[#db3f6e]">Lucy Smirnova</SheetTitle>
                                </SheetHeader>
                                <div className="flex flex-col gap-6 mt-8">
                                    <nav className="flex flex-col gap-4">
                                        {navLinks.map((link) => (
                                            <Link
                                                key={link.href}
                                                href={link.href}
                                                onClick={(e) => isLanding ? handleScroll(e, link.href) : undefined}
                                                className="text-lg font-medium hover:text-primary transition-colors"
                                            >
                                                {link.label}
                                            </Link>
                                        ))}
                                    </nav>

                                    <div className="border-t pt-6">
                                        {user ? (
                                            <div className="flex flex-col gap-4">
                                                <div className="flex items-center gap-3">
                                                    <Avatar className="h-10 w-10 border-2 border-[#D4AF37]">
                                                        <AvatarFallback className="bg-white text-black font-bold">{user.email[0].toUpperCase()}</AvatarFallback>
                                                    </Avatar>
                                                    <div className="flex flex-col">
                                                        <span className="font-medium text-sm text-black">{user.role === 'admin' ? 'Админ' : 'Студент'}</span>
                                                        <span className="text-xs text-muted-foreground">{user.email}</span>
                                                    </div>
                                                </div>
                                                {user.role === 'admin' && (
                                                    <Link
                                                        href="/admin/courses"
                                                        className="flex items-center gap-2 text-base font-medium hover:text-primary transition-colors"
                                                    >
                                                        <User className="h-4 w-4" />
                                                        Админ панель
                                                    </Link>
                                                )}
                                                <Link
                                                    href="/dashboard"
                                                    className="flex items-center gap-2 text-base font-medium hover:text-primary transition-colors"
                                                >
                                                    <BookOpen className="h-4 w-4" />
                                                    Мои курсы
                                                </Link>
                                                <Link
                                                    href="/profile"
                                                    className="flex items-center gap-2 text-base font-medium hover:text-primary transition-colors"
                                                >
                                                    <User className="h-4 w-4" />
                                                    Профиль
                                                </Link>
                                                <button
                                                    onClick={handleLogout}
                                                    className="flex items-center gap-2 text-base font-medium text-destructive hover:text-destructive/80 transition-colors text-left"
                                                >
                                                    <LogOut className="h-4 w-4" />
                                                    Выйти
                                                </button>
                                            </div>
                                        ) : (
                                            <div className="flex flex-col gap-3">
                                                <Button asChild className="w-full" size="lg">
                                                    <Link href="/auth/login">Войти</Link>
                                                </Button>
                                                <Button asChild className="w-full bg-[#db3f6e] hover:bg-[#db3f6e]/90 text-white border-none" size="lg">
                                                    <Link href="/#pricing">Купить курс</Link>
                                                </Button>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </SheetContent>
                        </Sheet>
                    )}
                </div>
            </div>
        </header>
    );
}
