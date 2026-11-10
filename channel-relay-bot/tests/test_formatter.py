import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from formatter import build_caption, clean_text, split_title_body, _visible_len  # noqa: E402
from media import brand_image  # noqa: E402
from store import Store  # noqa: E402

SAMPLE = """📣 اطلاعیه مهم: کدهای فعالسازی بزودی ارسال می شوند

تا حل مشکل باید صبوری کنید و تاریخی برای دریافت کد اعلام نشده
جزئیات: https://example.com/news?id=5

🌹ری_اکت به پست ها فراموش نشه🌹
#اطلاع_رسانی #رجیستری

🆔@sabregistry
پشتیبانی ما
👨‍💻@sabservice2"""

FMT = {"title_emoji": "📌", "body_label": "📰| <b>خلاصه خبر:</b>",
       "footer": ["<blockquote>t.me/techhub_ir</blockquote>"]}


def test_clean_removes_branding():
    out = clean_text(SAMPLE)
    for bad in ("@sabregistry", "@sabservice2", "#", "ری_اکت", "http", "پشتیبانی ما"):
        assert bad not in out, bad
    assert "کدهای فعالسازی" in out and "صبوری کنید" in out


def test_caption_shape():
    title, body = split_title_body(clean_text(SAMPLE))
    cap = build_caption(title, body, FMT)
    assert cap.startswith("<blockquote>📌 <b>📣 اطلاعیه مهم")
    assert "<blockquote expandable>" in cap and cap.endswith("t.me/techhub_ir</blockquote>")


def test_caption_is_trimmed_to_limit():
    cap = build_caption("تیتر", "کلمه " * 600, FMT)
    assert _visible_len(cap) <= 1024 and cap.endswith("t.me/techhub_ir</blockquote>")


def test_html_is_escaped():
    cap = build_caption("A <b> & C", "x < y", FMT)
    assert "A &lt;b&gt; &amp; C" in cap and "x &lt; y" in cap


def test_store_dedup():
    with tempfile.TemporaryDirectory() as d:
        s = Store(os.path.join(d, "t.db"))
        assert not s.seen("a:1"); s.mark_seen("a:1"); assert s.seen("a:1")
        story = "گوشی جدید سامسونگ با باتری بزرگ‌تر و دوربین بهتر معرفی شد و قیمتش اعلام شد"
        assert not s.duplicate_text(story)
        assert s.duplicate_text("  " + story + " !!")  # same story from another channel
        qid = s.enqueue("@x", "x:1", "t", "b", "c", [])
        assert s.next_ready()["id"] == qid
        s.set_status(qid, "posted"); assert s.posted_since(0) == 1


def test_brand_image_crop_and_logo():
    from PIL import Image
    with tempfile.TemporaryDirectory() as d:
        src, logo, dst = (os.path.join(d, n) for n in ("s.jpg", "l.png", "o.jpg"))
        Image.new("RGB", (800, 600), "red").save(src)
        Image.new("RGBA", (100, 50), (0, 0, 255, 255)).save(logo)
        brand_image(src, dst, crop_bottom=0.1, logo=logo)
        out = Image.open(dst)
        assert out.size == (800, 540)
        px = out.getpixel((40, 540 - 30))  # inside the bottom-left logo
        assert px[2] > 200 and px[0] < 60
