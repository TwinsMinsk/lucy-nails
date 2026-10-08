"use client"

import { createContext, useContext } from "react"

export const AdminPermissionsContext = createContext<string[]>([])

export function useAdminPermission(permission: string) {
    const permissions = useContext(AdminPermissionsContext)
    return permissions.includes("*") || permissions.includes(permission)
}
