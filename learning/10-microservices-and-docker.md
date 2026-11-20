<style>
body, .markdown-body { direction: rtl; text-align: right; line-height: 1.85; }
h1, h2, h3, h4, h5, h6, p, ul, ol, li, table, th, td { direction: rtl; text-align: right; }
pre, pre code { direction: ltr !important; text-align: left !important; unicode-bidi: embed; }
code { direction: ltr; unicode-bidi: isolate; }
</style>

# فاز ۸: معماری Modular Monolith در برابر Microservices و Docker (`10-microservices-and-docker.md`)

---

## 1. What is this technology? (این تکنولوژی چیست؟)

- **Modular Monolith (مونولیت ماژولار):** معماری‌ای که در آن کل سیستم در یک پروسه و یک مخزن کد (`Single Deployment Unit`) مستقر می‌شود، اما کدها به ماژول‌های کاملاً مستقل با مرزهای مشخص (`core`, `devices`, `simulation`, `database`, `api`, `reporting`) تقسیم شده‌اند (مشابه یک اپلیکیشن Multi-Module در Android/Gradle).
- **Microservices (میکروسرویس‌ها):** معماری‌ای که در آن هر قابلیت کسب‌وکار در یک کانتینر/سرور مستقل اجرا می‌شود و از طریق شبکه (`REST / gRPC / Message Queue`) با سایر سرویس‌ها ارتباط برقرار می‌کند.
- **Docker & Docker Compose:** ابزار استاندارد بسته‌بندی نرم‌افزار و تمام وابستگی‌هایش (`Python`, `pyATS`, `OpenSSH`) در یک ایمیج یکسان (`Container Image`) و اجرای چند کانتینر مرتبط با هم.

---

## 2. Why is a Modular Monolith sufficient for our current project? (چرا Modular Monolith برای نسخه فعلی بهترین انتخاب است؟)

> **💡 سؤال کلاسیک مصاحبه System Design:**
> *«چرا پروژه را از روز اول Microservices ننوشتید؟»*

پاسخ مهندسی:
1. **حذف سربار شبکه و زیرساخت (`Zero Network Latency & Operational Overhead`):** در یک Modular Monolith، فراخوانی `HealthCheckExecutionService` از داخل `FastAPI` یک فراخوانی تابع در حافظه است (نانوثانیه)، نه یک درخواست HTTP بین دو کانتینر به همراه سریالایز کردن JSON و مدیریت خطاهای شبکه.
2. **تراکنش‌ها و دیباگ ساده:** تمام لاگ‌ها و دیتابیس در یکجا قرار دارند و بدون نیاز به Distributed Tracing (مثل Jaeger) یا Message Broker پیچیده، کل سیستم قابل تست و دیباگ است.
3. **آمادگی برای تبدیل به Microservices در آینده:** از آنجا که ما مرزهای لایه‌ها را تمیز نگه داشتیم (`api` از `core` و `devices` جداست)، هر زمان که مقیاس پروژه واقعاً نیاز داشت، می‌توانیم هر پکیج را بدون بازنویسی منطق دامنه به یک سرویس مستقل تبدیل کنیم!

---

## 3. How could the system be divided into Microservices later? (نحوه تقسیم سیستم به میکروسرویس‌ها در مقیاس بالا)

اگر سازمان شما هزاران روتر در دیتاسنترهای مختلف داشته باشد، سیستم به ۴ سرویس مستقل تقسیم می‌شود:

```text
                   ┌──────────────────────────┐
Client / UI ─────► │      1. API Service      │ (FastAPI Gateway)
                   └──────┬─────────────┬─────┘
                          │             │
         Reads Inventory  │             │ Enqueues Test Job (Redis / RabbitMQ)
                          ▼             ▼
┌─────────────────────────────┐     ┌────────────────────────────────┐
│ 2. Device Management Service│     │ 3. Test Execution Worker Fleet │ (pyATS + Genie + Unicon)
│ (Testbed & Vault Secrets)   │     └───────────────┬────────────────┘
└─────────────────────────────┘                     │
                                                    │ Writes Results
                                                    ▼
                                    ┌────────────────────────────────┐
                                    │   4. Result Storage Service    │ (PostgreSQL / TimescaleDB)
                                    └────────────────────────────────┘
```

1. **API Service:** دریافت درخواست‌های کاربران، احراز هویت، و ثبت درخواست تست در صف.
2. **Test Execution Service (Workers):** کانتینرهای حاوی `pyATS` و `Genie` که می‌توان تعداد آن‌ها را مستقل از API مقیاس‌دهی افقی (`Horizontal Scaling`) کرد.
3. **Device Management Service:** مدیریت لیست تجهیزات شبکه (`Inventory / Testbed`) و دریافت امن رمزهای عبور از HashiCorp Vault.
4. **Result Storage:** دیتابیس مرکزی برای نگهداری تاریخچه تست‌ها و گزارش‌ها.

---

## 4. Important concepts and terminology (مفاهیم و اصطلاحات مهم)

