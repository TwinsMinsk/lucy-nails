# Quick Test Guide: Kinescope Video Player

## Быстрый старт

### 1. Запустить оба сервера

```powershell
# Terminal 1 - Backend
.\scripts\dev.ps1

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### 2. Проверить что серверы запущены

- **Backend:** http://localhost:8000/docs
- **Frontend:** http://localhost:3000

---

## Тестовые сценарии

### ✅ Сценарий 1: Видео без авторизации (401)

**Ожидаемый результат:** Ошибка авторизации

**Шаги:**
1. Открой в браузере любой URL урока напрямую (без логина):
   ```
   http://localhost:3000/courses/test-id/lessons/test-lesson-id
   ```
2. **Увидишь:** Ошибку или редирект на логин (зависит от реализации auth middleware)

---

### ✅ Сценарий 2: Preview урок (успех)

**Ожидаемый результат:** YouTube видео загружается

**Шаги:**
1. **Авторизуйся** на сайте или используй существующую сессию
2. Найди урок с `is_preview=true` в seed данных
3. Открой этот урок
4. **Увидишь:**
   - Спиннер (1-2 сек)
   - YouTube iframe с видео

---

### ✅ Сценарий 3: Платный урок без покупки (403)

**Ожидаемый результат:** Красивая ошибка с замком

**Шаги:**
1. Авторизуйся как обычный пользователь (не админ)
2. Открой урок с `is_preview=false` из курса, который ты НЕ купил
3. **Увидишь:**
   - Спиннер
   - Экран с иконкой замка
   - Текст: "Доступ ограничен"
   - Подсказка о покупке курса

---

### ✅ Сценарий 4: Несуществующий урок (404)

**Ожидаемый результат:** Ошибка "не найдено"

**Шаги:**
1. Открой URL с fake UUID:
   ```
   http://localhost:3000/courses/xxx/lessons/00000000-0000-0000-0000-000000000000
   ```
2. **Увидишь:**
   - Спиннер
   - Экран с иконкой ошибки
   - Текст ошибки от API

---

## Mock-режим проверка

### Backend Mock-режим активен?

```powershell
# Проверь переменную окружения
echo $env:KINESCOPE_API_KEY
# Должно быть пусто
```

### Какое видео показывается?

В Mock-режиме всегда:
```
https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=0
```

Это безопасное YouTube видео для тестирования плеера.

---

## Developer Tools (Chrome)

### Network Tab

1. Открой DevTools (F12)
2. Перейди во вкладку **Network**
3. Загрузи страницу урока
4. Найди запрос: `GET /api/lessons/{id}/play`
5. Проверь:
   - **Status:** 200 (success) или 403 (access denied)
   - **Headers:** Есть ли `Authorization: Bearer ...`
   - **Response:**
     ```json
     {
       "video_url": "...",
       "provider": "kinescope",
       "title": "..."
     }
     ```

### Console

Проверь ошибки в консоли:
```javascript
// Не должно быть ошибок типа:
// - CORS error
// - Failed to fetch
// - 401 Unauthorized (если залогинен)
```

---

## Responsive тестирование

### Desktop (1920x1080)
- VideoPlayer занимает полную ширину
- Aspect ratio 16:9
- Sidebar справа на больших экранах

### Tablet (768px)
- Плеер адаптируется
- Sidebar может скрываться

### Mobile (375px)
- Плеер на всю ширину экрана
- Кнопки навигации адаптивны

---

## Troubleshooting

### Проблема: "Failed to fetch"

**Возможные причины:**
1. Backend не запущен
2. CORS не настроен
3. Неверный `NEXT_PUBLIC_API_URL`

**Решение:**
```powershell
# 1. Проверь backend
curl http://localhost:8000/docs

# 2. Проверь .env.local
cat frontend\.env.local
# Должно быть: NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

### Проблема: Бесконечный спиннер

**Причины:**
1. API не отвечает
2. JavaScript ошибка в консоли
3. Неверный lessonId

**Решение:**
1. Открой Network tab и проверь статус запроса
2. Открой Console и проверь ошибки
3. Проверь что lessonId существует в БД

### Проблема: 401 Unauthorized

**Причины:**
1. Токен не сохранен в localStorage
2. Токен истек
3. Пользователь не залогинен

**Решение:**
```javascript
// В Console браузера:
localStorage.getItem('access_token')
// Должен вернуть JWT токен (длинная строка)

// Если пусто - нужно залогиниться
```

---

## Production Testing (будущее)

Когда будет деплой на Railway:

1. Обнови `.env.local`:
   ```env
   NEXT_PUBLIC_API_URL=https://api.lucysmirnova.ru/api
   ```

2. Обнови `KINESCOPE_API_KEY` на сервере (реальный ключ)

3. Проверь:
   - CORS настроен для `https://lucysmirnova.ru`
   - SSL сертификаты валидны
   - Watermark отображается на видео (email пользователя)

---

## Checklist перед релизом

- [ ] Mock-режим работает локально
- [ ] Production режим работает с реальным Kinescope API
- [ ] Все 4 состояния VideoPlayer отображаются корректно
- [ ] Responsive на всех устройствах
- [ ] Нет ошибок в Console
- [ ] Токен авторизации сохраняется
- [ ] 403 ошибка показывает красивый UI
- [ ] Iframe разрешает fullscreen

---

## Полезные команды

```powershell
# Перезапустить frontend
cd frontend
npm run dev

# Очистить кеш Next.js
rm -r .next
npm run dev

# Проверить переменные окружения
cat .env.local

# Проверить localStorage в браузере (Console)
localStorage.getItem('access_token')
```

---

**Готово к тестированию!** 🚀
