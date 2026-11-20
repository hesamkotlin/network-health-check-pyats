<style>
body, .markdown-body { direction: rtl; text-align: right; line-height: 1.85; }
h1, h2, h3, h4, h5, h6, p, ul, ol, li, table, th, td { direction: rtl; text-align: right; }
pre, pre code { direction: ltr !important; text-align: left !important; unicode-bidi: embed; }
code { direction: ltr; unicode-bidi: isolate; }
</style>

# فاز ۰: بررسی محیط توسعه و آماده‌سازی پروژه (`00-environment.md`)

---

## 1. What is this technology? (این تکنولوژی چیست؟)

در دنیای توسعه نرم‌افزار با **Python**، مدیریت نسخه مفسر (`Python Interpreter`)، محیط‌های مجازی ایزوله (`Virtual Environments` یا `venv`) و مدیر بسته‌ها (`pip`) زیربنای هر پروژه مهندسی را تشکیل می‌دهند.

اگر شما از دنیای **Android / Kotlin** می‌آیید، می‌توانید این اجزا را به شکل زیر شبیه‌سازی کنید:

| مفهوم در Python | معادل در Android / Kotlin | توضیح کاربردی |
| :--- | :--- | :--- |
| `Python Interpreter` (`python3`) | `JDK / JVM` | موتور اجرایی که کدهای شما را تفسیر و اجرا می‌کند. |
| `venv` (Virtual Environment) | ایزوله‌سازی وابستگی‌های هر پروژه در `Gradle` | یک پوشه اختصاصی (`.venv`) در داخل پروژه که تمام کتابخانه‌های نصب‌شده فقط در همان پروژه دیده می‌شوند و با کل سیستم‌عامل قاطی نمی‌شوند. |
| `pip` | `Gradle Dependency Resolver` | ابزار خط فرمان برای دانلود و نصب پکیج‌ها از مخزن رسمی **PyPI** (مشابه Maven Central). |
| `requirements.txt` / `pyproject.toml` | `build.gradle.kts` + `libs.versions.toml` | فایل‌هایی که لیست پکیج‌های مورد نیاز پروژه و نسخه‌های آن‌ها را مشخص می‌کنند. |

---

## 2. Why do we need it in this project? (چرا در این پروژه به آن نیاز داریم؟)

فریم‌ورک **Cisco pyATS** و کتابخانه **Genie** از ده‌ها زیرپکیج تخصصی شبکه (`pyats.aetest`, `pyats.topology`, `genie`, `unicon`) تشکیل شده‌اند که به نسخه‌های مشخصی از Python و کتابخانه‌های C/Cython وابسته هستند.

دلایل اهمیت بررسی محیط (`Environment Inspection`) قبل از نوشتن حتی یک خط کد:
1. **تطابق معماری پردازنده و سیستم‌عامل:** **pyATS** به صورت رسمی فقط روی **Linux** و **macOS** اجرا می‌شود (روی Windows نیاز به WSL2 دارد).
2. **سازگاری نسخه Python:** نسخه‌های جدید **Cisco pyATS (`25.x+`)** نیازمند **Python >= 3.10** هستند (نسخه‌های `3.11` و `3.12` بهترین پایداری را دارند)، در حالی که نسخه‌های قدیمی‌تر مثل `Python 3.9` تنها تا نسخه **`pyats 24.11`** پشتیبانی می‌شوند.
3. **جلوگیری از آلودگی سیستم‌عامل (`Global Pollution`):** نصب پکیج‌ها با دستور `pip install` بدون `Virtual Environment` می‌تواند ابزارهای سیستمی macOS را دچار تداخل کند.

---

## 3. How does it work? (چطور کار می‌کند؟)

وقتی دستور `python3 -m venv .venv` را اجرا می‌کنید:
1. یک پوشه به نام `.venv` در ریشه پروژه ساخته می‌شود.
2. یک کپی یا Symlink از باینری `python3` و `pip` داخل مسیر `.venv/bin/` قرار می‌گیرد.
3. یک پوشه ایزوله به نام `.venv/lib/pythonX.Y/site-packages/` ساخته می‌شود.
4. با اجرای `source .venv/bin/activate` در ترمینال (`zsh`)، متغیر محیطی `PATH` موقتاً تغییر می‌کند تا هر بار که `python` یا `pip` می‌زنید، به جای Python سیستم‌عامل، از `.venv/bin/python` استفاده شود.

---

## 4. Important concepts and terminology (مفاهیم و اصطلاحات مهم)

