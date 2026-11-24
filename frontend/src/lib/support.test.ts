import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { SUPPORT_BOT_FALLBACK_USERNAME, supportBotUrl, supportBotUsername } from "@/lib/support"

beforeEach(() => vi.stubEnv("NEXT_PUBLIC_SUPPORT_BOT_USERNAME", ""))
afterEach(() => vi.unstubAllEnvs())

it("falls back to the school bot when nothing is configured", () => {
    expect(SUPPORT_BOT_FALLBACK_USERNAME).toBe("lucynails_bot")
    expect(supportBotUrl()).toBe("https://t.me/lucynails_bot")
})

it("uses the configured username, with or without @", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPPORT_BOT_USERNAME", "@school_help_bot")
    expect(supportBotUsername()).toBe("school_help_bot")
    vi.stubEnv("NEXT_PUBLIC_SUPPORT_BOT_USERNAME", " school_help_bot ")
    expect(supportBotUrl()).toBe("https://t.me/school_help_bot")
})

it("ignores a username Telegram would not accept", () => {
    for (const value of ["bad name", "abc", "evil.com/x", "a".repeat(33)]) {
        vi.stubEnv("NEXT_PUBLIC_SUPPORT_BOT_USERNAME", value)
        expect(supportBotUrl()).toBe("https://t.me/lucynails_bot")
    }
})

it("adds a valid start parameter", () => {
    expect(supportBotUrl("o_AbC-123_xyz")).toBe("https://t.me/lucynails_bot?start=o_AbC-123_xyz")
})

it("drops a start parameter Telegram would reject", () => {
    for (const value of [null, undefined, "", "o_bad param", "o_<script>", "a".repeat(65)]) {
        expect(supportBotUrl(value)).toBe("https://t.me/lucynails_bot")
    }
})