- **Dockerfile:** دستورالعمل متنی برای ساخت ایمیج کانتینر (`FROM`, `WORKDIR`, `COPY`, `RUN`, `EXPOSE`, `CMD`).
- **Docker Compose (`docker-compose.yml`):** تعریف و اجرای چند سرویس کانتینری به همراه شبکه داخلی و Volumeهای اشتراکی.
- **Docker Volume (`nhc_results_data`):** فضای ذخیره‌سازی پایدار (`Persistent Storage`) خارج از چرخه حیات کانتینر تا با ری‌استارت شدن کانتینر، دیتابیس SQLite و گزارش‌های تست پاک نشوند.

---

## 5. Explanation of each relevant source file (توضیح فایل‌های مرتبط در پروژه)

- **`docker/Dockerfile`**: ایمیج لینوکسی بر پایه `python:3.11-slim` که `openssh-client`، پکیج‌های `pyats[library]` و `fastapi/uvicorn` را نصب کرده و سرویس API را روی پورت `8000` بالا می‌آورد.
- **`docker/docker-compose.yml`**: تعریف دو سرویس کانتینری (`api-service` و `test-execution-worker`) که از طریق Volume مشترک `nhc_results_data` به پوشه `/app/reports` دسترسی دارند.

---

## 6. Explanation of important blocks in `Dockerfile` and `docker-compose.yml`

- **`FROM python:3.11-slim`**: استفاده از ایمیج رسمی و سبک Python 3.11 روی Debian.
- **`COPY requirements.txt ...` قبل از کدها در لایه‌بندی Docker:** استفاده بهینه از Docker Layer Caching تا با تغییر کدهای پایتون، مرحله زمان‌بر نصب `pyats` دوباره تکرار نشود.
- **`volumes: - nhc_results_data:/app/reports`**: اشتراک‌گذاری پایدار گزارش‌ها و فایل SQLite بین کانتینر API و کانتینر Worker.

---

## 7. Step-by-step execution flow with Docker Compose (روند اجرا با Docker)

1. ساخت ایمیج‌ها:
   ```bash
   docker compose -f docker/docker-compose.yml build
   ```
2. اجرای سرویس API و Worker اجرای تست:
   ```bash
   docker compose -f docker/docker-compose.yml up
   ```

---

## 8. Real code examples (محتوای `docker/docker-compose.yml`)

```yaml
services:
  api-service:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: nhc-api-service
    ports:
      - "8000:8000"
    environment:
      - NHC_MODE=offline
      - NHC_DATABASE_PATH=/app/reports/network_health_history.db
    volumes:
      - nhc_results_data:/app/reports

  test-execution-worker:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: nhc-test-worker
    command: ["python", "src/network_health/tests/aetest_health_check.py", "--scenario", "healthy"]
    environment:
      - NHC_MODE=offline
    volumes:
      - nhc_results_data:/app/reports

volumes:
  nhc_results_data:
```

---

## 9. Common mistakes and debugging techniques (خطاهای رایج و تکنیک‌های دیباگ)

1. **اجرای `uvicorn` روی `127.0.0.1` داخل کانتینر Docker:**
   - **خطا:** اگر داخل کانتینر برنامه به `127.0.0.1` بایند شود، از بیرون کانتینر (ماشین Host) قابل دسترسی نخواهد بود!
   - **راه‌حل:** همیشه داخل Docker از `--host 0.0.0.0` استفاده کنید (همانند خط آخر `docker/Dockerfile`).
2. **ذخیره دیتابیس SQLite داخل فایل‌سیستم موقت کانتینر بدون Volume:**
   - با حذف کانتینر (`docker compose down`) تمام تاریخچه تست‌ها از بین می‌رود مگر اینکه روی یک **Docker Volume** ذخیره شود.

---

## 10. Practical exercises (تمرین‌های عملی)

فایل‌های [docker/Dockerfile](file:///Users/hesam/.gemini/antigravity/scratch/network-health-check/docker/Dockerfile) و [docker/docker-compose.yml](file:///Users/hesam/.gemini/antigravity/scratch/network-health-check/docker/docker-compose.yml) را باز کنید و ببینید چطور یک Image واحد (`docker/Dockerfile`) با دو دستور شروع (`CMD` پیش‌فرض برای `api-service` و `command` سفارشی برای `test-execution-worker`) دو نقش میکروسرویسی متفاوت را اجرا می‌کند.

---

## 11. Expected exercise results (نتایج مورد انتظار تمرین‌ها)

درک کامل نحوه استفاده از یک ایمیج پایه مشترک برای اجرای هم‌زمان سرویس وب (`uvicorn`) و کارگر اجرای تست (`aetest_health_check.py`).

---

## 12. Short knowledge-check quiz (آزمون کوتاه سنجش دانش و مصاحبه)

1. **سؤال ۱ (مصاحبه):** سه مزیت اصلی شروع پروژه با معماری **Modular Monolith** به جای **Microservices** چیست؟
2. **سؤال ۲ (مصاحبه):** چرا در `Dockerfile` برای اجرای وب‌سرور باید حتماً `--host 0.0.0.0` را مشخص کنیم نه `127.0.0.1`؟