- **CPython:** پیاده‌سازی استاندارد و مرجع زبان Python که به زبان C نوشته شده است.
- **PyPI (Python Package Index):** مخزن مرکزی پکیج‌های Python (نشانی `pypi.org`)، معادل **Maven Central** یا **Google Maven Repository** در اندروید.
- **Wheel (`.whl`):** فرمت باینری یا از پیش بسته‌بندی‌شده پکیج‌های Python (مشابه فایل‌های `.aar` یا `.jar` در اندروید) که نیاز به کامپایل مجدد هنگام نصب ندارد.
- **Editable Install (`pip install -e .`):** نصب پکیج خودِ پروژه در حالت توسعه؛ به‌طوری‌که هر تغییری در پوشه `src/` بدهید، بلافاصله بدون نیاز به Build یا نصب مجدد، در کل پروژه و تست‌ها قابل `import` است.
- **PEP (Python Enhancement Proposal):** اسناد استانداردسازی طراحی زبان Python (مانند `PEP 8` برای استاندارد نگارش کد و `PEP 484` برای `Type Hints`).

---

## 5. Explanation of each relevant source file (توضیح فایل‌های مرتبط در پروژه)

در پایان راه‌اندازی اولیه، فایل‌های پیکربندی محیط در ریشه پروژه به شرح زیر خواهند بود:

- **`PROJECT_STATUS.md`**: وضعیت لحظه‌ای پیشرفت فازها، نتایج اجرای تست‌ها و محدودیت‌های شناسایی‌شده.
- **`pyproject.toml`**: فایل مدرن پیکربندی پروژه Python (مشابه `settings.gradle.kts` و `build.gradle.kts`) که نام پکیج (`network_health`)، مسیر کدهای منبع (`src/`) و تنظیمات ابزارهای تست (`pytest`) را مشخص می‌کند.
- **`requirements.txt`**: لیست دقیق وابستگی‌های پروژه (`pyats[library]`, `pytest`, و در فازهای بعدی `fastapi`, `uvicorn`).
- **`.gitignore`**: جلوگیری از کامیت شدن پوشه `.venv/`، فایل‌های کش (`__pycache__/`)، فایل `.env` حاوی رمزهای عبور، و لاگ‌های موقت در Git.
- **`.env.example`**: الگوی متغیرهای محیطی (بدون مقادیر محرمانه واقعی) برای اتصال امن در فازهای بعدی.

---

## 6. Explanation of important classes and functions (توضیح دستورات و ماژول‌های کلیدی محیط)

در فاز ۰، به جای کلاس‌های برنامه، با ماژول‌های داخلی Python برای مدیریت محیط سر و کار داریم:

- **`venv` module (`python3 -m venv .venv`)**: ماژول استاندارد داخلی Python برای ساخت محیط مجازی ایزوله. فلگ `-m` به مفسر Python می‌گوید یک ماژول کتابخانه استاندارد را به عنوان اسکریپت اجرا کند.
- **`sys.version` / `sys.executable`**: ویژگی‌های داخل ماژول `sys` که در کد Python به ما نشان می‌دهند کدام باینری Python و چه نسخه‌ای در حال اجرای برنامه است.
- **`pyats version check`**: دستور CLI رسمی فریم‌ورک **pyATS** که نسخه تمامی کامپوننت‌های نصب‌شده (`pyats`, `genie`, `unicon`) را بررسی و نمایش می‌دهد.

---

## 7. Step-by-step execution flow (روند گام‌به‌گام بررسی و راه‌اندازی محیط)

گام‌هایی که در سیستم شما اجرا و بررسی شدند:

1. **گام اول – بررسی سیستم‌عامل و معماری پردازنده:**
   - سیستم‌عامل: `macOS 15.7.9` (Build `24G830`)
   - پردازنده: `Intel(R) Core(TM) i7-4870HQ CPU @ 2.50GHz` با معماری `x86_64`
   - نتیجه: کاملاً سازگار با **Cisco pyATS**.

2. **گام دوم – بررسی Git و ابزارهای خط فرمان:**
   - نسخه Git: `git version 2.39.5 (Apple Git-154)`
   - مدیران بسته جانبی (`brew`, `pyenv`, `uv`, `poetry`, `conda`): روی سیستم نصب نیستند.

3. **گام سوم – بررسی Python نصب‌شده روی سیستم:**
   - مسیر باینری: `/usr/bin/python3`
   - نسخه فعلی: `Python 3.9.6` (ارائه‌شده توسط Apple Command Line Developer Tools)
   - نسخه `pip`: `pip 21.2.4`

4. **گام چهارم – تحلیل سازگاری با Cisco pyATS:**
   - طبق مستندات رسمی Cisco، نسخه‌های جدید **`pyATS 25.x+`** به **`Python >= 3.10`** (پیشنهاد ویژه: **Python 3.11** یا **Python 3.12**) نیاز دارند.
   - اگر از `Python 3.9.6` فعلی استفاده کنیم، `pip` به صورت خودکار آخرین نسخه سازگار با Python 3.9 یعنی سری **`pyats 24.11`** را نصب خواهد کرد.

---

## 8. Real code examples (مثال‌های واقعی دستورات و کد)

### بررسی محیط از طریق خط فرمان (`zsh`)
```bash
# 1. Check macOS version and CPU architecture
sw_vers
uname -m

# 2. Check active Python and pip versions
python3 --version
pip3 --version
```

