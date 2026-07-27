# أتمتة نشر Ahadeeth__14 — تيليجرام (+إنستقرام لاحقًا) عبر GitHub Actions

ينشر بوستًا واحدًا **كل يوم الساعة 10 صباحًا و10 مساءً بتوقيت الكويت**، تلقائيًا وبدون
تشغيل جهازك. الكابشن = **العنوان بخط عريض** ثم نص الرواية كاملة (السند + المتن) ثم 📖 المصدر ثم @ahadeeth_14. لا يكرّر أي بوست (سجلّ
`published.json`).

## المتطلبات لمرة واحدة
- حساب **GitHub** مجاني.
- **توكن البوت** (من BotFather) والبوت **أدمن** في قناة `@ahadeeth_14` (صلاحية Post Messages).
- Python على جهازك (لخطوة التجهيز فقط).

## خطوات التشغيل (أول مرة)

### 1) جهّز الصور والكابشنات محليًا
افتح Terminal داخل هذا المجلد ونفّذ:
```
pip install requests
python build_assets.py "C:/Users/Acer/Dropbox/أحاديث 14/بوستات جاهزة 400"
```
ينشئ مجلد `posts/` فيه ٥٦٧ صورة بأسماء `001.png … 567.png` وملف `captions_ascii.json`.

### 2) اختبار محلي (اختياري، لا ينشر)
```
python poster.py status
python poster.py post-next --dry-run
```

### 3) ارفعه على GitHub
1. أنشئ **repo خاص (Private)** جديد على GitHub، مثلاً `ahadeeth-autopost`.
2. من داخل هذا المجلد:
   ```
   git init
   git add .
   git commit -m "initial"
   git branch -M main
   git remote add origin https://github.com/<اسمك>/ahadeeth-autopost.git
   git push -u origin main
   ```
   (ملف `config.json` لن يُرفع — محمي بـ `.gitignore`. التوكن يُوضع كـ Secret بالخطوة التالية.)

### 4) أضف الأسرار (Secrets)
في صفحة الـ repo على GitHub: **Settings → Secrets and variables → Actions → New repository secret**، وأضف:
| الاسم | القيمة |
|---|---|
| `TELEGRAM_TOKEN` | توكن البوت |
| `TELEGRAM_CHANNEL` | `@ahadeeth_14` |

(إنستقرام لاحقًا: `IG_TOKEN`, `IG_USER_ID`, `PUBLIC_BASE_URL`.)

### 5) فعّل وجرّب
- **Actions** (أعلى صفحة الـ repo) → فعّل الـ workflows إذا طلب.
- افتح **Ahadeeth auto-post → Run workflow** (زر يدوي) وجرّب **dry run = true** أولًا، ثم
  شغّله فعليًا لنشر أول بوست تجريبي.
- بعد نجاحه، بيشتغل تلقائيًا **7:00 و19:00 UTC** = **10ص و10م بتوقيت الكويت** كل يوم.

## التحكم اليومي
- **إيقاف مؤقت**: Actions → الـ workflow → `⋯` → Disable. **تشغيل**: Enable.
- **تغيير الأوقات**: عدّل سطري `cron` في `.github/workflows/post.yml` (بتوقيت UTC).
- **نشر يدوي الآن**: Run workflow، أو محليًا `python poster.py post-next`.
- **الحالة**: `python poster.py status` (كم اننشر وكم باقي).

## ملاحظات
- الجدولة في GitHub قد تتأخر بضع دقائق وقت الازدحام — طبيعي.
- الـ ٥٦٧ صورة تكفي **٢٨٣ يومًا** (بوستين/يوم: ١٠ صباحًا و١٠ مساءً). لما تقرب تخلص، ولّد دفعة جديدة بالمهارة
  `ahadeeth14-posts` وأعد الخطوة 1 ثم `git add posts captions_ascii.json && git commit && git push`.
- **إنستقرام**: يحتاج Meta app + access token لحساب الأعمال المربوط بصفحة فيسبوك، ورابطًا عامًا
  للصورة (نستعمل رابط GitHub الخام). جاهّز التوكن وبنضيفه كـ Secrets ويشتغل تلقائيًا مع تيليجرام.
