import type { Metadata } from "next";

// Auth pages are client components and cannot export metadata themselves.
export const metadata: Metadata = {
    title: "Личный кабинет",
    robots: { index: false, follow: true },
};

export default function AuthLayout({ children }: { children: React.ReactNode }) {
    return children;
}
