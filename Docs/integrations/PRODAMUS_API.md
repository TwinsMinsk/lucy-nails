# https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/deaktivaciya-i-povtornaya-aktivaciya-podpiski

Если подписка была деактивирована менеджером или пользователем, будут отправлены следующие типы уведомлений:

- веб-хук на URL адрес, указанный на странице настроек платежной формы, в блоке “Настройка уведомлений”

- e-mail уведомление на адреса менеджеров, указанных на странице настроек подписок, в блоке “Общие настройки”


При этом, если подписка была повторно активирована менеджером или пользователем до наступления следующей плановой даты списания, будут отправлены те же типы уведомлений с данными о повторной активации подписки.

**Пример URL уведомления о деактивации подписки:**

Copy

```
$_POST = Array
(
    [date] => 2024-09-01T00:00:00+03:00
    [order_id] => 0
    [order_num] => 9999999999
    [domain] => testingqa.payform.ru
    [sum] => 50.00
    [currency] => rub
    [customer_phone] => +79999999997
    [customer_email] => test.subscribtion@prodamus.ru
    [customer_extra] =>
    [payment_type] => Автоплатеж
    [attempt] => 1
    [discount_value] => 0.00
    [subscription] => Array
        (
            [type] => action
            [action_code] => deactivation
            [action_reason] => deactivated
            [date] => 2024-08-28 15:14
            [id] => 1000000
            [active] => 1
            [active_manager] => 1
            [active_user] => 1
            [cost] => 50.00
            [name] => Тестовая подписка
            [limit_autopayments] => 3
            [autopayments_num] => 0
            [first_payment_discount] => 0.00
            [next_payment_discount] => 0.00
            [next_payment_discount_num] =>
            [date_create] => 2024-09-01 00:00:42
            [date_first_payment] => 2024-09-01 00:00:42
            [date_last_payment] => 2024-09-01 00:00:42
            [date_next_payment] => 2024-10-27 00:00:42
            [date_next_payment_discount] =>2024-09-01 00:00:42
            [current_attempt] => 1
            [payment_num] => 1
            [autopayment] => 1
        )

)
```

**Пример URL уведомления о повторной активации подписки:**

Copy

```
$_POST = Array
(
    [date] => 2024-09-01T00:00:00+03:00
    [order_id] => 0
    [order_num] => 9999999999
    [domain] => testingqa.payform.ru
    [sum] => 50.00
    [currency] => rub
    [customer_phone] => +79999999997
    [customer_email] => test.subscribtion@prodamus.ru
    [customer_extra] =>
    [payment_type] => Автоплатеж
    [attempt] => 1
    [discount_value] => 0.00
    [subscription] => Array
        (
            [type] => action
            [action_code] => reactivation
            [action_reason] => reactivated
            [date] => 2024-09-01 00:00
            [id] => 1000000
            [active] => 0
            [active_manager] => 0
            [active_user] => 1
            [cost] => 50.00
            [name] => Тестовая подписка
            [limit_autopayments] => 3
            [autopayments_num] => 0
            [first_payment_discount] => 0.00
            [next_payment_discount] => 0.00
            [next_payment_discount_num] =>
            [date_create] =>2024-09-01 15:08:42
            [date_first_payment] => 2024-09-01 00:00:42
            [date_last_payment] => 2024-09-01 00:00:42
            [date_next_payment] => 2024-10-27 00:00:42
            [date_next_payment_discount] => 2024-09-01 00:00:42
            [current_attempt] => 1
            [payment_num] => 1
            [autopayment] => 1
        )

)
```

circle-info

Подробное описание параметров описано в разделе [Параметры URL-уведомления по подпискеarrow-up-right](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/uvedomleniya)

circle-info

Информация носит исключительно справочный характер и не является офертой. С актуальной редакцией оферты и тарифами Вы можете ознакомиться в разделе " [Документыarrow-up-right](https://prodamus.ru/documents)".

[PreviousУведомления при автосписанииchevron-left](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/uvedomleniya-pri-avtospisanii) [NextПараметры URL-уведомления по подпискеchevron-right](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/uvedomleniya)

Last updated 2 days ago

