import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Download, FileText } from "lucide-react";

export default function PrivacyPage() {
    return (
        <div className="container py-12 md:py-24 max-w-4xl mx-auto">
            <Card>
                <CardHeader className="text-center">
                    <CardTitle className="text-3xl font-bold">Политика конфиденциальности</CardTitle>
                    <CardDescription>
                        Документ, определяющий порядок обработки и защиты персональных данных пользователей.
                    </CardDescription>
                </CardHeader>
                <CardContent className="flex flex-col items-center gap-8 py-8">
                    <div className="flex flex-col items-center gap-4 text-center text-muted-foreground p-8 border rounded-lg bg-muted/20 w-full">
                        <FileText className="h-16 w-16 text-primary/60" />
                        <div className="space-y-2">
                            <p className="max-w-[600px]">
                                Полный текст политики конфиденциальности доступен для скачивания в формате DOCX.
                            </p>
                            <p className="text-sm">
                                Мы бережно относимся к вашим данным и соблюдаем все требования законодательства.
                            </p>
                        </div>
                    </div>

                    <div className="flex justify-center">
                        <a href="/legal/privacy-policy.docx" download="privacy-policy.docx">
                            <Button size="lg" className="gap-2">
                                <Download className="h-4 w-4" />
                                Скачать документ (DOCX)
                            </Button>
                        </a>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
