import type { Metadata } from "next";
import { Inter, Playfair_Display } from "next/font/google"; // 1. Import Playfair
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";
// 1. Импортируем компоненты (убедись, что пути правильные)
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { getPublicSiteUrl } from "@/lib/env";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin", "cyrillic"],
});

const playfair = Playfair_Display({ // 2. Configure Playfair
  variable: "--font-serif",
  subsets: ["latin", "cyrillic"],
});

const siteUrl = getPublicSiteUrl();

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Обучающие курсы по маникюру от Люси Смирновой",
    template: "%s — Lucy Nails Academy",
  },
  description: "Авторские онлайн-курсы маникюра и дизайна ногтей с защищёнными видео-уроками.",
  openGraph: {
    type: "website",
    locale: "ru_RU",
    url: siteUrl,
    siteName: "Lucy Nails Academy",
    title: "Обучающие курсы по маникюру от Люси Смирновой",
    description: "Авторские онлайн-курсы маникюра и дизайна ногтей с защищёнными видео-уроками.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Обучающие курсы по маникюру от Люси Смирновой",
    description: "Авторские онлайн-курсы маникюра и дизайна ногтей с защищёнными видео-уроками.",
  },
  icons: {
    icon: "/icon.svg",
    shortcut: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body
        className={`${inter.variable} ${playfair.variable} antialiased min-h-screen flex flex-col bg-background text-foreground`}
      >
        {/* 2. Добавляем Header сверху */}
        <Header />

        {/* 3. Оборачиваем контент в main с flex-1, чтобы он занимал всё свободное место */}
        <main className="flex-1">
          {children}
        </main>

        {/* 4. Добавляем Footer снизу */}
        <Footer />
        <Toaster />
      </body>
    </html>
  );
}