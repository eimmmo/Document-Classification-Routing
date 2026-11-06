# Document Classification & Routing (doc-router)

نظام بياخد نص مستند وارد، يصنّفه لنوعه، ويقترح القسم المستلم.

- **الفريق:** روان، إيمان، ملك، ياسمين
- **وثيقة المشروع (المرجع):** ضعي هنا لينك الوثيقة

## الحالة الحالية
المرحلة 1: تجهيز الداتا لفئتين (Complaint وContract).

## الإعداد
```bash
python -m venv .venv
source .venv/bin/activate   # على ويندوز: .venv\Scripts\activate
pip install -r requirements.txt
```

## قواعد الشغل
- كل واحدة تشتغل على branch باسمها.
- كل تغيير بـ Pull Request، ومراجعة من واحدة تانية قبل الدمج.
- ملفات الداتا مش بتترفع على GitHub، بتتبادل على Google Drive.
- مفيش مفاتيح أو أسرار في الكود (استخدموا environment variables).
- ملفات CSV: UTF-8، من غير عمود index، والأعمدة بالظبط: `text` و`label` و`source`.
- أسماء الفئات بالحروف بالظبط: `Complaint` و`Contract`.