This site uses cookies to deliver its service and to analyze traffic. By browsing this site, you accept the [privacy policy](https://policies.gitbook.com/privacy/cookies).

close

AcceptReject

---

# https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/uvedomleniya

URL-уведомления по подпискам отличаются от уведомлений по обычным платежам только наличием блока subscription

Все параметры кроме subscription описаны в разделе [Уведомления](https://help.prodamus.ru/payform/uvedomleniya)

Описание параметров subscription:

Параметр

Описание

type

тип уведомления

**action** \- действие

**notification** \- уведомление

action\_code

действие может принимать значение

**auto\_payment**\- автосписание

**deactivation** \- деактивация подписки

**finish** \- завершение подписки

notification\_code

уведомление может принимать значение

**auto\_payment**\- автосписание

**auto\_payment\_reminder** \- уведомление об автосписании

error\_code

код ошибки

см. [Коды ошибок](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/kody-oshibok)

error

текст ошибки

last\_attempt

признак была ли данная попытка списания последней

**yes** \- последняя попытка

**no** \- будет предпринята повторная попытка списания

payment\_date

дата попытки платежа

id

ID подписки

profile\_id

ID профиля подписавшегося в системе Продамус

active

активность подписки

active\_manager

статус активности подписки (управляется менеджером)

active\_user

статус активности подписки (управляется пользователем)

cost

стоимость подписки без учета скидок

name

название подписки

limit\_autopayments

максимальное количество автосписаний

autopayments\_num

количество совершенных автосписаний

first\_payment\_discount

сумма скидка на первый платеж

next\_payment\_discount

сумма скидка на следующий платеж

next\_payment\_discount\_num

количество следующих платежей, на которые действует скидка

date\_create

дата оформления подписки

date\_first\_payment

дата первой оплаты

date\_last\_payment

дата последней фактической оплаты

date\_next\_payment

дата следующего платежа

date\_next\_payment\_discount

дата определения суммы скидки следующего платежа

payment\_num

количество оплат всего

current\_attempt

номер попытки автосписания

max\_attempts

максимальное количество попыток списания

autopayment

признак авто-платежа

**0** \- покупка

**1** \- автосписание

circle-info

Информация носит исключительно справочный характер и не является офертой. С актуальной редакцией оферты и тарифами Вы можете ознакомиться в разделе " [Документыarrow-up-right](https://prodamus.ru/documents)".

[PreviousДеактивация и повторная активация подпискиchevron-left](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/deaktivaciya-i-povtornaya-aktivaciya-podpiski) [NextКоды ошибокchevron-right](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/kody-oshibok)

Last updated 2 days ago

This site uses cookies to deliver its service and to analyze traffic. By browsing this site, you accept the [privacy policy](https://policies.gitbook.com/privacy/cookies).

close

AcceptReject

---

# https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov

- [URL-адрес и секретный ключ](https://help.prodamus.ru/payform/integracii/rest-api/url-dlya-uvedomlenii-i-sekretnyi-klyuch)

- [Параметры для запросовarrow-up-right](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov#parametry-kotorye-vy-mozhete-peredat-v-zaprose)

- [Ссылка на оплату](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov#formiruem-zapros)

- [Пример программного кода формирования ссылки на оплату](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov#primer-programmnogo-koda-formirovaniya-ssylki-dlya-demo-formy)

- [Проверка успешной интеграции](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov#proverka-uspeshnoi-integracii)


### [hashtag](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov\#formiruem-zapros)    Формируем запрос

Для формирования платежной ссылки вам необходимо отправить GET или POST запрос себе на платежную страницу

Где прописать URL-адрес и скопировать секретный ключ подробно в разделе ["Где найти url для уведомлений и секретный ключ"](https://help.prodamus.ru/payform/integracii/rest-api/url-dlya-uvedomlenii-i-sekretnyi-klyuch)

В зависимости от сервиса, с которым вы интегрируетесь, вы можете прописывать параметры платежной страницы отдельно, передавая их программным кодом или использую стандартные команды вашего сервиса ( _например Автопилот или SmartSender_) либо в самой ссылке Get-запроса.

Для формирования GET или POST запроса вам потребуется:

- check



URL-адрес платежной формы в системе Продамус. По сути это адрес из адресной строки вашей платежной страницы


> ссылка должна быть вида http://название\_поддомена.payform.ru/
>
> _Например https://demo.payform.ru/_

### [hashtag](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov\#parametry-kotorye-vy-mozhete-peredat-v-zaprose)    Параметры, которые вы можете передать в запросе

#### [hashtag](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov\#obyazatelnye-parametry-pri-formirovanii-ssylki)    Обязательные параметры при формировании ссылки

Параметр

Тип

Описание

do

строка

[может принимать значения](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov#vozmozhnye-znacheniya-parametra-do)

products

массив

товары ( [перейти к описанию параметров массива `products`](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov#parametry-massiva-products))

sys

строка

Параметр SYS — это код вашей интеграции ( **его нужно согласовать с** [**поддержкой Prodamus** arrow-up-right](https://max.ru/id1215156909_2_bot)). По нему система определяет интеграцию. У всех клиентов в рамках одной интеграции должен быть один и тот же SYS.

#### [hashtag](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov\#vozmozhnye-znacheniya-parametra-do)    Возможные значения параметра `do`

1. "link" - возвращает ссылку, которую отправляем пользователю для самостоятельного перехода на страницу оплаты

2. "pay" - отправляет покупателя сразу на оплату. Используется для интернет-магазинов действие "Оплата"


#### [hashtag](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov\#parametry-massiva-products)    Параметры массива `products`

Параметр

 -

Тип

Описание

Обязательный

name

 -

строка

наименование товара

ДА

price

 -

число

цена товара

ДА

quantity

 -

целое число

количество товара

ДА

sku

 -

строка

id товара в системе интернет-магазин

НЕТ

type

- course - Доступ к курсу

- service - Услуга

- goods - Товар


строка

Категория товара

НЕТ

> Чтобы прописать параметры массива: **наименование, цена и количество товара**, необходимо обратиться в глубь массива `products
> Например``products[0]name` для php

**Параметры продукта, являются НЕобязательными**

Параметр

Тип

Описание

order\_sum

число

сумма заказа

discount\_value

число

размер скидки в рублях

#### [hashtag](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov\#undefined)

#### [hashtag](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov\#parametry-dlya-rekurrentnykh-platezhei)    Параметры для рекуррентных платежей

Параметр

Тип

Описание

Обязательный

subscription

целое число

id подписки

**ДА**

subscription\_date\_start

строка

дата начала подписки в формате "гггг-мм-дд чч:мм"

P.S. Если указать дату в прошлом, то старт подписки будет сдвинут на интервал этой подписки.

нет

subscription\_demo\_period

целое число

количество дней демо-периода подписки

нет

subscription\_limit\_autopayments

целое число

максимальное количество авто-платежей по подписке

если не указано или меньше единицы, значение будет взято из настроек подписного товара

нет

**Параметры для пользователей Вк, являются НЕобязательными**

Параметр

Тип

Описание

vk\_user\_id

целое число

id пользователя в системе Вк

vk\_user\_name

строка

ФИО пользователя в системе Вк

#### [hashtag](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov\#parametry-peredayushie-dannye-o-yur.statuse-platelshika)    Параметры передающие данные о юр.статусе плательщика

Параметр

Тип

Описание

npd\_income\_type

строка

тип плательщика, с возможными значениями:

**FROM\_INDIVIDUAL** \- физическое лицо

**FROM\_LEGAL\_ENTITY** \- юридическое лицо

**FROM\_FOREIGN\_AGENCY** \- иностранная организация

значение по умолчанию: **FROM\_INDIVIDUAL**

npd\_income\_inn

целое число

инн плательщика

**обязательно, если форма работает в режиме самозанятого и тип плательщика FROM\_LEGAL\_ENTITY**

npd\_income\_company

строка

название компании плательщика

**обязательно, если форма в режиме самозанятого и тип плательщика FROM\_LEGAL\_ENTITY или FROM\_FOREIGN\_AGENCY**

#### [hashtag](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov\#obshie-neobyazatelnye-parametry)    Общие Н **еобязательные параметры**

Параметр

Тип

Описание

order\_id

строка

номер заказа в Вашей системе

customer\_phone

строка

номер телефона клиента (обязательный к заполнению при оплате, [подробнее о параметре `customer_phone`](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov#parametr-customer_phone))

customer\_email

строка

e-mail адрес клиента

customer\_extra

строка

описание заказа (Поле дополнительные данные)

ref

строка

идентификатор партнера (ПРОМОКОД)

paid\_content

строка

платный контент

link\_expired

строка

срок действия ссылки в формате "дд.мм.гггг чч:мм"

payment\_method

строка

метод оплаты, выбранный клиентом, если есть возможность выбора на стороне интернет-магазина, иначе клиент выбирает метод оплаты на стороне платежной формы

доступные значения:

**AC** \- оплата картой, выпущенной в РФ

**ACkz** \- оплата картой Казахстана

**ACf** \- оплата картами стран СНГ, кроме РФ

**ACUSDGTL** \- Оплата в USD картой всех стран, кроме РФ

**ACEURGTL** \- Оплата в EUR картой всех стран, кроме РФ

**ACBYNGTL** \- Оплата в BYN оплата картой Беларуси

**ACUSDKB**\- Оплата в USD Карты банков мира кроме России
**ACEURKB** \- Оплата в EUR Карты банков мира кроме России

**SBP** \- Быстрый платёж, без ввода данных карты. Для карт РФ

**sbol** \- Сбербанк онлайн **invoice** \- Оплата по счету

**tpay -** Оплата через Т-Банк без ввода данных карты

**fresh\_installment\_0\_0\_6** — Рассрочка от Фреш Кредит на 6 месяцев
**fresh\_installment\_0\_0\_10** — Рассрочка от Фреш Кредит на 10 месяцев
**fresh\_installment\_0\_0\_12** — Рассрочка от Фреш Кредит на 12 месяцев
**fresh\_installment\_0\_0\_18** — Рассрочка от Фреш Кредит на 18 месяцев
**fresh\_installment\_0\_0\_24** — Рассрочка от Фреш Кредит на 24 месяца
**fresh\_installment\_0\_0\_36** — Рассрочка от Фреш Кредит на 36 месяцев

**dolyame:installment** — Оплата долями от Т-банка

**proonline\_installment\_rb\_0\_0\_6** — Рассрочка от Про-онлайн в РБ на 6 месяцев
**proonline\_installment\_rb\_0\_0\_12** — Рассрочка от Про-онлайн в РБ на 12 месяцев
**proonline\_installment\_rb\_0\_0\_18** — Рассрочка от Про-онлайн в РБ на 18 месяцев
**proonline\_installment\_rb\_0\_0\_24** — Рассрочка от Про-онлайн в РБ на 24 месяца

**proonline\_installment\_kz\_0\_0\_6** — Рассрочка от Про-онлайн в КЗ на 6 месяцев
**proonline\_installment\_kz\_0\_0\_12** — Рассрочка от Про-онлайн в КЗ на 12 месяцев
**proonline\_installment\_kz\_0\_0\_18** — Рассрочка от Про-онлайн в КЗ на 18 месяцев
**proonline\_installment\_kz\_0\_0\_24** — Рассрочка от Про-онлайн в КЗ на 24 месяца

**proonline\_installment\_kg\_0\_0\_6** — Рассрочка от Про-онлайн в Кыргызстане на 6 месяцев
**proonline\_installment\_kg\_0\_0\_12** — Рассрочка от Про-онлайн в Кыргызстане на 12 месяцев
**proonline\_installment\_kg\_0\_0\_18** — Рассрочка от Про-онлайн в Кыргызстане на 18 месяцев
**proonline\_installment\_kg\_0\_0\_24** — Рассрочка от Про-онлайн в Кыргызстане на 24 месяца

**installment\_4\_14:v3.0** \- Частями 3.0 от Продамус на 1,5 месяца

**installment\_5\_21:v3.0**\- Частями 3.0 от Продамус на 3 месяца
**installment\_6\_28:v3.0** \- Частями 3.0 от Продамус на 6 месяцев
**installment\_10\_28:v3.0** \- Частями 3.0 от Продамус на 10 месяцев
**installment\_12\_28:v3.0** \- Частями 3.0 от Продамус на 12 месяцев
**yandex\_installment\_0\_0\_2** \- Яндекс Сплит на 2 месяца
**yandex\_installment\_0\_0\_4** \- Яндекс Сплит на 4 месяца
**yandex\_installment\_0\_0\_6** \- Яндекс Сплит на 6 месяцев
**yandex\_installment\_0\_0\_12** \- Яндекс Сплит на 12 и 24 месяца

**TINKOFF\_API\_SUBSIDIZED\_HIGH\_INSTALLMENT\_0\_0\_3** \- рассрочка Т-банка на 3 месяца **TINKOFF\_API\_SUBSIDIZED\_HIGH\_INSTALLMENT\_0\_0\_4** \- рассрочка Т-банка на 4 месяца **TINKOFF\_API\_SUBSIDIZED\_HIGH\_INSTALLMENT\_0\_0\_6** \- рассрочка Т-банка на 6 месяцев **TINKOFF\_API\_SUBSIDIZED\_HIGH\_INSTALLMENT\_0\_0\_10** \- рассрочка Т-банка на 10 месяцев

**TINKOFF\_API\_SUBSIDIZED\_HIGH\_INSTALLMENT\_0\_0\_12**\- рассрочка Т-банка на 12 месяцев **TINKOFF\_API\_SUBSIDIZED\_HIGH\_INSTALLMENT\_0\_0\_18** \- рассрочка Т-банка на 18 месяцев **TINKOFF\_API\_SUBSIDIZED\_HIGH\_INSTALLMENT\_0\_0\_24** \- рассрочка Т-банка на 24 месяца **TINKOFF\_API\_SUBSIDIZED\_HIGH\_INSTALLMENT\_0\_0\_36**\- рассрочка Т-банка на 36 месяцев

**credit** \- Кредит от Тинькофф
**vsegdada\_installment\_0\_0\_3** \- Рассрочка ВсегдаДа на 3 месяца без переплаты!

**vsegdada\_installment\_0\_0\_4** \- Рассрочка ВсегдаДа на 4 месяца без переплаты! (не работает с available\_payment\_methods)

**vsegdada\_installment\_0\_0\_6** \- Рассрочка от ВсегдаДа на 6 месяцев без переплаты!

**vsegdada\_installment\_0\_0\_10** \- Рассрочка от ВсегдаДа на 10 месяцев без переплаты

**vsegdada\_installment\_0\_0\_12** \- Рассрочка от ВсегдаДа на 12 месяцев без переплаты

**vsegdada\_installment\_0\_0\_18** \- Рассрочка от ВсегдаДа на 18 месяцев без переплаты

**vsegdada\_installment\_0\_0\_24** \- Рассрочка от ВсегдаДа на 24 месяца без переплаты!

**vsegdada\_installment\_0\_0\_36** \- Рассрочка от ВсегдаДа на 36 месяцев без переплаты!

**sbrf\_installment\_0\_0\_6** \- Рассрочка от СберБанка на 6 месяцев

**sbrf\_installment\_0\_0\_10** \- Рассрочка от СберБанка на 10 месяцев

**sbrf\_installment\_0\_0\_12** \- Рассрочка от СберБанка на 12 месяцев

**sbrf\_installment\_0\_0\_18 -** Рассрочка от СберБанка на 18 месяца
**otp\_installment\_0\_0\_3 -** Рассрочка «ОТП Банка» на 3 месяца
**otp\_installment\_0\_0\_6 -** Рассрочка «ОТП Банка» на 6 месяцев
**otp\_installment\_0\_0\_10 -** Рассрочка «ОТП Банка» на 10 месяцев
**otp\_installment\_0\_0\_12 -** Рассрочка «ОТП Банка» на 12 месяцев
**otp\_installment\_0\_0\_18 -** Рассрочка «ОТП Банка» на 18 месяцев

**otp\_installment\_0\_0\_24 -** Рассрочка «ОТП Банка» на 24 месяцев

**otp\_installment\_0\_0\_36 -** Рассрочка «ОТП Банка» на 36 месяцев
**monetaworld** \- Карты банков мира, кроме РФ
**sbrf\_bnpl** \- Частями от Сбер
**wbpay** \- WB кошелек
**yandexpay** \- Yandex Pay

available\_payment\_methods

строка

Список доступных методов оплаты. Список возможных значений аналогичен параметру **payment\_method.** Допускается передача нескольких значений, разделяя их вертикальной чертой. Если **available\_payment\_methods** передан, то список доступных методов оплаты будет ограничен переданными кодами. Если в результате фильтрации не остается ни одного метода оплаты, данный параметр будет проигнорирован и выведется полный список доступных методов.

urlReturn

строка

URL-адрес для возврата пользователя без оплаты

urlSuccess

строка

URL-адрес для возврата пользователя при успешной оплате

urlNotification

строка

служебный URL-адрес для уведомления интернет-магазина о поступлении оплаты по заказу

в случае успешной обработки запроса, должен вернуть ответ с кодом 200
P.S. Для того, чтобы система учла этот параметр, также должен быть передан параметр sys

\_param\_хххх

строка

произвольный сквозной параметр, где хххх \- имя вашего произвольного параметра

utm\_хххх

строка

сквозной параметр в виде utm-метки, где хххх - имя вашей метки

Например: utm\_source

installments\_disabled

целое число

отключение рассрочки

если передан и не 0, методы оплаты связанные с рассрочкой будут недоступны для выбора при оплате

demoFlow

строка

Параметр для проверки негативного сценария с отказом по рассрочке. ❗ **Работает только в демо-режиме❗** Доступное значение:

**reject**

demo\_mode

целое число

Если передано значение 1, то платеж пройдет в демо-режиме

type

строка

Если передано значение json, то ответ от Продамуса придет в формате json

callbackType

строка

Если передано значение json, то веб-хуки от Продамуса будут приходить в формате json

currency

строка

Валюта платежа. Возможные значения:

rub

usd

eur
kzt
P.S. Параметр должен быть в нижнем регистре.

payments\_limit

целое число

Лимит оплат по сформированной ссылке

acquiring

строка

Эквайринг.
Возможные значения:
sbrf
moneta

qiwi

xpay

xpaykz

circle-info

- Переход пользователя по **urlSuccess** не является подтверждением факта оплаты;

- **urlSuccess** используется только для пользовательского сценария возврата при успешной оплате;

- Подтверждением оплаты считается только webhook ( **urlNotification**) с валидной подписью.


#### [hashtag](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov\#parametr-customer_phone)    **Параметр**`customer_phone`

Данный параметр является обязательным при оплате покупателем товара на вашей платежной странице, но не является обязательным при формировании ссылки.

То есть вы можете сформировать ссылку на оплату не указывая номер телефона покупателя, он заполнит это поле самостоятельно. В этом случае покупателю откроется ссылка в предварительном окне оплаты, где система попросит заполнить поле номер телефона (рис. 1⬇️) и после его заполнения и нажатия кнопки "Оплатить" ваш плательщик уже перейдет на страницу с выбором метода оплаты и сможет оплатить товар (рис.2⬇️)

Если вы хотите исключить дополнительный шаг при покупке, то можете прописать параметр `customer_phone`уже при формировании ссылки на оплату, тогда ваш покупатель будет переходить сразу на шаг выбора удобного ему метода оплаты (рис.2⬇️)

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-legacy-files%2Fo%2Fassets%252F-M5pHt5axogA0zyX7V6_%252F-MOAh3a8aay-oGFeuuCi%252F-MOBCORlZd5OMCjUNG8u%252Fimage.png%3Falt%3Dmedia%26token%3D8061c732-7494-4655-a863-b623ea449014&width=768&dpr=3&quality=100&sign=9413f9cd&sv=2)

рис. 1

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-legacy-files%2Fo%2Fassets%252F-M5pHt5axogA0zyX7V6_%252F-MOAh3a8aay-oGFeuuCi%252F-MOBD9G-Hs34ExrJDrMF%252Fimage.png%3Falt%3Dmedia%26token%3D719ef3cb-9bf9-4cc3-87b0-e0e164c0af41&width=768&dpr=3&quality=100&sign=2ae2461a&sv=2)

рис. 2

circle-check

Параметры urlReturn и urlSuccess актуальны, например, в тех случаях, когда оплата была инициирована на стороне Вашего интернет-магазина и необходимо чтобы пользователь вернулся обратно. В случае отсутствия данных параметров в запросе, сообщение об успехе или ошибке, после оплаты, будет показано показано на платежной странице системы Продамус.

triangle-exclamation

Если передан параметр subscription, параметр products игнорируется.

### [hashtag](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov\#ssylka-na-oplatu)    Ссылка на оплату

При значении параметра `do`=link ссылка возвращается в текстовом формате вида `https://payform.ru/u8zDE/`

Именно ее вам необходимо передать клиенту по средствам возможности вашего бота при помощи сообщения в мессенджере или через сторонние сервисы-рассыльщики

Так же есть возможность прописать развернутую ссылку с прописанными необходимыми в ней параметрами

> _Пример ссылки с запросом и прописанными в ней параметрами:_
>
> `https://demo.payform.ru/?order_id=test&customer_phone=79998887755&products[0][price]=2000&products[0][quantity]=1&products[0][name]=Обучающие материалы&customer_extra=Полная оплата курса&do=pay`

### [hashtag](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov\#pri-nastroike-samostoyatelnoi-integracii)    При настройке самостоятельной интеграции

Чтобы сформировать Webhook на стороне вашего сервиса для передачи данных об плате, вам необходимо добавить программный код на вашем сайте

### [hashtag](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov\#undefined-1)

### [hashtag](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov\#primer-programmnogo-koda-formirovaniya-ssylki-dlya-demo-formy)    Пример программного кода формирования ссылки для демо-формы:

В данном примере используется платежная страница демо-формы: `https://demo.payform.ru`

Секретный ключ демо-формы: `2y2aw4oknnke80bp1a8fniwuuq7tdkwmmuq7vwi4nzbr8z1182ftbn6p8mhw3bhz`

Copy

```
<?php

header('Content-type:text/plain;charset=utf-8');

require_once __DIR__ . '/Hmac.php';

$linktoform = 'https://demo.payform.ru/';

// Секретный ключ. Можно найти на странице настроек,
// в личном кабинете платежной формы.
$secret_key = '2y2aw4oknnke80bp1a8fniwuuq7tdkwmmuq7vwi4nzbr8z1182ftbn6p8mhw3bhz';

$data = [\
	// хххх - номер заказ в системе интернет-магазина\
	'order_id' => хххх,\
\
	// +7хххххххххх - мобильный телефон клиента\
	'customer_phone' => '+7хххххххххх',\
\
	// ИМЯ@prodamus.ru - e-mail адрес клиента\
	'customer_email' => 'ИМЯ@prodamus.ru',\
\
	// перечень товаров заказа\
	'products' => [\
		[\
			// id товара в системе интернет-магазина\
			//    (не обязательно) - при необходимоти прописать\
			'sku' => ХХХХХ,\
\
			// название товара - необходимо прописать название вашего товара\
			//          (обязательный параметр)\
			'name' => 'товар 1',\
\
			// цена за единицу товара, 123 - значение, которое нужно прописать\
			//      (обязательный параметр)\
			'price' => '123',\
\
			// количество товара, х - значение, которое нужно прописать\
			//           (обязательный параметр)\
			'quantity' => 'Х',\
\
			// данные о налоге\
			// (не обязательно, если не указано будет взято из настроек Магазина\
			//  на стороне системы)\
			'tax' => [\
\
			  // ставка НДС, с возможными значениями (при необходимоти заменить):\
			  //	0 – без НДС;\
			  //	1 – НДС по ставке 0%;\
			  //	2 – НДС чека по ставке 10%;\
			  //	4 – НДС чека по расчетной ставке 10/110;\
			  //	6 - НДС чека по ставке 20%;\
			  //	7 - НДС чека по расчетной ставке 20/120;\
			  //  10 - НДС чека по ставке 5%;\
		 	  //  11 - НДС чека по расчетной ставке 5/105;\
			  //  12 - НДС чека по ставке 7%;\
			  //  13 - НДС чека по расчетной ставке 7/107;\
			  //  14 - НДС по ставке 22%;\
			  //  15 - НДС чека по расчетной ставке 22/122.\
			  'tax_type' => 0,\
\
			  // (не обязательно) сумма налога, хх - при необходимости заменить\
			  'tax_sum' => хх,\
\
			],\
\
			// Тип оплаты, с возможными значениями (при необходимости заменить):\
			//	1 - полная предварительная оплата до момента передачи предмета расчёта;\
			//	2 - частичная предварительная оплата до момента передачи\
			//      предмета расчёта;\
			//	3 - аванс;\
			//	4 - полная оплата в момент передачи предмета расчёта;\
			//	5 - частичная оплата предмета расчёта в момент его передачи\
			//      с последующей оплатой в кредит;\
			//	6 - передача предмета расчёта без его оплаты в момент\
			//      его передачи с последующей оплатой в кредит;\
			//	7 - оплата предмета расчёта после его передачи с оплатой в кредит.\
			// (не обязательно, если не указано будет взято из настроек\
			//     Магазина на стороне системы)\
			'paymentMethod' => х,\
\
			// Тип оплачиваемой позиции, с возможными\
			//     значениями (при необходимости заменить):\
			//	1 - товар;\
			//	2 - подакцизный товар;\
			//	3 - работа;\
			//	4 - услуга;\
			//	5 - ставка азартной игры;\
			//	6 - выигрыш азартной игры;\
			//	7 - лотерейный билет;\
			//	8 - выигрыш лотереи;\
			//	9 - предоставление РИД;\
			//	10 - платёж;\
			//	11 - агентское вознаграждение;\
			//	12 - составной предмет расчёта;\
			//	13 - иной предмет расчёта.\
			// (не обязательно, если не указано будет взято из настроек Магазина на стороне системы)\
			'paymentObject' => х,\
		],\
	],\
\
	// id подписки (при необходимости прописать)\
	// актуально и обязательно только для рекуррентных платежей,\
	//           передается вместо параметра products\
	'subscription' => 123,\
\
	// вк id пользователя (при необходимости прописать)\
	'vk_user_id' => 123,\
\
	// фио пользователя в ВК (при необходимости прописать)\
	'vk_user_name' => 'Фамилия Имя Отчество',\
\
	// дополнительные данные\
	'customer_extra' => 'Текст, который отобразится в поле "Дополнительные данные"',\
\
	// для интернет-магазинов доступно только действие "Оплата"\
	'do' => 'pay',\
\
	// url-адрес для возврата пользователя без оплаты\
	//           (при необходимости прописать свой адрес)\
	'urlReturn' => 'https://demo.payform.ru/demo-return',\
\
	// url-адрес для возврата пользователя при успешной оплате\
	//           (при необходимости прописать свой адрес)\
	'urlSuccess' => 'https://demo.payform.ru/demo-success',\
\
	// служебный url-адрес для уведомления интернет-магазина\
	//           о поступлении оплаты по заказу\
	// 	         пока реализован только для Advantshop,\
	//           формат данных настроен под систему интернет-магазина\
	//           (при необходимости прописать свой адрес)\
	'urlNotification' => 'https://demo.payform.ru/demo-notification',\
\
	// код системы интернет-магазина, запросить у поддержки,\
	//     для самописных систем можно оставлять пустым полем\
	//     (при необходимости прописать свой код)\
	'sys' => 'код системы',\
\
	// метод оплаты, выбранный клиентом\
	// 	     если есть возможность выбора на стороне интернет-магазина,\
	// 	     иначе клиент выбирает метод оплаты на стороне платежной формы\
	//       варианты (при необходимости прописать значение):\
	// 	AC - банковская карта\
	// 	PC - Яндекс.Деньги\
	// 	QW - Qiwi Wallet\
	// 	WM - Webmoney\
	// 	GP - платежный терминал\
	'payment_method' => 'ХХ',\
\
	// сумма скидки на заказ\
	// 	     указывается только в том случае, если скидка\
	//       не прменена к товарным позициям на стороне интернет-магазина\
	// 	     алгоритм распределения скидки по товарам\
	//       настраивается на стороне пейформы\
	'discount_value' => 0.00,\
\
	// тип плательщика, с возможными значениями:\
	//     FROM_INDIVIDUAL - Физическое лицо\
	//     FROM_LEGAL_ENTITY - Юридическое лицо\
	//     FROM_FOREIGN_AGENCY - Иностранная организация\
	//     (не обязательно. если форма работает в режиме самозанятого\
	//      значение по умолчанию: FROM_INDIVIDUAL)\
	'npd_income_type' => 'FROM_INDIVIDUAL',\
\
	// инн плательщика (при необходимости прописат)\
	//     (обязательно, если форма в режиме самозанятого\
	//      и тип плательщика FROM_LEGAL_ENTITY)\
	'npd_income_inn' => 1234567890,\
\
	// название компании плательщика (при необходимости прописать название)\
	//          (обязательно, если форма в режиме самозанятого\
	//           и тип плательщика FROM_LEGAL_ENTITY или FROM_FOREIGN_AGENCY)\
	'npd_income_company' => 'Название компании плательщика',\
\
	// срок действия ссылки в формате: дд.мм.гггг чч:мм или гггг-мм-дд чч:мм\
	//      при необходимости добавить дату\
	//      (не обязательно, по умолчанию срок действия ссылки не ограничен)\
	'link_expired' => 'дд.мм.гггг чч:мм',\
\
	// дата начала подписки в формате: дд.мм.гггг чч:мм или гггг-мм-дд чч:мм\
	//      при необходимости добавить дату\
	//      (не обязательно, актуально только для рекуррентных платежей,\
	//       по умолчанию текущая дата/время)\
	'subscription_date_start' => 'дд.мм.гггг чч:мм',\
\
	// текст который будет показан пользователю после совершения оплаты\
	//       (не обязательно)\
	'paid_content' => 'Текс сообщения'\
];

$data['signature'] = Hmac::create($data, $secret_key);

$link = sprintf('%s?%s', $linktoform, http_build_query($data));
```

Массив `data`содержит данные для формирования платежной ссылки. Параметр `signature`-подпись запроса **.** Формируется на основе данных формы и секретного ключа. Для формирования подписи запроса можно воспользоваться готовой библиотекой Hmac ⤵️

file-download

1KB

[Hmac.php](https://4061190562-files.gitbook.io/~/files/v0/b/gitbook-legacy-files/o/assets%2F-M5pHt5axogA0zyX7V6_%2F-MG5STXFTiYELgQ9Zjg4%2F-MG5T6RFkEEc2SWLZQMx%2FHmac.php?alt=media&token=f075dcda-63dc-4696-bdde-e24cdef8c366)

downloadDownload [arrow-up-right-from-squareOpen](https://4061190562-files.gitbook.io/~/files/v0/b/gitbook-legacy-files/o/assets%2F-M5pHt5axogA0zyX7V6_%2F-MG5STXFTiYELgQ9Zjg4%2F-MG5T6RFkEEc2SWLZQMx%2FHmac.php?alt=media&token=f075dcda-63dc-4696-bdde-e24cdef8c366)

Библиотека Hmac.php

file-archive

651B

[Hmac.js.zip](https://4061190562-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2F-M5pHt5axogA0zyX7V6_%2Fuploads%2F8wxiomTz12RS2rm5Hopk%2FHmac.js.zip?alt=media&token=b384d44e-c49c-44cc-8e59-1c56ae50edad)

archive

downloadDownload [arrow-up-right-from-squareOpen](https://4061190562-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2F-M5pHt5axogA0zyX7V6_%2Fuploads%2F8wxiomTz12RS2rm5Hopk%2FHmac.js.zip?alt=media&token=b384d44e-c49c-44cc-8e59-1c56ae50edad)

Библиотека Hmac.js

**Алгоритм формирования подписи:**

1. Возьмите содержимое запроса и приведите все значения к строкам

2. Далее отсортируйте все содержимое по ключам в алфавитном порядке, в том числе вглубь

3. Переведите массив в json строку

4. В json строке экранируйте /

5. Подпишите получившуюся json строку через sha256 секретным ключом со страницы.


**Поведение демо-платежей на уровне подписи:**

- при демо-платежах используется намеренно отличающаяся подпись (secret key с суффиксом demo);

- такая подпись не должна проходить проверку как боевая;

- это сделано специально, чтобы исключить принятие демо-платежей за реальные и предотвратить выдачу платного контента.


circle-info

**Дополнительно:**

В системе предусмотрены два сценария демо-режима:

- демо-режим, который мерчант может включить самостоятельно в настройках платежной страницы, предназначен для тестирования пользовательского сценария и не влияет на подпись запросов

- защитная логика с изменением подписи применяется только при отключении боевого режима платежной страницы **на стороне системы**


### [hashtag](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov\#kak-prinyat-uvedomlenie-ob-uspeshnoi-oplate)    Как принять Уведомление об успешной оплате

При настройке принятия веб-хука с уведомлением об успешной оплате на вашем сервисе (пример [уведомления об оплате здесь](https://help.prodamus.ru/payform/uvedomleniya)), вам необходимо проверить подпись пришедшего запроса. Так скажем, убедиться, что Веб-Хук пришел именно от Продамуса.

Проверка подписи необходима в целях безопасности, иначе, технически, веб-хук может отправить кто угодно. Подпись формируется на основе данных запроса и секретного ключа вашей платежной страницы.

Для проверки подписи, необходимо вызвать метод **verify** класса **Hmac**, в качестве аргументов передайте данные входящего POST запроса, секретный ключ платежной страницы и подпись из заголовков запроса. Метод сформирует подпись на основе данных запроса и секретного ключа (аргументы 1 и 2) и сравнит его с подписью, которая была передана в запросе (аргумент 3). Если метод вернул **false** (подписи не совпадают), необходимо вернуть http-код отличный от 200 и прекратить дальнейшую обработку. В случае, если метод вернул **true** (подписи совпадают), необходимо вернуть http-код 200 и отработать дальнейшие команды на стороне вашего сервиса.

Пример проверки подписи запроса:

Copy

```
require_once 'Hmac.php';

$secret_key = 'ваш_секретный_ключ';
$headers = apache_request_headers();

try {
	if ( empty($_POST) ) {
		throw new Exception('$_POST is empty');
	}
	elseif ( empty($headers['Sign']) ) {
		throw new Exception('signature not found');
	}
	elseif ( !Hmac::verify($_POST, $secret_key, $headers['Sign']) ) {
		throw new Exception('signature incorrect');
	}

	http_response_code(200);
	echo 'success';
}
catch (Exception $e) {
	http_response_code($e->getCode() ? $e->getCode() : 400);
	printf('error: %s', $e->getMessage());
}
```

file-download

1KB

[Hmac.php](https://4061190562-files.gitbook.io/~/files/v0/b/gitbook-legacy-files/o/assets%2F-M5pHt5axogA0zyX7V6_%2F-MIUcYNmNYoLCbO07FSa%2F-MIUcge6O0UqlW3S8wh4%2FHmac.php?alt=media&token=3360c7ee-4175-40ca-92de-488fbcc3dd2e)

downloadDownload [arrow-up-right-from-squareOpen](https://4061190562-files.gitbook.io/~/files/v0/b/gitbook-legacy-files/o/assets%2F-M5pHt5axogA0zyX7V6_%2F-MIUcYNmNYoLCbO07FSa%2F-MIUcge6O0UqlW3S8wh4%2FHmac.php?alt=media&token=3360c7ee-4175-40ca-92de-488fbcc3dd2e)

Библиотека Hmac

file-archive

651B

[Hmac.js.zip](https://4061190562-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2F-M5pHt5axogA0zyX7V6_%2Fuploads%2F8wxiomTz12RS2rm5Hopk%2FHmac.js.zip?alt=media&token=b384d44e-c49c-44cc-8e59-1c56ae50edad)

archive

downloadDownload [arrow-up-right-from-squareOpen](https://4061190562-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2F-M5pHt5axogA0zyX7V6_%2Fuploads%2F8wxiomTz12RS2rm5Hopk%2FHmac.js.zip?alt=media&token=b384d44e-c49c-44cc-8e59-1c56ae50edad)

Библиотека Hmac.js

### [hashtag](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov\#proverka-uspeshnoi-integracii)    Проверка успешной интеграции

Для тестирования используйте свою платежную странницу, в исключительном случае вы можете воспользоваться данными нашей демо-страницы, для этого необходимо запросить доступ у менеджеров

circle-check

по телефону: `8 (495) 150-08-71`

в личные сообщения группы в VK: [https://vk.com/im?sel=-11636316arrow-up-right](https://vk.com/im?sel=-11636316)

на электронную почту: [sales@prodamus.ruenvelope](mailto:sales@prodamus.ru)

в боте в MAX: [https://max.ru/id1215156909\_2\_botarrow-up-right](https://max.ru/id1215156909_2_bot)

circle-info

После всех настроек **обязательно** проверьте формирование ссылки. Пройдите по ней, проверьте все ли параметры прописаны корректно

circle-info

Информация носит исключительно справочный характер и не является офертой. С актуальной редакцией оферты и тарифами Вы можете ознакомиться в разделе " [Документыarrow-up-right](https://prodamus.ru/documents)".

[PreviousГде найти url для уведомлений и секретный ключchevron-left](https://help.prodamus.ru/payform/integracii/rest-api/url-dlya-uvedomlenii-i-sekretnyi-klyuch) [NextТехническая документация по автоплатежамchevron-right](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham)

Last updated 2 days ago

This site uses cookies to deliver its service and to analyze traffic. By browsing this site, you accept the [privacy policy](https://policies.gitbook.com/privacy/cookies).

close

AcceptReject

---

# https://help.prodamus.ru/payform/uvedomleniya/uvedomleniya-v-sms-coobsheniyakh

Если вы хотите получать уведомления о платежах клиентов на свой телефон, следуйте инструкции ниже.

### [hashtag](https://help.prodamus.ru/payform/uvedomleniya/uvedomleniya-v-sms-coobsheniyakh\#h.ajpwf5q9vr8r)    Шаг 1\. Авторизуйтесь на платёжной странице и перейдите в раздел «Настройки»

👉 [Инструкция: как авторизоваться на платёжной страницеarrow-up-right](https://www.google.com/url?q=https://help.prodamus.ru/payform/nastroika-platezhnoi-stranicy/kak-avtorizovatsya-na-platyozhnoi-stranice&sa=D&source=editors&ust=1688959183930669&usg=AOvVaw31XVpCmJpFgbvazZrimy-6)

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252F-M5pHt5axogA0zyX7V6_%252Fuploads%252FoHsHOZVDt5LS9Dv7Jz0U%252Fimage.png%3Falt%3Dmedia%26token%3D65a8c61f-29a1-46a8-9e78-28dcdb32a67c&width=768&dpr=3&quality=100&sign=eb774d8&sv=2)

### [hashtag](https://help.prodamus.ru/payform/uvedomleniya/uvedomleniya-v-sms-coobsheniyakh\#shag-2.-ukazhite-v-bloke-nastroika-uvedomlenii-nomera-telefonov-na-kotorye-prodamus-budet-otpravlyat)    Шаг 2\. Укажите в блоке «Настройка уведомлений» номера телефонов, на которые Prodamus будет отправлять оповещения о платежах клиентов

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252F-M5pHt5axogA0zyX7V6_%252Fuploads%252Fkyqm7v0jsBJC2HNKAzN4%252Fimage.png%3Falt%3Dmedia%26token%3Dc691fc32-91a0-4186-a33f-875320be5320&width=768&dpr=3&quality=100&sign=3b8058fd&sv=2)

Нажмите «Сохранить».

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252F-M5pHt5axogA0zyX7V6_%252Fuploads%252Fi6u0CPxAAugZLspeA7sP%252Fimage.png%3Falt%3Dmedia%26token%3D28497b8d-75dd-4c60-ae8c-50f6275a6c3f&width=768&dpr=3&quality=100&sign=7e63d1b6&sv=2)

### [hashtag](https://help.prodamus.ru/payform/uvedomleniya/uvedomleniya-v-sms-coobsheniyakh\#h.xd8fpf9dotp6)    Шаг 3\. Пополните баланс своего счёта

circle-info

Услуга отправки СМС уведомлений платная. Стоимость одного оповещения — от двух до семи рублей. Точная стоимость зависит от объёма отправляемого сообщения и вашего оператора связи.

Чтобы зачислить деньги на свой счёт, включите «Дополнительный пакет SMS-уведомлений» и нажмите «Пополнить»

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252F-M5pHt5axogA0zyX7V6_%252Fuploads%252FDEp9mTKkS6toR0gflVUJ%252Fimage.png%3Falt%3Dmedia%26token%3D86e28992-80db-41ce-b461-3a7b52ebc43d&width=768&dpr=3&quality=100&sign=2b7634d9&sv=2)

Перейдите в раздел «Финансы» и авторизуйтесь в личном кабинете владельца платёжной страницы.

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252F-M5pHt5axogA0zyX7V6_%252Fuploads%252F6vU1y6G0X5uWTQeiAD1D%252Fimage.png%3Falt%3Dmedia%26token%3D6ee88a79-1d9c-4910-a971-06391c3a52bd&width=768&dpr=3&quality=100&sign=2508bcd1&sv=2)

Нажмите кнопку «Пополнить».

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252F-M5pHt5axogA0zyX7V6_%252Fuploads%252FspMy43of7CHeADg8N7U5%252Fimage.png%3Falt%3Dmedia%26token%3D80acdf9e-4548-4135-8eba-3969e313819a&width=768&dpr=3&quality=100&sign=c60f34bf&sv=2)

Выберите удобный способ оплаты, укажите сумму пополнения и нажмите кнопку «Оплатить».

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252F-M5pHt5axogA0zyX7V6_%252Fuploads%252Fx0Q8iIDdpUVD1vOWVHFx%252Fimage.png%3Falt%3Dmedia%26token%3Dbf715c66-1f2b-493a-8a7f-02ca001cba50&width=768&dpr=3&quality=100&sign=98c75a61&sv=2)

Внесите плату и проверьте баланс. Сделать это можно в личном кабинете платёжной страницы в разделе «Настройки» → «Настройки уведомлений».

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252F-M5pHt5axogA0zyX7V6_%252Fuploads%252FZYwBZrXNsPNCWWeTxGun%252Fimage.png%3Falt%3Dmedia%26token%3Da7e44c7b-13d5-4494-8af7-50a07fd51d34&width=768&dpr=3&quality=100&sign=6338650a&sv=2)

[PreviousКак получать уведомления об оплатах на emailchevron-left](https://help.prodamus.ru/payform/uvedomleniya/email) [NextКак получать уведомления об оплатах на URL-адресchevron-right](https://help.prodamus.ru/payform/uvedomleniya/uvedomleniyakh-na-url-adres)

Last updated 2 days ago

This site uses cookies to deliver its service and to analyze traffic. By browsing this site, you accept the [privacy policy](https://policies.gitbook.com/privacy/cookies).

close

AcceptReject

---

# https://help.prodamus.ru/payform/uvedomleniya/uvedomleniyakh-na-url-adres

Отправка уведомлений на URL-адрес пригодится, если вы настроили интеграцию Prodamus со сторонним сервисом и вам нужно, чтобы в него попадали оповещения о платежах клиентов.

### [hashtag](https://help.prodamus.ru/payform/uvedomleniya/uvedomleniyakh-na-url-adres\#h.tbfsnzogtxsu)    Шаг 1\. Авторизуйтесь на платёжной странице и перейдите в раздел «Настройки»

👉 [Инструкция: как авторизоваться на платёжной страницеarrow-up-right](https://www.google.com/url?q=https://help.prodamus.ru/payform/nastroika-platezhnoi-stranicy/kak-avtorizovatsya-na-platyozhnoi-stranice&sa=D&source=editors&ust=1685379409960906&usg=AOvVaw3T_E5Mb42A7IwRVbK_uKm7)

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252F-M5pHt5axogA0zyX7V6_%252Fuploads%252FyezAXfybhixcQhzzVoSt%252Fimage.png%3Falt%3Dmedia%26token%3D5f07fa37-0f4d-4f6e-a873-db932c2ab25f&width=768&dpr=3&quality=100&sign=b0c85823&sv=2)

### [hashtag](https://help.prodamus.ru/payform/uvedomleniya/uvedomleniyakh-na-url-adres\#h.3kuz4lf1t1na)    Шаг 2\. Заполните поле «URL адреса для уведомлений»

Укажите URL-адрес, на который Prodamus будет отправлять уведомления об оплатах. Если хотите получать оповещения на несколько адресов, нажмите на кнопку «+» и введите другие адреса.

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252F-M5pHt5axogA0zyX7V6_%252Fuploads%252FrT9VQQK5cIEtZJL1drqg%252Fimage.png%3Falt%3Dmedia%26token%3D5988933a-75fc-4f6f-a6f8-4e1c9ddc556e&width=768&dpr=3&quality=100&sign=fe90ef8d&sv=2)

В разделе «Настройки» вы также найдёте секретный ключ, который нужно скопировать и указать на стороне сервиса, с которым вы настраиваете интеграцию.

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252F-M5pHt5axogA0zyX7V6_%252Fuploads%252FhZJJLyV81KmF6BCVnleE%252Fimage.png%3Falt%3Dmedia%26token%3D106f9d74-6ae5-4373-b622-2d07b8f785d7&width=768&dpr=3&quality=100&sign=ad94d98c&sv=2)

circle-info

**Важно.** Если вы просто укажете URL-адреса, но при этом не настроите взаимодействие между Prodamus и сторонним сервисом, уведомления о платежах обрабатываться не будут.

### [hashtag](https://help.prodamus.ru/payform/uvedomleniya/uvedomleniyakh-na-url-adres\#h.xlz3ttvfrc7r)    Шаг 3\. Нажмите кнопку «Сохранить»

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252F-M5pHt5axogA0zyX7V6_%252Fuploads%252FvujokdkSLIdjmEqgZjmI%252Fimage.png%3Falt%3Dmedia%26token%3D0310bd6f-b145-4a14-bfe2-21a62e75feb9&width=768&dpr=3&quality=100&sign=9168aa84&sv=2)

circle-info

Информация носит исключительно справочный характер и не является офертой. С актуальной редакцией оферты и тарифами Вы можете ознакомиться в разделе " [Документыarrow-up-right](https://prodamus.ru/documents)".

[PreviousКак получать уведомления об оплатах через СМСchevron-left](https://help.prodamus.ru/payform/uvedomleniya/uvedomleniya-v-sms-coobsheniyakh) [NextИнтервалы уведомленийchevron-right](https://help.prodamus.ru/payform/uvedomleniya/intervaly-uvedomlenii)

Last updated 2 days ago

This site uses cookies to deliver its service and to analyze traffic. By browsing this site, you accept the [privacy policy](https://policies.gitbook.com/privacy/cookies).

close

AcceptReject

---

# https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/zavershenie-podpiski

Завершенная подписка \- это подписка с истекшим оплаченным периодом, по которой не возможно совершить очередное продление.

Продление подписки не возможно в следующих случаях:

- для подписки установлено максимальное количество автосписаний и было совершено последнее списание

- подписка была деактивирована менеджером/пользователем

- после нескольких попыток не удалось списать деньги с карты пользователя


**Примеры:**

_Вариант 1_

- клиент оформил месячную подписку, по которой предполгагается 5 продлений

- с интервалом в 30 дней было произведено 5 автосписаний (продление подписки)

- наступает дата очередного продления подписки

- подписка завершается, т.к. 5 продлений уже были выполнены


_Вариант 2_

- клиент оформил подписку

- клиент или менеджер деактивирует подписку

- отправляется уведомление о деактивации подписки

- наступает дата очередного продления подписки

- подписка завершается, т.к. она была деактивирована


_Вариант 3_

- клиент оформил подписку (для подписок установлено 3 попытки списания при неудаче)

- наступает дата очередного продления подписки

- было предпринято 3 неудачные попытки списания

- подписка завершается, т.к. была последняя попытка списания


Управление завершенными подписками не допускается. Например, в ЛК, вместо переключателей статусов подписки, будет отображен статус "Завершена", а при попытке изменить данные через REST API будет получен ответ со следующей ошибкой:

Copy

```
subscription {id} completed, data modification is prohibited
```

При завершении подписки будет отправлено уведомление на почту клиенту и менеджерам, а так же веб-хук, на URL-адрес, указанный в настройках подписок ЛК.

Далее примеры передаваемых в веб-хуке данных, в зависимости от причины завершения подписки.

_Совершено максимальное количество автосписаний:_

Copy

```
Array
(
    [date] => 2020-07-17T18:22:02+03:00
    [order_id] => 0
    [order_num] =>
    [domain] => demo.payform.ru
    [sum] => 1.00
    [customer_phone] => +79999999999
    [payment_type] => Автоплатеж
    [attempt] => 1
    [discount_value] => 0.00
    [subscription] => Array
        (
            [type] => action
            [action_code] => finish
            [action_reason] => completed
            [date] => 2020-07-17 18:21
            [id] => 593600
            [active] => 1
            [active_manager] => 1
            [active_user] => 1
            [cost] => 1.00
            [name] => Доступ в клуб "Девелопер клаб" – тестовая подписка
            [limit_autopayments] => 3
            [autopayments_num] => 3
            [first_payment_discount] => 0.00
            [next_payment_discount] => 0.00
            [next_payment_discount_num] =>
            [date_create] => 2020-03-16 12:42:32
            [date_first_payment] => 2020-03-17 12:42:32
            [date_last_payment] => 2020-06-17 14:40:53
            [date_next_payment] =>
            [date_next_payment_discount] =>
            [current_attempt] => 1
            [payment_num] => 4
            [autopayment] => 1
        )

)
```

_Завершение деактивированной подписки:_

Copy

```
Array
(
    [date] => 2020-07-17T18:22:02+03:00
    [order_id] => 0
    [order_num] =>
    [domain] => demo.payform.ru
    [sum] => 1.00
    [customer_phone] => +79999999999
    [payment_type] => Автоплатеж
    [attempt] => 1
    [discount_value] => 0.00
    [subscription] => Array
        (
            [type] => action
            [action_code] => finish
            [action_reason] => deactivated
            [date] => 2020-07-17 18:21
            [id] => 593600
            [active] => 0
            [active_manager] => 1
            [active_user] => 0
            [cost] => 1.00
            [name] => Доступ в клуб "Девелопер клаб" – тестовая подписка
            [limit_autopayments] => 3
            [autopayments_num] => 3
            [first_payment_discount] => 0.00
            [next_payment_discount] => 0.00
            [next_payment_discount_num] =>
            [date_create] => 2020-03-16 12:42:32
            [date_first_payment] => 2020-03-17 12:42:32
            [date_last_payment] => 2020-06-17 14:40:53
            [date_next_payment] =>
            [date_next_payment_discount] =>
            [current_attempt] => 1
            [payment_num] => 4
            [autopayment] => 1
        )

)
```

_При очередном продлении, не удалось списать деньги со счета клиента (достигнут лимит попыток списания):_

Copy

```
Array
(
    [date] => 2020-07-17T18:31:02+03:00
    [order_id] => 287190
    [order_num] => тест
    [domain] => demo.payform.ru
    [sum] => 1.00
    [customer_phone] => +79999999999
    [payment_type] => Автоплатеж
    [attempt] => 1
    [discount_value] => 0.00
    [subscription] => Array
        (
            [type] => action
            [action_code] => deactivation
            [error_code] => insufficient_funds
            [error] => Недостаточно средств
            [last_attempt] => yes
            [attempt_num] => 2
            [payment_date] => 2020-07-17 18:30:44
            [id] => 593600
            [active] => 0
            [active_manager] => 0
            [active_user] => 1
            [cost] => 1.00
            [name] => Доступ в клуб "Девелопер клаб" – тестовая подписка
            [limit_autopayments] =>
            [autopayments_num] => 3
            [first_payment_discount] => 0.00
            [next_payment_discount] => 0.00
            [next_payment_discount_num] =>
            [date_create] => 2020-03-16 12:42:32
            [date_first_payment] => 2020-03-17 12:42:32
            [date_last_payment] => 2020-06-17 14:40:53
            [date_next_payment] =>
            [date_next_payment_discount] =>
            [current_attempt] => 1
            [payment_num] => 4
        )

)
```

circle-info

Подробное описание уведомлений на странице Уведомления о завершении подписки

circle-info

Информация носит исключительно справочный характер и не является офертой. С актуальной редакцией оферты и тарифами Вы можете ознакомиться в разделе " [Документыarrow-up-right](https://prodamus.ru/documents)".

[PreviousУправление клубным функционаломchevron-left](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/untitled) [NextУведомления при автосписанииchevron-right](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/uvedomleniya-pri-avtospisanii)

Last updated 2 days ago

This site uses cookies to deliver its service and to analyze traffic. By browsing this site, you accept the [privacy policy](https://policies.gitbook.com/privacy/cookies).

close

AcceptReject

---

# https://help.prodamus.ru/payform/integracii/rest-api/url-dlya-uvedomlenii-i-sekretnyi-klyuch

Где взять секретный ключ и как прописать url уведомлений - YouTube

Tap to unmute

[Где взять секретный ключ и как прописать url уведомлений](https://www.youtube.com/watch?v=GYKKPr9WR_U) [Prodamus](https://www.youtube.com/channel/UCy74WeLy3sERrKiX_ys3qAA)

![thumbnail-image](https://yt3.ggpht.com/R61Hqkx3jo64tr00e4gp9LT24Pj8tjd7DGiFa8sSjnPrcp2KK4YQFrtgBw4T9EdK-7n5hhMqztQ=s68-c-k-c0x00ffffff-no-rj)

Prodamus957 subscribers

[Watch on](https://www.youtube.com/watch?v=GYKKPr9WR_U)

1. Авторизуемся на платежной странице, как это сделать подробно в инструкции


👉 [Как авторизоваться на платежной странице](https://help.prodamus.ru/payform/nastroika-platezhnoi-stranicy/kak-avtorizovatsya-na-platyozhnoi-stranice)

2\.
Секретный ключ и URL-адрес для уведомлений (или еще называют вебхук) нужны при интеграции с другими сервисами.

В нижнем меню нажимаем пункт Настройки

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-legacy-files%2Fo%2Fassets%252F-M5pHt5axogA0zyX7V6_%252F-MLD80CuwbDfes39te7I%252F-MLDBKwYjpJSRwT_tAH9%252Fimage.png%3Falt%3Dmedia%26token%3D6e0c5854-a300-4fc7-9d96-0d0b0703a1af&width=768&dpr=3&quality=100&sign=410a4e90&sv=2)

Раздел «Настройки»

Здесь мы можем найти секретный ключ. Его можно скопировать и использовать по назначению

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252F-M5pHt5axogA0zyX7V6_%252Fuploads%252FyRmC2XEMifeQuNrioCrd%252FScreenshot%2520%2812%29.png%3Falt%3Dmedia%26token%3Da5d9de7d-3ed7-4bd0-a1d7-a1be1ebdffa8&width=768&dpr=3&quality=100&sign=d3d299ab&sv=2)

circle-check

Если в дальнейшем в работе Вам потребуется новый секретный ключ, то нужно будет обратиться в поддержку:

по телефону: `8 (495) 150-08-71`

в личные сообщения группы в VK: [https://vk.com/im?sel=-11636316arrow-up-right](https://vk.com/im?sel=-11636316)

на электронную почту: [sales@prodamus.ruenvelope](mailto:sales@prodamus.ru)

в боте в MAX: [https://t.me/prodamus\_botarrow-up-right](https://t.me/prodamus_bot)

4\. В следующем поле «Настройка уведомлений» вводим URL адрес для уведомлений. Нажимаем обязательно кнопку сохранить

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-legacy-files%2Fo%2Fassets%252F-M5pHt5axogA0zyX7V6_%252F-MJl4Uoj-xVz7yrpql7m%252F-MJl8eczULfRrHcZxvKN%252Fimage.png%3Falt%3Dmedia%26token%3D9f93e1aa-9543-40e1-b2de-d5918a419c4f&width=768&dpr=3&quality=100&sign=e013a87a&sv=2)

1.Можно добавить еще один адрес URL адрес. 2. Удалить ненужный URL адрес

**5.** **Важная информация для владельцев клубов.**

Вам обязательно нужно ввести URL-адреса для уведомлений о совершении оплат по подписке в разделе Подписки. В противном случае уведомления по автоплатежам не будут уходить. Как это сделать

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-legacy-files%2Fo%2Fassets%252F-M5pHt5axogA0zyX7V6_%252F-MLD80CuwbDfes39te7I%252F-MLDBKwYjpJSRwT_tAH9%252Fimage.png%3Falt%3Dmedia%26token%3D6e0c5854-a300-4fc7-9d96-0d0b0703a1af&width=768&dpr=3&quality=100&sign=410a4e90&sv=2)

Раздел «Настройки»

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-legacy-files%2Fo%2Fassets%252F-M5pHt5axogA0zyX7V6_%252F-MLKO7EprivvfKv6IZ0V%252F-MLKOpxuNAFRmtisAeMA%252Fimage.png%3Falt%3Dmedia%26token%3D75d4ccdb-2ae0-4be6-9f76-5040b555c6c2&width=768&dpr=3&quality=100&sign=76193ba6&sv=2)

В верхнем меню нажимаем поле «подписки»

6\. Вводим URL адрес для уведомлений о совершении оплат по подписке. Нажимаем «сохранить»

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-legacy-files%2Fo%2Fassets%252F-M5pHt5axogA0zyX7V6_%252F-MLKO7EprivvfKv6IZ0V%252F-MLKPHX9N9dA3PJw2AfU%252Fimage.png%3Falt%3Dmedia%26token%3D1f0124d9-5894-4aa0-b929-a36f85bd1fbc&width=768&dpr=3&quality=100&sign=21eb3cca&sv=2)

circle-info

Информация носит исключительно справочный характер и не является офертой. С актуальной редакцией оферты и тарифами Вы можете ознакомиться в разделе " [Документыarrow-up-right](https://prodamus.ru/documents)".

[PreviousДокументация для интеграции со сторонними сервисамиchevron-left](https://help.prodamus.ru/payform/integracii/rest-api) [NextДокументация для самостоятельной интеграции сервисовchevron-right](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov)

Last updated 2 days ago

This site uses cookies to deliver its service and to analyze traffic. By browsing this site, you accept the [privacy policy](https://policies.gitbook.com/privacy/cookies).

close

AcceptReject

---

# https://help.prodamus.ru/payform/integracii/rest-api-1/setactivity

Управление осуществляется от лица менеджера и пользователя

> Менеджер \- владелец платежной страницы
>
> Пользователь \- покупатель

Если решение по отключению подписки принято владельцем платежной страницы, то деактивация должна осуществляться от лица менеджера. А если отписку инициирует покупатель, то от лица пользователя

circle-exclamation

После деактивации подписки от лица пользователя, активировать ее повторно не возможно.

Для возобновления доступа к подписке, пользователь может оформить ее повторно

## [hashtag](https://help.prodamus.ru/payform/integracii/rest-api-1/setactivity\#setactivity)    setActivity

`POST``https://demo.payform.ru/rest/setActivity/`

Управляет статусами подписки

#### [hashtag](https://help.prodamus.ru/payform/integracii/rest-api-1/setactivity\#query-parameters)    Query Parameters

Name

Type

Description

signature

string

Подпись запроса

subscription

integer

ID подписки
\- допускается передача нескольких ID в виде массива

tg\_user\_id

integer

ID профиля клиента Telegram
\- обязателен, если не передан один из параметров vk\_user\_id/profile/customer\_phone/customer\_email

customer\_email

string

Email клиента
\- обязателен, если не передан один из параметров vk\_user\_id/tg\_user\_id/customer\_phone/profile

profile

integer

ID профиля клиента
\- обязателен, если не передан один из параметров vk\_user\_id/tg\_user\_id/customer\_phone/customer\_email

vk\_user\_id

integer

ID профиля клиента ВКонтакте
\- обязателен, если не передан один из параметров profile/tg\_user\_id/customer\_phone/customer\_email

customer\_phone

string

Номер телефона клиента в формате: +79999999999
\- обязателен, если не переданы profile и vk\_user\_id

active\_manager

boolean

Статус подписки устанавливаемый менеджером
\- обязателен, если не передан active\_user **.** Значение 0 - отписан менеджером

active\_user

boolean

Статус подписки устанавливаемый пользователем\- обязателен, если не передан active\_manager . Значение 0 - отписан пользователем
\- для пользователя доступна только деактивация подписки

200 Запрос успешно обработан

400 Не передана подпись запроса

Copy

```
success
```

Copy

```
signature not found in request
```

**Пример запроса:**

Copy

```
header('Content-type:text/plain;charset=utf-8');

require_once __DIR__ . '/Hmac.php';

$url = 'https://demo.payform.ru/rest/setActivity/';
$secret_key = '2y2aw4oknnke80bp1a8fniwuuq7tdkwmmuq7vwi4nzbr8z1182ftbn6p8mhw3bhz';

$data = [\
  'subscription' => 1,\
  'vk_user_id' => 123,\
  'active_manager' => 0\
];

$data['signature'] = Hmac::create($data, $secret_key);

$ch = curl_init($url);

curl_setopt_array($ch, [\
	CURLOPT_SSL_VERIFYPEER => false,\
	CURLOPT_SSL_VERIFYHOST => false,\
	CURLOPT_RETURNTRANSFER => true,\
	CURLOPT_POSTFIELDS => http_build_query($data)\
]);

$response = curl_exec($ch);
```

file-download

1KB

[Hmac.php](https://4061190562-files.gitbook.io/~/files/v0/b/gitbook-legacy-files/o/assets%2F-M5pHt5axogA0zyX7V6_%2F-MIUcYNmNYoLCbO07FSa%2F-MIUcge6O0UqlW3S8wh4%2FHmac.php?alt=media&token=3360c7ee-4175-40ca-92de-488fbcc3dd2e)

downloadDownload [arrow-up-right-from-squareOpen](https://4061190562-files.gitbook.io/~/files/v0/b/gitbook-legacy-files/o/assets%2F-M5pHt5axogA0zyX7V6_%2F-MIUcYNmNYoLCbO07FSa%2F-MIUcge6O0UqlW3S8wh4%2FHmac.php?alt=media&token=3360c7ee-4175-40ca-92de-488fbcc3dd2e)

Библиотека Hmac.php

circle-info

Информация носит исключительно справочный характер и не является офертой. С актуальной редакцией оферты и тарифами Вы можете ознакомиться в разделе " [Документыarrow-up-right](https://prodamus.ru/documents)".

[PreviousRest APIchevron-left](https://help.prodamus.ru/payform/integracii/rest-api-1) [NextУправление скидкой по подпискеchevron-right](https://help.prodamus.ru/payform/integracii/rest-api-1/setsubscriptiondiscount)

Last updated 2 days ago

This site uses cookies to deliver its service and to analyze traffic. By browsing this site, you accept the [privacy policy](https://policies.gitbook.com/privacy/cookies).

close

AcceptReject

---

# https://help.prodamus.ru/payform/uvedomleniya/kak-ustroena-otpravka-uvedomlenii-ob-oplate

Рассказываем, какие типы уведомлений об оплате есть в Prodamus и объясняем, как они устроены.

**SMS-уведомления.** Отправляются на номера, которые вы укажете в настройках платёжной страницы в поле «Номера телефонов для уведомлений».

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2Flh5.googleusercontent.com%2FWVFZwlEWyuz78BLFiZTc__nKr2dk5TOGXZussj1qocyyp0pfkvgrzujb3qobG5TwZCcem2arKf9elDa_FSLpwFj3rVC6IiXLJffN27qwWNFLLNhjXrLChg7C402dPTqYmKMRVP0U12iayGXDoObvzjU&width=768&dpr=3&quality=100&sign=8137bb09&sv=2)

Услуга отправки СМС уведомлений платная. Стоимость одного оповещения — от двух до семи рублей. Точная стоимость зависит от объёма отправляемого сообщения и вашего оператора связи.

👉 [Инструкция: как подключить уведомления об оплатах через СМСarrow-up-right](https://help.prodamus.ru/payform/uvedomleniya/uvedomleniya-v-sms-coobsheniyakh)

**E-mail уведомления.** Отправляются на адреса менеджеров, которые вы укажете в настройках платёжной страницы в поле «email адреса для уведомлений».

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2Flh5.googleusercontent.com%2FNSeUjG2vlK9T-moxFHetbUdp4gk6A5dEbyFgDgQDuHawkd1qrO79RpP1U9Op6PNmYNe3ro_XmR3vSiqhoGRA4gKTHNBHemwyzvYUngIaCdqUwpCuotxyG3W5li3QZuIop9Qj3NsATdA28Bm0Q0MR64M&width=768&dpr=3&quality=100&sign=989a1d3&sv=2)

👉 [Инструкция: как получать уведомления об оплатах на emailarrow-up-right](https://help.prodamus.ru/payform/uvedomleniya/email)

**Веб-хук уведомления.** Отправляются на URL-адреса, которые вы укажете в настройках платёжной страницы в поле «URL-адреса для уведомлений».

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2Flh6.googleusercontent.com%2F9eqr8vavZP183n8_tOmy492DNqix-_ImkyzZqjYchggivAVDYuLPyEKbODZVJ56ptg7QgYP4jY42Y1XWS8H59_Ne4va18qYXriLjFO5DcbeNEJU_xqar_88d1vttva9bI6ejlGrVRPuRmP8n9mjBUxA&width=768&dpr=3&quality=100&sign=64be2244&sv=2)

👉 [Инструкция: как настроить получение уведомлений об оплатах на URL-адресarrow-up-right](https://help.prodamus.ru/payform/uvedomleniya/uvedomleniyakh-na-url-adres)

Веб-хук отправляется POST-запросом в формате multipart/form-data. При успешной обработке запроса ответ должен быть передан с HTTP-кодом 200. В противном случае будут предприняты повторные попытки отправки веб-хука. После успешной обработки отправка уведомлений прекращается.

👉 [Частота отправки URL-уведомлений при неудачной обработке веб-хукаarrow-up-right](https://help.prodamus.ru/payform/uvedomleniya/intervaly-uvedomlenii)

chevron-rightПример URL-уведомления [hashtag](https://help.prodamus.ru/payform/uvedomleniya/kak-ustroena-otpravka-uvedomlenii-ob-oplate#primer-url-uvedomleniya)

**Заголовок:**

Sign: b20d453561eccafb6874d95a986449f2185df25e3f0237319976df6d788342e6

**Тело запроса:**

array (

'date' => '2020-07-27T12:31:01+03:00',

'order\_id' => '300155',

'order\_num' => 'test',

'domain' => 'demo.payform.ru',

'sum' => '100.00',

'customer\_phone' => '+79999999999',

'customer\_email' => 'test@domain.ru',

'customer\_extra' => 'тест',

'payment\_type' => 'Пластиковая карта Visa, MasterCard, МИР',

'commission' => '3.5',

'commission\_sum' => '0.03',

'attempt' => '1',

'sys' => 'demo',

'vk\_user\_id' => '1234567890',

'products' => array (

0 => array (

'name' => 'Доступ в клуб "Девелопер клаб"',

'price' => '100.00',

'quantity' => '1',

'sum' => '100.00',

),

),

'payment\_status' => 'success',

'payment\_status\_description' => 'Успешная оплата'

)

Чтобы протестировать отправку запроса, перейдите в «Настройки» → «Настройки уведомлений» и нажмите на 🔁.

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2Flh3.googleusercontent.com%2F-gMoZIpaC71TYyU_QB8-_hlDCw5mohk2jYzHbTzVZ_hhTXVMMdNJpVWBVeP3qk0SbVxryzz7TTfzTEemCd8A5t2D9c1vClWee88htRY2Le2f8OQJaUfnsJA-JHN9F4hv54vnzY1_OPFR5qW6AVv-wTo&width=768&dpr=3&quality=100&sign=4170aeb0&sv=2)

Выберите тип уведомления, который хотите протестировать, и нажмите «Отправить».

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2Flh6.googleusercontent.com%2F2cw3Ig5yqptYCzYHjYWkoNPT0tuN0sOUR9AIzZsm1X0VJ2PuQORyY2wg2QoEsutxDGCP5Rp-25FzLXc8O6z-7-84os20R9usSgdWcGXfYfL5ixU_7gRFYwlIc3-fvzEUMvenUT5ILgt555lJVjwmyEQ&width=768&dpr=3&quality=100&sign=3fcdcec2&sv=2)

chevron-rightОписание параметров запроса [hashtag](https://help.prodamus.ru/payform/uvedomleniya/kak-ustroena-otpravka-uvedomlenii-ob-oplate#opisanie-parametrov-zaprosa)

Date — дата платежа
Order\_id — ID заказа в системе Prodamus
Order\_num — номер заказа на стороне магазина
Domain — домен платежной страницы
Sum — сумма заказа
Customer\_phone — номер телефона клиента
Customer\_email — e-mail клиента
Vk\_user\_id — вк id клиента
Customer\_extra — дополнительные данные
Payment\_type — метод оплаты
Commission — процент комиссии
Commission\_sum — сумма комиссии
Attempt — номер попытки отправки текущего уведомления
Sys — код системы интернет-магазина
Products — корзина товаров
Name — наименование товара
Price — цена товара
Quantity — количество товара
Sum — сумма
Payment\_init — источник оплаты. Api — оплата произведена по токену через API. Auto — оплата произведена роботом (автоплатеж при подписке). Manual — оплата произведена клиентом.
Payment\_status — статус оплаты. Success — заказ успешно оплачен. Order\_canceled — заявка отменена покупателем. Order\_denied — заявка отклонена банком (отказ в рассрочке).
Payment\_status\_description — расшифровка статуса оплаты.

При желании вы можете инициировать отправление запроса вручную. Для этого перейдите в раздел «Список платежей». Нажмите на ID нужного заказа и кликните на 🗘 в блоке «URL-оповещения».

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2Flh3.googleusercontent.com%2F80zXCLOxeygVcRlLTAm9OVafM_cCR0MpH-mirAeKyLkd3wk88tRK_tRdQoXXL8-YqLNDiLD57q0QiYVO0JHeaHgKTMJCWuxGU0VGjkcFraxTKqExHkXwvO2uN5uUcBRSyMb7Nk4keZ-tBbz-M2uV9EU&width=768&dpr=3&quality=100&sign=854ab82&sv=2)

После ручной отправки запроса напротив даты платежа появится иконка 👤.

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2Flh6.googleusercontent.com%2FcxDuOlWcHpnzoi_wuejCRCDHicmo2U5fb1WBK9mDsSkjqDJMU38qpoNQ-WNHsWFjeIsUNzcjntIEWG46z-rsW_-0BM5P22qP1AWmNKYO6UBjhp6_SCuI84AM_s4kc1oTGcoPngBcR_JY9BbZevP5gjo&width=768&dpr=3&quality=100&sign=60ddeac4&sv=2)

[PreviousУведомления при оплатеchevron-left](https://help.prodamus.ru/payform/uvedomleniya) [NextКак получать уведомления об оплатах на emailchevron-right](https://help.prodamus.ru/payform/uvedomleniya/email)

Last updated 2 days ago

This site uses cookies to deliver its service and to analyze traffic. By browsing this site, you accept the [privacy policy](https://policies.gitbook.com/privacy/cookies).

close

AcceptReject

---

# https://help.prodamus.ru/payform/uvedomleniya

[Как устроена отправка уведомлений об оплатеchevron-right](https://help.prodamus.ru/payform/uvedomleniya/kak-ustroena-otpravka-uvedomlenii-ob-oplate) [Как получать уведомления о подписках на URL-адресchevron-right](https://help.prodamus.ru/payform/rekurrent-i-kluby/kak-poluchat-uvedomleniya-o-podpiskakh-na-url-adres) [Как получать уведомления об оплатах на emailchevron-right](https://help.prodamus.ru/payform/uvedomleniya/email) [Как получать уведомления об оплатах через СМСchevron-right](https://help.prodamus.ru/payform/uvedomleniya/uvedomleniya-v-sms-coobsheniyakh) [Интервалы уведомленийchevron-right](https://help.prodamus.ru/payform/uvedomleniya/intervaly-uvedomlenii)

[PreviousКак посмотреть неоплаченные заказыchevron-left](https://help.prodamus.ru/payform/kak-uvidet-oplaty.-bukhotchetnost/kak-posmotret-neoplachennye-zakazy) [NextКак устроена отправка уведомлений об оплатеchevron-right](https://help.prodamus.ru/payform/uvedomleniya/kak-ustroena-otpravka-uvedomlenii-ob-oplate)

Last updated 2 days ago

This site uses cookies to deliver its service and to analyze traffic. By browsing this site, you accept the [privacy policy](https://policies.gitbook.com/privacy/cookies).

close

AcceptReject

---

# https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/uvedomleniya-pri-avtospisanii

При автосписании по подписке будут отправлены следующие типы уведомлений:

- веб-хук на URL адрес, указанный на странице настроек платежной формы, в блоке "Настройка уведомлений"

- e-mail уведомление на адреса менеджеров, указанных на странице настроек подписок, в блоке "Общие настройки"


**Пример URL уведомления:**

_Заголовок:_

Copy

```
Sign: b20d453561eccafb6874d95a986449f2185df25e3f0237319976df6d788342e6
```

_Тело запроса:_

Copy

```
array (
  'date' => '2020-07-27T12:36:02+03:00',
  'order_id' => '300169',
  'order_num' => '',
  'domain' => 'demo.payform.ru',
  'sum' => '100.00',
  'customer_phone' => '+79999999999',
  'customer_email' => 'test@domain.ru',
  'customer_extra' => '',
  'payment_type' => 'Автоплатеж',
  'attempt' => '1',
  'commission' => '3.9',
  'commission_sum' => '0.04',
  'discount_value' => '0.00',
  'subscription' =>
  array (
    'type' => 'action',
    'action_code' => 'auto_payment',
    'payment_date' => '2020-07-27 12:35',
    'id' => '593600',
    'active' => '1',
    'active_manager' => '1',
    'active_user' => '1',
    'cost' => '100.00',
    'name' => 'Доступ в клуб "Девелопер клаб" – тестовая подписка',
    'limit_autopayments' => '',
    'autopayments_num' => '1',
    'first_payment_discount' => '0.00',
    'next_payment_discount' => '0.00',
    'next_payment_discount_num' => '',
    'date_create' => '2020-07-23 20:38:57',
    'date_first_payment' => '2020-06-27 20:38:57',
    'date_last_payment' => '2020-07-27 12:35:08',
    'date_next_payment' => '2020-08-25 12:30:37',
    'date_next_payment_discount' => '2020-07-23 20:38:57',
    'current_attempt' => '1',
    'payment_num' => '2',
    'autopayment' => '1',
  ),
)
```

Подробное описание параметров описано в разделе [Параметры URL-уведомления по подписке](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/uvedomleniya)

#### [hashtag](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/uvedomleniya-pri-avtospisanii\#primer-e-mail-uvedomleniya-menedzheru)    **Пример e-mail уведомления менеджеру:**

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-legacy-files%2Fo%2Fassets%252F-M5pHt5axogA0zyX7V6_%252F-MDEsn5CpWdEkQUFT7aR%252F-MDEu0OB3DZzzk791V93%252Fimage.png%3Falt%3Dmedia%26token%3D5b678cb2-047f-42a8-89e3-45f5e53d17b8&width=768&dpr=3&quality=100&sign=8ce4fea5&sv=2)

circle-info

Информация носит исключительно справочный характер и не является офертой. С актуальной редакцией оферты и тарифами Вы можете ознакомиться в разделе " [Документыarrow-up-right](https://prodamus.ru/documents)".

[PreviousЗавершение подпискиchevron-left](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/zavershenie-podpiski) [NextДеактивация и повторная активация подпискиchevron-right](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/deaktivaciya-i-povtornaya-aktivaciya-podpiski)

Last updated 2 days ago

This site uses cookies to deliver its service and to analyze traffic. By browsing this site, you accept the [privacy policy](https://policies.gitbook.com/privacy/cookies).

close

AcceptReject

---

# https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham

- [Формирование ссылки на оплату](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/formirovanie-ssylki-na-oplatu)

- [Управление клубным функционалом](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/untitled)

- [Завершение подписки](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/zavershenie-podpiski)

- [Уведомления при автосписании](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/uvedomleniya-pri-avtospisanii)

- [Параметры URL-уведомления по подписке](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/uvedomleniya)

- [Коды ошибок](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/kody-oshibok)


[PreviousДокументация для самостоятельной интеграции сервисовchevron-left](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov) [NextФормирование ссылки на оплатуchevron-right](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/formirovanie-ssylki-na-oplatu)

Last updated 2 days ago

This site uses cookies to deliver its service and to analyze traffic. By browsing this site, you accept the [privacy policy](https://policies.gitbook.com/privacy/cookies).

close

AcceptReject

---

# https://help.prodamus.ru/payform/uvedomleniya/email

Если вы хотите изменить адрес электронной почты, на который будут приходить уведомления о платежах клиентов, следуйте инструкции ниже.

### [hashtag](https://help.prodamus.ru/payform/uvedomleniya/email\#h.ajpwf5q9vr8r)    Шаг 1\. Авторизуйтесь на платёжной странице и перейдите в раздел «Настройки»

👉 [Инструкция: как авторизоваться на платёжной страницеarrow-up-right](https://www.google.com/url?q=https://help.prodamus.ru/payform/nastroika-platezhnoi-stranicy/kak-avtorizovatsya-na-platyozhnoi-stranice&sa=D&source=editors&ust=1685379391733683&usg=AOvVaw1KtrR2umE76vWtVKUCtJGS)

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252F-M5pHt5axogA0zyX7V6_%252Fuploads%252F1x4SBdppLkYKrVJdLcRT%252Fimage.png%3Falt%3Dmedia%26token%3D7734d233-8b44-41c3-aeb2-63dd9bb5eeee&width=768&dpr=3&quality=100&sign=ec9a4a01&sv=2)

### [hashtag](https://help.prodamus.ru/payform/uvedomleniya/email\#h.3kuz4lf1t1na)    Шаг 2\. Заполните поле «e-mail адреса для уведомлений»

Укажите адрес электронной почты, на который Prodamus будет отправлять уведомления об оплатах. Если хотите получать оповещения на несколько адресов, нажмите на кнопку «+» и введите другие адреса.

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252F-M5pHt5axogA0zyX7V6_%252Fuploads%252FtmOOxjtgvxrWpnAp0Cbz%252Fimage1.gif%3Falt%3Dmedia%26token%3D60d40fb5-c1b5-4e44-983e-d2210a27a507&width=768&dpr=3&quality=100&sign=43899edd&sv=2)

circle-info

**Важно.** В редких случаях уведомление об оплате может не прийти на email-адрес или попасть в папку «Спам». Если оповещение не пришло, отследить платёж можно в личном кабинете Prodamus в разделе «Список платежей».

👉 [Как посмотреть и скачать данные по платежам клиентовarrow-up-right](https://www.google.com/url?q=https://help.prodamus.ru/payform/kak-uvidet-oplaty.-bukhotchetnost/kak-prosmotret-spisok-oplat-i-sformirovat-otchet-agenta&sa=D&source=editors&ust=1685379391736362&usg=AOvVaw0vxjN_zpbTEfJ-8m5IY592)

### [hashtag](https://help.prodamus.ru/payform/uvedomleniya/email\#h.xlz3ttvfrc7r)    Шаг 3\. Нажмите кнопку «Сохранить»

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252F-M5pHt5axogA0zyX7V6_%252Fuploads%252FnZcDET0jfkPYBHlNuO4q%252Fimage.png%3Falt%3Dmedia%26token%3D89396443-9d76-4686-ae78-3f791a9c01ae&width=768&dpr=3&quality=100&sign=c5d42d46&sv=2)

**Пример уведомления:**

![](https://help.prodamus.ru/~gitbook/image?url=https%3A%2F%2F4061190562-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252F-M5pHt5axogA0zyX7V6_%252Fuploads%252F9CTLt3AmTJ2Wkl4sSqnw%252Fimage.png%3Falt%3Dmedia%26token%3D0e787826-22d2-4651-8c58-54b1d999bca7&width=768&dpr=3&quality=100&sign=4e7fc44c&sv=2)

circle-info

Информация носит исключительно справочный характер и не является офертой. С актуальной редакцией оферты и тарифами Вы можете ознакомиться в разделе " [Документыarrow-up-right](https://prodamus.ru/documents)".

[PreviousКак устроена отправка уведомлений об оплатеchevron-left](https://help.prodamus.ru/payform/uvedomleniya/kak-ustroena-otpravka-uvedomlenii-ob-oplate) [NextКак получать уведомления об оплатах через СМСchevron-right](https://help.prodamus.ru/payform/uvedomleniya/uvedomleniya-v-sms-coobsheniyakh)

Last updated 2 days ago

This site uses cookies to deliver its service and to analyze traffic. By browsing this site, you accept the [privacy policy](https://policies.gitbook.com/privacy/cookies).

close

AcceptReject

---

# https://help.prodamus.ru/payform/uvedomleniya/intervaly-uvedomlenii

Все уведомления делятся на три типа:

- e-mail уведомления

- sms уведомления

- url уведомления


Если по какой-то причине, одно или несколько уведомлений не было отправлено, будет предпринято определенное количество повторных попыток отправки через определенный интервал, в зависимости от типа уведомления.

Ниже представлена таблица с интервалами уведомлений по каждому типу:

№

E-mail

SMS

URL

1

3 мин.

3 мин.

1 мин.

2

10 мин.

10 мин.

1 мин.

3

30 мин.

30 мин.

1 мин.

4

60 мин.

60 мин.

5 мин.

5

-

-

5 мин.

6

-

-

5 мин.

7

-

-

10 мин.

8

-

-

10 мин.

9

-

-

10 мин.

10

-

-

30 мин.

11

-

-

30 мин.

12

-

-

30 мин.

13

-

-

1 ч.

14

-

-

1 ч.

15

-

-

1 ч.

16

-

-

3 ч.

17

-

-

3 ч.

18

-

-

3 ч.

19

-

-

6 ч.

20

-

-

6 ч.

21

-

-

6 ч.

22

-

-

12 ч.

23

-

-

24 ч.

circle-info

Информация носит исключительно справочный характер и не является офертой. С актуальной редакцией оферты и тарифами Вы можете ознакомиться в разделе " [Документыarrow-up-right](https://prodamus.ru/documents)".

[PreviousКак получать уведомления об оплатах на URL-адресchevron-left](https://help.prodamus.ru/payform/uvedomleniya/uvedomleniyakh-na-url-adres) [NextВозвраты платежейchevron-right](https://help.prodamus.ru/payform/vozvraty-platezhei)

Last updated 2 days ago

This site uses cookies to deliver its service and to analyze traffic. By browsing this site, you accept the [privacy policy](https://policies.gitbook.com/privacy/cookies).

close

AcceptReject

---

# https://help.prodamus.ru/payform/integracii/rest-api-1

**Формат запроса:** https://{домен}/rest/{метод api}/

**Метод запроса:** GET или POST

**Доступные методы:**

- [setActivity](https://help.prodamus.ru/payform/integracii/rest-api-1/setactivity) — активация/деактивация подписки

- [setSubscriptionDiscount](https://help.prodamus.ru/payform/integracii/rest-api-1/setsubscriptiondiscount) — установка скидки на следующие списания по подписке

- [setSubscriptionPaymentDate](https://help.prodamus.ru/payform/integracii/rest-api-1/setsubscriptionpaymentdate) — установка следующей даты списания по подписке


[PreviousКоды ошибокchevron-left](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/kody-oshibok) [NextУправление статусами подпискиchevron-right](https://help.prodamus.ru/payform/integracii/rest-api-1/setactivity)

Last updated 2 days ago

This site uses cookies to deliver its service and to analyze traffic. By browsing this site, you accept the [privacy policy](https://policies.gitbook.com/privacy/cookies).

close

AcceptReject

---

# https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/kody-oshibok

Код ошибки

Текст ошибки в хуке/письме

Рекомендация

card\_expired

Срок действия карты истёк.

Перевыпустите карту и попробуйте оплатить снова. Оплата по связкам после перевыпуска карты не всегда возможна. Если оплата не прошла, подписку необходимо будет оформить повторно.

operation\_rejected

Операция отклонена. Обратитесь в банк, выпустивший карту.

Банк-эмитент отклонил операцию по неизвестной причине. За подробностями необходимо обратиться в банк выпустивший карту.

insufficient\_funds

Недостаточно средств.

Недостаточно средств на счету для проведения операции. Необходимо пополнить счет.

operation\_denied

Отказ в проведении операции банком эмитентом.

Банк-эмитент отклонил операцию по неизвестной причине. За подробностями необходимо обратиться в банк выпустивший карту.

card\_limit

Превышен лимит по карте.

Превышен лимит на сумму или количество операций за определенный период. За более подробной информацией необходимо обратиться в банк-эмитент.

card\_lost

Карта утеряна

Карта заблокирована по причине ее утери.

3ds\_error

Отказ в проведении операции банком.

Ошибка при попытке списания по связке полученной при оплате через ApplePay/GooglePay. Автосписание по такой связке не возможно.

system\_error

Системная ошибка

Не обработанное исключение. За подробностями необходимо обратиться к менеджерам.

circle-info

Информация носит исключительно справочный характер и не является офертой. С актуальной редакцией оферты и тарифами Вы можете ознакомиться в разделе " [Документыarrow-up-right](https://prodamus.ru/documents)".

[PreviousПараметры URL-уведомления по подпискеchevron-left](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/uvedomleniya) [NextRest APIchevron-right](https://help.prodamus.ru/payform/integracii/rest-api-1)

Last updated 2 days ago

This site uses cookies to deliver its service and to analyze traffic. By browsing this site, you accept the [privacy policy](https://policies.gitbook.com/privacy/cookies).

close

AcceptReject

---

# https://help.prodamus.ru/payform/integracii/rest-api

- [Где найти url для уведомлений и секретный ключ](https://help.prodamus.ru/payform/integracii/rest-api/url-dlya-uvedomlenii-i-sekretnyi-klyuch)

- [Инструкция для самостоятельной интеграции сервисов для тех.специалистов](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov)


circle-check

Если что-то в документации не понятно, у вас остались вопросы или вам нужна помощь, пишите или звоните нам

по телефону: `8 (495) 150-08-71`

в личные сообщения группы в VK: [https://vk.com/im?sel=-11636316arrow-up-right](https://vk.com/im?sel=-11636316)

на электронную почту: [sales@prodamus.ruenvelope](mailto:sales@prodamus.ru)

в боте в MAX: [https://max.ru/id1215156909\_2\_botarrow-up-right](https://t.me/prodamus_bot)

[PreviousПриложение и примеры работы для VKchevron-left](https://help.prodamus.ru/payform/integracii/prilozhenie-i-primery-raboty-dlya-vk) [NextГде найти url для уведомлений и секретный ключchevron-right](https://help.prodamus.ru/payform/integracii/rest-api/url-dlya-uvedomlenii-i-sekretnyi-klyuch)

Last updated 2 days ago

This site uses cookies to deliver its service and to analyze traffic. By browsing this site, you accept the [privacy policy](https://policies.gitbook.com/privacy/cookies).

close

AcceptReject

---

# https://help.prodamus.ru/payform/integracii/rest-api-1/setsubscriptiondiscount

Задает размер скидки на следующие платежи по подписке. Скидка может быть установлена на ограниченное и не ограниченное количество списаний.

## [hashtag](https://help.prodamus.ru/payform/integracii/rest-api-1/setsubscriptiondiscount\#setsubscriptiondiscount)    setSubscriptionDiscount

`POST``https://demo.payform.ru/rest/setSubscriptionDiscount/`

#### [hashtag](https://help.prodamus.ru/payform/integracii/rest-api-1/setsubscriptiondiscount\#query-parameters)    Query Parameters

Name

Type

Description

signature\*

string

Подпись запроса

subscription\*

integer

ID подписки

profile

integer

ID профиля клиента
\- обязателен, если не передан один из параметров vk\_user\_id/tg\_user\_id/customer\_phone/customer\_emai

vk\_user\_id

integer

ID профиля клиента ВКонтакте
\- обязателен, если не передан один из параметров profile/tg\_user\_id/customer\_phone/customer\_email

customer\_phone

String

Номер телефона клиента в формате: +79999999999
\- обязателен, если не переданы profile и vk\_user\_id

discount\_value

number

Размер скидки
\- десятичное число с точностью до двух знаков после точки
\- значение должно быть больше нуля и не превышать базовую стоимость подписки

num

integer

Количество оплат на которые будет действовать скидка
\- по умолчанию: 0 (количество оплат со скидкой не ограничено)

tg\_user\_id

integer

ID профиля клиента Telegram
\- обязателен, если не передан один из параметров vk\_user\_id/profile/customer\_phone/customer\_email

customer\_email

String

Email клиента
\- обязателен, если не передан один из параметров vk\_user\_id/tg\_user\_id/customer\_phone/profile

200 Запрос успешно обработан

400 Не передана подпись запроса

Copy

```
success
```

Copy

```
signature not found in request
```

**Примеры запроса:**

Copy

```
header('Content-type:text/plain;charset=utf-8');

require_once __DIR__ . '/Hmac.php';

$url = 'https://demo.payform.ru/rest/setSubscriptionDiscount/';
$secret_key = '2y2aw4oknnke80bp1a8fniwuuq7tdkwmmuq7vwi4nzbr8z1182ftbn6p8mhw3bhz';

$data = [\
  'subscription' => 1,\
  'customer_phone' => '+79999999999',\
  'discount_value' => 1000\
];

$data['signature'] = Hmac::create($data, $secret_key);

$ch = curl_init($url);

curl_setopt_array($ch, [\
	CURLOPT_SSL_VERIFYPEER => false,\
	CURLOPT_SSL_VERIFYHOST => false,\
	CURLOPT_RETURNTRANSFER => true,\
	CURLOPT_POSTFIELDS => http_build_query($data)\
]);

$response = curl_exec($ch);
```

file-download

1KB

[Hmac.php](https://4061190562-files.gitbook.io/~/files/v0/b/gitbook-legacy-files/o/assets%2F-M5pHt5axogA0zyX7V6_%2F-MIUcYNmNYoLCbO07FSa%2F-MIUcge6O0UqlW3S8wh4%2FHmac.php?alt=media&token=3360c7ee-4175-40ca-92de-488fbcc3dd2e)

downloadDownload [arrow-up-right-from-squareOpen](https://4061190562-files.gitbook.io/~/files/v0/b/gitbook-legacy-files/o/assets%2F-M5pHt5axogA0zyX7V6_%2F-MIUcYNmNYoLCbO07FSa%2F-MIUcge6O0UqlW3S8wh4%2FHmac.php?alt=media&token=3360c7ee-4175-40ca-92de-488fbcc3dd2e)

Библиотека Hmac.php

circle-info

Информация носит исключительно справочный характер и не является офертой. С актуальной редакцией оферты и тарифами Вы можете ознакомиться в разделе " [Документыarrow-up-right](https://prodamus.ru/documents)".

[PreviousУправление статусами подпискиchevron-left](https://help.prodamus.ru/payform/integracii/rest-api-1/setactivity) [NextУстановка даты следующего платежа по подпискеchevron-right](https://help.prodamus.ru/payform/integracii/rest-api-1/setsubscriptionpaymentdate)

Last updated 2 days ago

This site uses cookies to deliver its service and to analyze traffic. By browsing this site, you accept the [privacy policy](https://policies.gitbook.com/privacy/cookies).

close

AcceptReject

---

# https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/untitled

Управление клубным функционалом осуществляется при помощи методов [Rest API](https://help.prodamus.ru/payform/integracii/rest-api-1)

- [Управление статусами подписки](https://help.prodamus.ru/payform/integracii/rest-api-1/setactivity)

- [Управление скидкой по подписке](https://help.prodamus.ru/payform/integracii/rest-api-1/setsubscriptiondiscount)

- [Установка даты следующего платежа по подписке](https://help.prodamus.ru/payform/integracii/rest-api-1/setsubscriptionpaymentdate)


[PreviousФормирование ссылки на оплатуchevron-left](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/formirovanie-ssylki-na-oplatu) [NextЗавершение подпискиchevron-right](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/zavershenie-podpiski)

Last updated 2 days ago

This site uses cookies to deliver its service and to analyze traffic. By browsing this site, you accept the [privacy policy](https://policies.gitbook.com/privacy/cookies).

close

AcceptReject

---

# https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/formirovanie-ssylki-na-oplatu

Данные запроса для формирования ссылки на оплату передаются методом GET или POST в кодировке UTF-8 на URL-адрес платежной формы в системе Продамус.

Адрес демо-формы: [https://demo.payform.ruarrow-up-right](https://demo.payform.ru/)

Секретный ключ демо-формы: 2y2aw4oknnke80bp1a8fniwuuq7tdkwmmuq7vwi4nzbr8z1182ftbn6p8mhw3bhz

circle-info

Список доступных параметров Вы можете найти на странице [инструкции для самостоятельной интеграции](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov).

Пример формирования ссылки на оплату:

Copy

```
<?php

header('Content-type:text/plain;charset=utf-8');

$linktoform = 'https://demo.payform.ru/';

$data = [\
	'order_id' => '',\
	'customer_phone' => '+79278820060',\
	'customer_email' => 'site_testing@prodamus.ru',\
	'subscription' => 1,\
	'vk_user_id' => 12345,\
	'vk_user_name' => 'Фамилия Имя Отчество',\
	'customer_extra' => '',\
	'do' => 'link',\
	'urlReturn' => 'https://demo.payform.ru/demo-return',\
	'urlSuccess' => 'https://demo.payform.ru/demo-success',\
	'sys' => 'getcourse',\
	'discount_value' => 100.00,\
	'link_expired' => '2021-01-01 00:00:00',\
	'subscription_date_start' => '2021-01-01 00:00:00',\
	'subscription_limit_autopayments' => 10\
];

$link = file_get_contents($linktoform . '?' . http_build_query($data));
```

circle-info

Информация носит исключительно справочный характер и не является офертой. С актуальной редакцией оферты и тарифами Вы можете ознакомиться в разделе " [Документыarrow-up-right](https://prodamus.ru/documents)".

[PreviousТехническая документация по автоплатежамchevron-left](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham) [NextУправление клубным функционаломchevron-right](https://help.prodamus.ru/payform/integracii/tekhnicheskaya-dokumentaciya-po-avtoplatezham/untitled)

Last updated 2 days ago

This site uses cookies to deliver its service and to analyze traffic. By browsing this site, you accept the [privacy policy](https://policies.gitbook.com/privacy/cookies).

close

AcceptReject

---

# https://help.prodamus.ru/payform/integracii/rest-api-1/setsubscriptionpaymentdate

С помощью данного метода можно сдвинуть дату следующего платежа по подписке. Сдвигать дату можно только "в будущее" относительно текущей установленной даты следующего платежа. Тем самым увеличивая срок пребывания в клубе.

_Например, можно применять в качестве бонуса для подписчиков_

## [hashtag](https://help.prodamus.ru/payform/integracii/rest-api-1/setsubscriptionpaymentdate\#setsubscriptionpaymentdate)    setSubscriptionPaymentDate

`POST``https://demo.payform.ru/rest/setSubscriptionPaymentDate/`

#### [hashtag](https://help.prodamus.ru/payform/integracii/rest-api-1/setsubscriptionpaymentdate\#query-parameters)    Query Parameters

Name

Type

Description

auth\_type

string

Тип идентификации клиента. Возможные значения:
\- profile – id профиля в системе Продамус
\- vk\_user\_id – id профиля ВК
\- customer\_phone – номер телефона клиента

signature

string

Подпись запроса

subscription

integer

ID подписки

profile

integer

ID профиля клиента в системе Продамус. Обязателен, если значение параметра auth\_type = profile

vk\_user\_id

integer

ID профиля клиента ВКонтакте. Обязателен, если значение параметра auth\_type = vk\_user\_id

customer\_phone

string

Номер телефона клиента в формате: +79999999999/
Обязателен, если значение параметра auth\_type = customer\_phone

date

string

Устанавливаемая дата следующего платежа
\- дата в формате: гггг\-мм\-дд чч:мм
\- дата не может быть в прошлом или раньше расчетной даты следующего платежа

200 Запрос успешно обработан

400 Не передана подпись запроса

Copy

```
success
```

Copy

```
signature not found in request
```

**Пример запроса:**

Copy

```
header('Content-type:text/plain;charset=utf-8');

require_once __DIR__ . '/Hmac.php';

$url = 'https://demo.payform.ru/rest/setSubscriptionPaymentDate/';
$secret_key = '2y2aw4oknnke80bp1a8fniwuuq7tdkwmmuq7vwi4nzbr8z1182ftbn6p8mhw3bhz';

$data = [\
  'subscription' => 1,\
  'auth_type' => 'vk_user_id',\
  'vk_user_id' => 123,\
  'date' => '2021-12-31 23:59'\
];

$data['signature'] = Hmac::create($data, $secret_key);

$ch = curl_init($url);

curl_setopt_array($ch, [\
	CURLOPT_SSL_VERIFYPEER => false,\
	CURLOPT_SSL_VERIFYHOST => false,\
	CURLOPT_RETURNTRANSFER => true,\
	CURLOPT_POSTFIELDS => http_build_query($data)\
]);

$response = curl_exec($ch);
```

file-download

1KB

[Hmac.php](https://4061190562-files.gitbook.io/~/files/v0/b/gitbook-legacy-files/o/assets%2F-M5pHt5axogA0zyX7V6_%2F-MIUcYNmNYoLCbO07FSa%2F-MIUcge6O0UqlW3S8wh4%2FHmac.php?alt=media&token=3360c7ee-4175-40ca-92de-488fbcc3dd2e)

downloadDownload [arrow-up-right-from-squareOpen](https://4061190562-files.gitbook.io/~/files/v0/b/gitbook-legacy-files/o/assets%2F-M5pHt5axogA0zyX7V6_%2F-MIUcYNmNYoLCbO07FSa%2F-MIUcge6O0UqlW3S8wh4%2FHmac.php?alt=media&token=3360c7ee-4175-40ca-92de-488fbcc3dd2e)

Библиотека Hmac.php

circle-info

Информация носит исключительно справочный характер и не является офертой. С актуальной редакцией оферты и тарифами Вы можете ознакомиться в разделе " [Документыarrow-up-right](https://prodamus.ru/documents)".

[PreviousУправление скидкой по подпискеchevron-left](https://help.prodamus.ru/payform/integracii/rest-api-1/setsubscriptiondiscount) [NextПартнёрская программаchevron-right](https://help.prodamus.ru/partnyorskaya-programma)

Last updated 2 days ago

This site uses cookies to deliver its service and to analyze traffic. By browsing this site, you accept the [privacy policy](https://policies.gitbook.com/privacy/cookies).

close

AcceptReject

---
