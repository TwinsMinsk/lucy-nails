"use client"

import { useEffect, useState } from "react"

import { adminGetCapabilities, UserResponse } from "@/lib/api"

/**
 * Permissions that open each admin section, in navigation order. The admin
 * layout guards routes with this map; the header and dashboard use it to link
 * only where the user may go.
 */
export const ADMIN_ROUTE_PERMISSIONS: Record<string, string[]> = {
    "/admin": ["analytics.read"],
    "/admin/users": ["users.read"],
    "/admin/access": ["users.read"],
    "/admin/orders": ["commerce.read"],
    "/admin/courses": ["content.manage"],
    "/admin/landing": ["content.manage"],
    "/admin/ads": ["ads.read"],
    "/admin/certificates": ["certificates.manage"],
    "/admin/notifications": ["notifications.manage"],
    "/admin/analytics": ["analytics.read"],
    "/admin/system": ["audit.read", "system.manage_roles"],
}

export const hasAnyPermission = (granted: string[], required: string[]) => (
    granted.includes("*") || required.some((permission) => granted.includes(permission))
)

export const canOpenAdminRoute = (granted: string[], href: string) => (
    hasAnyPermission(granted, ADMIN_ROUTE_PERMISSIONS[href] ?? [])
)

/** First admin page these permissions open, or null without admin access. */
export function firstAdminRoute(granted: string[]): string | null {
    return Object.keys(ADMIN_ROUTE_PERMISSIONS).find((href) => canOpenAdminRoute(granted, href)) ?? null
}

/** Link target for the signed-in user's admin entry, from their team capabilities. */
export function useAdminEntry(user: UserResponse | null): string | null {
    const [entry, setEntry] = useState<{ userId: string; href: string | null } | null>(null)
    const userId = user?.id ?? null
    useEffect(() => {
        if (!userId) return
        let current = true
        adminGetCapabilities()
            .then((capabilities) => {
                if (!current) return
                const allowed = capabilities.roles.length > 0 && capabilities.permissions.length > 0
                setEntry({ userId, href: allowed ? firstAdminRoute(capabilities.permissions) : null })
            })
            .catch(() => { if (current) setEntry({ userId, href: null }) })
        return () => { current = false }
    }, [userId])
    return entry && entry.userId === userId ? entry.href : null
}
