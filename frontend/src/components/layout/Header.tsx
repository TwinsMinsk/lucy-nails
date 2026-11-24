"use client"

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { Menu, User, LogOut, BookOpen, ShieldCheck, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    Sheet,
    SheetClose,
    SheetContent,
    SheetDescription,
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
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { usePathname, useRouter } from "next/navigation";
import { toast } from "sonner";
import { getMe, logout, UserResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

// Shared look of a tappable row in the mobile drawer: 48px tall, text sits on the 20px inset.
const drawerRowClass =
    "flex min-h-12 w-full items-center gap-3 rounded-xl px-2 text-left font-medium text-text-primary transition-colors hover:bg-primary/5 hover:text-primary active:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export function Header() {
    const pathname = usePathname();
    const router = useRouter();
    const [mounted, setMounted] = useState(false);
    const [user, setUser] = useState<UserResponse | null>(null);
    const [menuOpen, setMenuOpen] = useState(false);
    const [loggingOut, setLoggingOut] = useState(false);
    // Anchor picked in the drawer; scrolled to once the drawer has closed and released the scroll lock.
    const pendingHashRef = useRef<string | null>(null);
    const pendingScrollTimerRef = useRef<number | null>(null);

    // Determines if we are on the landing page
    const isLanding = pathname === "/";

    // Define links based on context. The "/" prefix keeps them working outside the landing page.
    const landingLinks = [
        { href: "/#about", label: "О курсе" },
        { href: "/#program", label: "Программа" },
        { href: "/#gallery", label: "Галерея" },
        { href: "/#pricing", label: "Стоимость" },
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
            } catch {
                // Token invalid or expired
                setUser(null);
            }
        };
        checkAuth();
    }, [pathname]);

    // A new page (link, Back/Forward) closes the drawer and drops an anchor scroll meant for the old page.
    useEffect(() => {
        setMenuOpen(false);
        pendingHashRef.current = null;
        if (pendingScrollTimerRef.current !== null) {
            window.clearTimeout(pendingScrollTimerRef.current);
            pendingScrollTimerRef.current = null;
        }
    }, [pathname]);

    // Back/Forward between entries of the same page (hash changes) does not change the pathname.
    useEffect(() => {
        if (!menuOpen) return;
        const closeMenu = () => setMenuOpen(false);
        window.addEventListener("popstate", closeMenu);
        return () => window.removeEventListener("popstate", closeMenu);
    }, [menuOpen]);

    // Returns false when the server did not end the session: the user stays signed in and can retry.
    const handleLogout = async (): Promise<boolean> => {
        if (loggingOut) return false;
        setLoggingOut(true);
        try {
            await logout();
        } catch {
            toast.error("Не удалось выйти. Проверьте подключение к интернету и попробуйте ещё раз.");
            return false;
        } finally {
            setLoggingOut(false);
        }
        setUser(null);
        router.push("/");
        router.refresh();
        return true;
    };

    const scrollToHash = (hash: string) => {
        const elem = document.getElementById(hash.slice(1));
        elem?.scrollIntoView({
            behavior: "smooth",
        });
        // Update URL hash without scroll jump (optional)
        window.history.pushState({}, "", hash);
    };

    // Smooth scroll handler for anchor links
    const handleScroll = (e: React.MouseEvent<HTMLAnchorElement, MouseEvent>, href: string) => {
        const hashIndex = href.indexOf("#");
        if (hashIndex !== -1) {
            e.preventDefault();
            scrollToHash(href.slice(hashIndex));
        }
    };

    // Drawer links always close the drawer; on the landing page anchors scroll after it has closed.
    const handleDrawerLink = (e: React.MouseEvent<HTMLAnchorElement, MouseEvent>, href: string) => {
        const hashIndex = href.indexOf("#");
        if (isLanding && hashIndex !== -1) {
            e.preventDefault();
            pendingHashRef.current = href.slice(hashIndex);
        }
        setMenuOpen(false);
    };

    const handleDrawerCloseAutoFocus = () => {
        const hash = pendingHashRef.current;
        if (!hash) return;
        pendingHashRef.current = null;
        // Wait a tick so the dialog has removed its body scroll lock.
        pendingScrollTimerRef.current = window.setTimeout(() => {
            pendingScrollTimerRef.current = null;
            scrollToHash(hash);
        }, 0);
    };

    // The drawer stays open on failure so the retry is one tap away; the toast explains what happened.
    const handleDrawerLogout = async () => {
        if (await handleLogout()) setMenuOpen(false);
    };

    const accountLinks = [
        { href: "/dashboard", label: "Мои курсы", icon: BookOpen },
        { href: "/profile", label: "Профиль", icon: User },
        ...(user?.role === "admin" ? [{ href: "/admin/courses", label: "Админ панель", icon: ShieldCheck }] : []),
    ];
    // Outside the landing page the main nav already holds "Мои курсы": do not list it twice.
    const drawerAccountLinks = accountLinks.filter((link) => !navLinks.some((nav) => nav.href === link.href));

    return (
        <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="container flex h-16 items-center justify-between px-4 md:px-6">

                {/* Logo */}
                <div className="flex items-center gap-6">
                    <Link href="/" className="flex items-center gap-2">
                        <span className="text-xl font-bold text-primary tracking-tight font-serif">
                            Lucy Smirnova
                        </span>
                    </Link>
                </div>

                {/* Desktop Navigation (Centered). From lg only: on tablets the centred links ran into the logo and the buttons */}
                <nav className="hidden lg:flex items-center gap-8 absolute left-1/2 -translate-x-1/2">
                    {navLinks.map((link) => (
                        <Link
                            key={link.href}
                            href={link.href}
                            onClick={(e) => isLanding ? handleScroll(e, link.href) : undefined}
                            className="text-sm font-medium text-text-secondary hover:text-foreground transition-colors"
                        >
                            {link.label}
                        </Link>
                    ))}
                </nav>

                {/* Right Side: Auth/User */}
                <div className="flex items-center gap-4">
                    <div className="hidden lg:flex">
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
                                            <p className="ym-hide-content text-xs leading-none text-muted-foreground">
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
                                <Button asChild size="sm" className="rounded-full px-6 shadow-md">
                                    <Link href="/#pricing">
                                        Купить курс
                                    </Link>
                                </Button>
                            </div>
                        )}
                    </div>

                    {/* Mobile Menu */}
                    {mounted && (
                        <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
                            <SheetTrigger asChild>
                                <Button variant="ghost" size="icon" className="-mr-3 size-11 lg:hidden">
                                    <Menu className="size-6" />
                                    <span className="sr-only">Меню</span>
                                </Button>
                            </SheetTrigger>
                            <SheetContent
                                side="right"
                                showCloseButton={false}
                                onCloseAutoFocus={handleDrawerCloseAutoFocus}
                                className="w-[85%] max-w-[22rem] gap-0 overflow-y-auto sm:max-w-[22rem]"
                            >
                                {/* Same 64px height and 20px inset as the site header bar */}
                                <SheetHeader className="h-16 shrink-0 flex-row items-center justify-between gap-0 border-b border-border px-5 py-0">
                                    <SheetTitle className="font-serif text-xl font-bold tracking-tight text-primary">
                                        Lucy Smirnova
                                    </SheetTitle>
                                    <SheetClose className="-mr-3 inline-flex size-11 shrink-0 items-center justify-center rounded-full text-text-secondary transition-colors hover:bg-primary/5 hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                                        <X className="size-6" aria-hidden="true" />
                                        <span className="sr-only">Закрыть меню</span>
                                    </SheetClose>
                                </SheetHeader>
                                <SheetDescription className="sr-only">Разделы сайта и личный кабинет</SheetDescription>

                                {navLinks.length > 0 && (
                                    <nav aria-label="Разделы сайта" className="flex flex-col gap-1 px-3 pt-4 pb-6">
                                        {navLinks.map((link) => {
                                            const isCurrent = !link.href.includes("#") && pathname === link.href;
                                            return (
                                                <Link
                                                    key={link.href}
                                                    href={link.href}
                                                    onClick={(e) => handleDrawerLink(e, link.href)}
                                                    aria-current={isCurrent ? "page" : undefined}
                                                    className={cn(drawerRowClass, "font-serif text-xl", isCurrent && "text-primary")}
                                                >
                                                    {link.label}
                                                </Link>
                                            );
                                        })}
                                    </nav>
                                )}

                                {/* Actions stay at the bottom, above the home indicator on iPhone */}
                                <div className="mt-auto px-5 pb-[calc(1.5rem+env(safe-area-inset-bottom))]">
                                    <div className="border-t border-border pt-5">
                                        {user ? (
                                            <div className="flex flex-col">
                                                <div className="flex items-center gap-3 pb-3">
                                                    <Avatar className="h-10 w-10 border-2 border-[#D4AF37]">
                                                        <AvatarFallback className="bg-white text-black font-bold">{user.email[0].toUpperCase()}</AvatarFallback>
                                                    </Avatar>
                                                    <div className="flex min-w-0 flex-col">
                                                        <span className="text-sm font-medium text-text-primary">{user.role === 'admin' ? 'Администратор' : 'Студент'}</span>
                                                        <span className="ym-hide-content truncate text-xs text-text-secondary">{user.email}</span>
                                                    </div>
                                                </div>
                                                <div className="-mx-2 flex flex-col">
                                                    {drawerAccountLinks.map(({ href, label, icon: Icon }) => (
                                                        <Link
                                                            key={href}
                                                            href={href}
                                                            onClick={(e) => handleDrawerLink(e, href)}
                                                            className={cn(drawerRowClass, "text-base")}
                                                        >
                                                            <Icon className="size-5 text-text-secondary" aria-hidden="true" />
                                                            {label}
                                                        </Link>
                                                    ))}
                                                    <button
                                                        type="button"
                                                        onClick={handleDrawerLogout}
                                                        disabled={loggingOut}
                                                        aria-busy={loggingOut || undefined}
                                                        className={cn(drawerRowClass, "text-base text-destructive hover:bg-destructive/5 hover:text-destructive active:bg-destructive/10 disabled:opacity-60")}
                                                    >
                                                        <LogOut className="size-5" aria-hidden="true" />
                                                        Выйти
                                                    </button>
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="flex flex-col gap-3">
                                                <Button asChild size="lg" className="h-12 w-full rounded-full text-base shadow-md">
                                                    <Link href="/#pricing" onClick={(e) => handleDrawerLink(e, "/#pricing")}>
                                                        Купить курс
                                                    </Link>
                                                </Button>
                                                <Button asChild variant="outline" size="lg" className="h-12 w-full rounded-full text-base">
                                                    <Link href="/auth/login" onClick={(e) => handleDrawerLink(e, "/auth/login")}>
                                                        Войти
                                                    </Link>
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
