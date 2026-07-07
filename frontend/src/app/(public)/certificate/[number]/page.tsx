import Link from "next/link";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { BadgeCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { CertificateActions } from "@/components/certificate/CertificateActions";
import { verifyCertificate } from "@/lib/api";

export async function generateMetadata({
    params,
}: {
    params: Promise<{ number: string }>;
}): Promise<Metadata> {
    const { number } = await params;
    const cert = await verifyCertificate(number);

    if (!cert) {
        return {
            title: "Сертификат не найден",
            robots: { index: false },
        };
    }

    const title = `Сертификат ${cert.student_name}`;
    const description = `Подтверждённый сертификат о прохождении курса «${cert.course_title}» в Lucy Nails Academy. № ${cert.certificate_number}.`;
    const url = `/certificate/${cert.certificate_number}`;
    const ogImages = cert.png_url
        ? [{ url: cert.png_url, width: 3508, height: 2480, alt: title }]
        : undefined;

    return {
        title,
        description,
        alternates: { canonical: url },
        openGraph: {
            title,
            description,
            url,
            ...(ogImages ? { images: ogImages } : {}),
        },
        twitter: {
            card: "summary_large_image",
            ...(ogImages ? { images: ogImages } : {}),
        },
    };
}

export default async function CertificatePage({
    params,
}: {
    params: Promise<{ number: string }>;
}) {
    const { number } = await params;
    const cert = await verifyCertificate(number);

    if (!cert) {
        notFound();
    }

    const issuedDate = new Date(cert.issued_at).toLocaleDateString("ru-RU", {
        day: "numeric",
        month: "long",
        year: "numeric",
    });

    return (
        <div className="min-h-screen bg-background pb-20">
            {/* Hero band */}
            <div className="bg-[#fff1f4] border-b border-[#db3f6e]/10 py-12 md:py-16 text-center">
                <p className="text-xs tracking-[0.3em] uppercase text-[#b02a52]">
                    LUCY NAILS ACADEMY
                </p>
                <h1 className="mt-3 font-serif text-3xl md:text-4xl text-text-primary">
                    Сертификат о прохождении курса
                </h1>
            </div>

            <div className="max-w-3xl mx-auto px-4 py-12 space-y-8">
                {/* Trust pill row */}
                <div className="flex flex-wrap items-center justify-center gap-3">
                    <span className="inline-flex items-center gap-2 rounded-full bg-success/10 text-success border border-success/30 px-4 py-2 text-sm font-medium">
                        <BadgeCheck className="h-4 w-4" />
                        Сертификат подтверждён
                    </span>
                    <span className="font-mono text-sm text-text-secondary">
                        № {cert.certificate_number}
                    </span>
                </div>

                {/* Certificate image */}
                {cert.png_url && (
                    <a
                        href={cert.png_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block p-2 bg-white rounded-2xl border border-[#D4AF37]/40 shadow-2xl"
                    >
                        {/* eslint-disable-next-line @next/next/no-img-element -- remote certificate storage URL, no next/image remote pattern configured */}
                        <img
                            src={cert.png_url}
                            alt={`Сертификат ${cert.student_name}`}
                            className="w-full rounded-xl"
                        />
                    </a>
                )}

                {/* Details card */}
                <Card>
                    <CardContent>
                        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-5">
                            <div>
                                <dt className="text-xs uppercase tracking-wide text-text-secondary">
                                    Студентка
                                </dt>
                                <dd className="mt-1 font-medium text-text-primary">
                                    {cert.student_name}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs uppercase tracking-wide text-text-secondary">
                                    Курс
                                </dt>
                                <dd className="mt-1 font-medium text-text-primary">
                                    {cert.course_title}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs uppercase tracking-wide text-text-secondary">
                                    Дата выдачи
                                </dt>
                                <dd className="mt-1 font-medium text-text-primary">{issuedDate}</dd>
                            </div>
                            <div>
                                <dt className="text-xs uppercase tracking-wide text-text-secondary">
                                    Номер
                                </dt>
                                <dd className="mt-1 font-mono font-medium text-text-primary">
                                    {cert.certificate_number}
                                </dd>
                            </div>
                        </dl>
                    </CardContent>
                </Card>

                <CertificateActions certificateNumber={cert.certificate_number} />

                {/* Marketing CTA */}
                <div className="bg-[#fff1f4] rounded-3xl p-8 text-center space-y-4">
                    <h2 className="font-serif text-2xl text-text-primary">Хотите так же?</h2>
                    <p className="text-[#666]">
                        Пройдите курс «{cert.course_title}» в Lucy Nails Academy
                    </p>
                    <Button
                        asChild
                        className="rounded-full bg-gradient-to-r from-[#db3f6e] to-[#b02a52] text-white"
                    >
                        <Link href={`/courses/${cert.course_id}`}>Пройти этот курс →</Link>
                    </Button>
                </div>
            </div>
        </div>
    );
}
