# Frexy Auto Like Telegram Bot

এটি একটি ফ্রি ফায়ার অটো-লাইক টেলিগ্রাম বট, যা Render ক্লাউড প্ল্যাটফর্মে নির্বিঘ্নে চালানোর জন্য অপ্টিমাইজ করা হয়েছে।

## Render-এ ডিপ্লয় করার নিয়ম:

1. **GitHub Repository তৈরি করুন:** 
   আপনার কোডগুলো (`main.py`, `render.yaml`, `requirements.txt`, এবং `README.md`) একটি পাবলিক অথবা প্রাইভেট গিটহাব রিপোজিটরিতে পুশ (Push) করুন।

2. **Render-এ সাইন-আপ করুন:** 
   [Render.com](https://render.com)-এ গিয়ে অ্যাকাউন্ট তৈরি করুন বা লগইন করুন।

3. **New Web Service তৈরি করুন:**
   * Render ড্যাশবোর্ড থেকে **New +** বাটনে ক্লিক করে **Web Service** সিলেক্ট করুন।
   * আপনার তৈরি করা GitHub রিপোজিটরিটি কানেক্ট করুন।

4. **কনফিগারেশন চেক করুন:**
   * **Runtime:** Python 3
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `python main.py`

5. **Deploy বাটনে ক্লিক করুন:**
   Render আপনার ডিপেনডেন্সি ইনস্টল করবে এবং পোর্ট ৮০৮০ বাইন্ড করে বটটিকে সফলভাবে সচল রাখবে।
