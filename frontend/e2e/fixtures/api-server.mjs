import { createServer } from "node:http"

const course = {
    id: "11111111-1111-4111-8111-111111111101",
    title: "Nail Design PRO — Playwright",
    price_self: 7200,
    access_days: 45,
    lessons_count: 0,
    total_duration: 0,
}

createServer((request, response) => {
    response.setHeader("Content-Type", "application/json")
    response.setHeader("Access-Control-Allow-Origin", "http://127.0.0.1:3015")
    response.setHeader("Access-Control-Allow-Credentials", "true")
    response.setHeader("Cache-Control", "no-store")
    if (request.method === "GET" && request.url === "/health") {
        response.end(JSON.stringify({ status: "ok" }))
    } else if (request.method === "GET" && request.url === "/api/landing") {
        response.end(JSON.stringify({ course_id: course.id, course, hero: { landing_title: course.title }, modules: [], gallery: [] }))
    } else {
        response.writeHead(503)
        response.end(JSON.stringify({ detail: "Not provided by the isolated Playwright fixture" }))
    }
}).listen(3016, "127.0.0.1")