### ساخت و فعال‌سازی محیط مجازی (`.venv`)
```bash
# Move into the project root directory
cd /Users/hesam/.gemini/antigravity/scratch/network-health-check

# Create an isolated virtual environment inside .venv
python3 -m venv .venv

# Activate the virtual environment in zsh/bash
source .venv/bin/activate

# Verify that python and pip now point to .venv/bin/
which python
which pip

# Upgrade core packaging tools inside the virtual environment
python -m pip install --upgrade pip setuptools wheel
```

### بررسی محیط از داخل کد Python
```python
import platform
import sys


def inspect_runtime_environment() -> dict[str, str]:
    """Return key runtime environment details for health check diagnostics."""
    return {
        "os_name": platform.system(),
        "os_release": platform.mac_ver()[0],
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
    }


if __name__ == "__main__":
    info = inspect_runtime_environment()
    for key, value in info.items():
        print(f"{key}: {value}")
```

---

## 9. Common mistakes and debugging techniques (خطاهای رایج و تکنیک‌های دیباگ)

1. **اجرای `pip install` بدون فعال بودن `.venv`:**
   - **نشانه:** پیام خطای `Permission denied` یا `externally-managed-environment`، و یا نصب شدن پکیج در مسیر سیستم‌عامل.
   - **راه‌حل:** همیشه قبل از نصب پکیج، خروجی `which python` را چک کنید تا مطمئن شوید مسیر `.venv/bin/python` را نشان می‌دهد، یا دستور را به شکل مستقیم `.venv/bin/python -m pip install ...` اجرا کنید.

2. **عدم ارتقای `pip` قدیمی قبل از نصب `pyats`:**
   - **نشانه:** در `pip 21.2.4` (نسخه پیش‌فرض Apple CLT)، ممکن است حل وابستگی‌ها (`Dependency Resolution`) برای پکیج‌های بزرگ مثل `pyats[library]` کند باشد یا Wheel مناسب را تشخیص ندهد.
   - **راه‌حل:** بلافاصله پس از ساخت `.venv`، دستور `python -m pip install --upgrade pip setuptools wheel` را اجرا کنید.

3. **کامیت کردن پوشه `.venv` در Git:**
   - **نشانه:** حجم مخزن Git به صدها مگابایت می‌رسد و روی سیستم‌های دیگر کار نمی‌کند (چون مسیرهای داخل `.venv` مطلق هستند).
   - **راه‌حل:** همیشه `.venv/` را در فایل `.gitignore` قرار دهید (معادل پوشه `.gradle/` و `build/` در پروژه‌های Android).

---

## 10. Practical exercises (تمرین‌های عملی)

### تمرین ۱: بررسی مسیر مفسر فعال
پس از ساخته شدن محیط مجازی `.venv` در ریشه پروژه:
1. بدون فعال‌سازی `.venv` دستور `which python3` را اجرا کنید.
2. محیط مجازی را با `source .venv/bin/activate` فعال کنید و دستور `which python` را اجرا کنید.
3. با دستور `python -c "import sys; print(sys.prefix)"` مسیر محیط فعال را چاپ کنید.

### تمرین ۲: بررسی تفاوت نسخه `pip`
نسخه `pip` سیستم (`/usr/bin/pip3 --version`) را با نسخه `pip` ارتقایافته داخل `.venv` (`.venv/bin/pip --version`) مقایسه کنید.

---

## 11. Expected exercise results (نتایج مورد انتظار تمرین‌ها)

- **نتیجه تمرین ۱:**
  - قبل از فعال‌سازی: `/usr/bin/python3`
  - بعد از فعال‌سازی: `/Users/hesam/.gemini/antigravity/scratch/network-health-check/.venv/bin/python`
  - خروجی `sys.prefix`: مسیر کامل پوشه `.venv` پروژه را چاپ می‌کند.
- **نتیجه تمرین ۲:**
  - `/usr/bin/pip3 --version` نسخه قدیمی `21.2.4` را نشان می‌دهد، اما `.venv/bin/pip --version` آخرین نسخه جدید `pip` را نمایش می‌دهد، بدون اینکه فایل‌های سیستم‌عامل macOS دستکاری شده باشند.

---

## 12. Short knowledge-check quiz (آزمون کوتاه سنجش دانش)

1. **سؤال ۱:** پوشه `.venv` در یک پروژه Python چه نقشی دارد و نزدیک‌ترین مفهوم به آن در اکوسیستم Android/Gradle چیست؟
2. **سؤال ۲:** چرا نصب مستقیم پکیج‌های پروژه با `/usr/bin/pip3 install` روی macOS یک Anti-Pattern محسوب می‌شود؟
3. **سؤال ۳:** طبق مستندات رسمی Cisco، نسخه‌های جدید `pyATS (25.x+)` به چه نسخه‌ای از Python نیاز دارند و وضعیت `Python 3.9.6` فعلی سیستم شما در برابر آن چیست؟
4. **سؤال ۴:** چه دستوری در ترمینال نشان می‌دهد که آیا محیط مجازی (`.venv`) شما در حال حاضر فعال است یا خیر؟
