"use client";
import { useEffect } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import Link from "@tiptap/extension-link";
import Placeholder from "@tiptap/extension-placeholder";
import {
    Bold,
    Italic,
    Underline as UnderlineIcon,
    List,
    ListOrdered,
    Heading1,
    Heading2,
    Quote,
    Undo,
    Redo,
    Link as LinkIcon
} from "lucide-react";
import { Button } from "./button";
import { cn } from "@/lib/utils";

interface EditorProps {
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
    className?: string;
}

const Toolbar = ({ editor }: { editor: any }) => {
    if (!editor) return null;

    const handleAction = (e: React.MouseEvent, action: () => void) => {
        e.preventDefault();
        e.stopPropagation();
        action();
    };

    return (
        <div className="flex flex-wrap items-center gap-1 p-1 border-b bg-muted/50 rounded-t-lg">
            <Button
                variant="ghost"
                size="sm"
                onMouseDown={(e) => e.preventDefault()}
                onClick={(e) => handleAction(e, () => editor.chain().focus().toggleBold().run())}
                className={cn(editor.isActive("bold") && "bg-muted-foreground/20")}
                type="button"
            >
                <Bold className="h-4 w-4" />
            </Button>
            <Button
                variant="ghost"
                size="sm"
                onMouseDown={(e) => e.preventDefault()}
                onClick={(e) => handleAction(e, () => editor.chain().focus().toggleItalic().run())}
                className={cn(editor.isActive("italic") && "bg-muted-foreground/20")}
                type="button"
            >
                <Italic className="h-4 w-4" />
            </Button>
            <Button
                variant="ghost"
                size="sm"
                onMouseDown={(e) => e.preventDefault()}
                onClick={(e) => handleAction(e, () => editor.chain().focus().toggleUnderline().run())}
                className={cn(editor.isActive("underline") && "bg-muted-foreground/20")}
                type="button"
            >
                <UnderlineIcon className="h-4 w-4" />
            </Button>
            <div className="w-[1px] h-4 bg-border mx-1" />
            <Button
                variant="ghost"
                size="sm"
                onMouseDown={(e) => e.preventDefault()}
                onClick={(e) => handleAction(e, () => editor.chain().focus().toggleHeading({ level: 1 }).run())}
                className={cn(editor.isActive("heading", { level: 1 }) && "bg-muted-foreground/20")}
                type="button"
            >
                <Heading1 className="h-4 w-4" />
            </Button>
            <Button
                variant="ghost"
                size="sm"
                onMouseDown={(e) => e.preventDefault()}
                onClick={(e) => handleAction(e, () => editor.chain().focus().toggleHeading({ level: 2 }).run())}
                className={cn(editor.isActive("heading", { level: 2 }) && "bg-muted-foreground/20")}
                type="button"
            >
                <Heading2 className="h-4 w-4" />
            </Button>
            <div className="w-[1px] h-4 bg-border mx-1" />
            <Button
                variant="ghost"
                size="sm"
                onMouseDown={(e) => e.preventDefault()}
                onClick={(e) => handleAction(e, () => editor.chain().focus().toggleBulletList().run())}
                className={cn(editor.isActive("bulletList") && "bg-muted-foreground/20")}
                type="button"
            >
                <List className="h-4 w-4" />
            </Button>
            <Button
                variant="ghost"
                size="sm"
                onMouseDown={(e) => e.preventDefault()}
                onClick={(e) => handleAction(e, () => editor.chain().focus().toggleOrderedList().run())}
                className={cn(editor.isActive("orderedList") && "bg-muted-foreground/20")}
                type="button"
            >
                <ListOrdered className="h-4 w-4" />
            </Button>
            <Button
                variant="ghost"
                size="sm"
                onMouseDown={(e) => e.preventDefault()}
                onClick={(e) => handleAction(e, () => editor.chain().focus().toggleBlockquote().run())}
                className={cn(editor.isActive("blockquote") && "bg-muted-foreground/20")}
                type="button"
            >
                <Quote className="h-4 w-4" />
            </Button>
            <div className="w-[1px] h-4 bg-border mx-1" />
            <Button
                variant="ghost"
                size="sm"
                onMouseDown={(e) => e.preventDefault()}
                onClick={(e) => handleAction(e, () => editor.chain().focus().undo().run())}
                disabled={!editor.can().undo()}
                type="button"
            >
                <Undo className="h-4 w-4" />
            </Button>
            <Button
                variant="ghost"
                size="sm"
                onMouseDown={(e) => e.preventDefault()}
                onClick={(e) => handleAction(e, () => editor.chain().focus().redo().run())}
                disabled={!editor.can().redo()}
                type="button"
            >
                <Redo className="h-4 w-4" />
            </Button>
        </div>
    );
};

export function Editor({ value, onChange, placeholder, className }: EditorProps) {
    const editor = useEditor({
        extensions: [
            StarterKit,
            Underline,
            Link.configure({
                openOnClick: false,
                HTMLAttributes: {
                    class: 'text-primary underline decoration-primary/50 hover:decoration-primary',
                },
            }),
            Placeholder.configure({
                placeholder: placeholder || "Начните писать...",
            }),
        ],
        editorProps: {
            attributes: {
                class: cn(
                    "prose prose-sm dark:prose-invert max-w-none min-h-[150px] p-4 focus:outline-none",
                    className
                ),
            },
        },
        immediatelyRender: false,
        onUpdate: ({ editor }) => {
            onChange(editor.getHTML());
        },
    });

    // Sync external value with editor content
    useEffect(() => {
        if (editor && value !== editor.getHTML()) {
            editor.commands.setContent(value);
        }
    }, [editor, value]);

    return (
        <div className="flex flex-col border rounded-lg focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 bg-background">
            <Toolbar editor={editor} />
            <EditorContent editor={editor} />
        </div>
    );
}
