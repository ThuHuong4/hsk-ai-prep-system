"""Tạo 30 tệp âm thanh Nghe HSK 1 bằng giọng đọc tiếng Trung có sẵn của Windows (không cần tài khoản, không cần mạng).

Đọc lời thoại từ scripts/data/hsk1_nghe_on_luyen.json: lượt 女 đọc giọng nữ, lượt 男 đọc giọng nam (nếu máy có);
không đọc nhãn 女/男 và không đọc phương án. Kết quả: uploads/practice/hsk1_nghe/H1_N001.wav … H1_N030.wav.

Chuẩn bị (một lần):
    pip install pyttsx3
    Máy cần có giọng đọc tiếng Trung (vd Microsoft Huihui). Chạy  python scripts/tao_am_thanh_hsk1_nghe_windows.py --giong
    để xem máy có giọng nào.

Cách chạy (đứng trong thư mục backend):
    python scripts/tao_am_thanh_hsk1_nghe_windows.py          # chỉ tạo tệp còn thiếu
    python scripts/tao_am_thanh_hsk1_nghe_windows.py --ghi-de # tạo lại tất cả
Nghe kiểm tra rồi chạy scripts/seed_hsk1_nghe.py.
"""
import json
import re
import sys
import tempfile
import wave
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
DATA = BACKEND / "scripts" / "data" / "hsk1_nghe_on_luyen.json"
RATE = 150          # tốc độ đọc (mặc định Windows ~200), chậm hơn cho người mới học
PAUSE_SECONDS = 0.6  # nghỉ giữa hai lượt nói
FEMALE = ("huihui", "yaoyao", "xiaoxiao", "female")
MALE = ("kangkang", "yunxi", "male")


def chinese_voices(engine) -> list:
    out = []
    for v in engine.getProperty("voices"):
        text = " ".join(str(x) for x in (v.id, v.name, getattr(v, "languages", ""))).lower()
        if any(k in text for k in ("zh-cn", "zh_cn", "chinese", "huihui", "kangkang", "yaoyao", "0804")):
            out.append(v)
    return out


def pick(voices: list, keys: tuple):
    for v in voices:
        if any(k in f"{v.id} {v.name}".lower() for k in keys):
            return v
    return None


def turns(dialogue: str) -> list[tuple[str, str]]:
    out = []
    for line in dialogue.split("\n"):
        m = re.match(r"^\s*([女男])：\s*(.+)$", line)
        if not m:
            raise ValueError(f"Dòng không có nhãn 女/男: {line}")
        out.append((m.group(1), m.group(2)))
    return out


def join_wavs(parts: list[Path], target: Path) -> None:
    """Nối các đoạn WAV cùng định dạng, chèn khoảng lặng giữa các lượt."""
    frames, params = [], None
    for p in parts:
        with wave.open(str(p), "rb") as w:
            if params is None:
                params = w.getparams()
            elif (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (params.nchannels, params.sampwidth, params.framerate):
                raise RuntimeError("Hai giọng đọc khác định dạng âm thanh; hãy dùng cùng một giọng (xem --giong)")
            frames.append(w.readframes(w.getnframes()))
    silence = b"\x00" * int(params.framerate * PAUSE_SECONDS) * params.sampwidth * params.nchannels
    with wave.open(str(target), "wb") as out:
        out.setnchannels(params.nchannels)
        out.setsampwidth(params.sampwidth)
        out.setframerate(params.framerate)
        out.writeframes(silence.join(frames) + silence)


def main() -> int:
    if sys.platform != "win32":
        print("✗ Script này dùng giọng đọc của Windows, hãy chạy trên máy Windows")
        return 1
    try:
        import pyttsx3
    except ImportError:
        print("✗ Chưa cài pyttsx3. Chạy: pip install pyttsx3")
        return 1
    engine = pyttsx3.init()
    voices = chinese_voices(engine)
    if "--giong" in sys.argv[1:]:
        print("Giọng tiếng Trung trên máy:" if voices else "Máy chưa có giọng tiếng Trung.")
        for v in voices:
            print(f"  - {v.name}")
        return 0
    if not voices:
        print("✗ Máy chưa có giọng đọc tiếng Trung. Cài trong Settings → Time & language → Language & region → "
              "thêm 中文(简体) có Text-to-speech, khởi động lại máy rồi chạy lại với --giong để kiểm tra")
        return 1
    female = pick(voices, FEMALE) or voices[0]
    male = pick(voices, MALE) or female
    print(f"Giọng nữ: {female.name} · Giọng nam: {male.name}" + (" (máy chỉ có một giọng)" if male is female else ""))
    engine.setProperty("rate", RATE)

    data = json.loads(DATA.read_text(encoding="utf-8"))
    items = [c for lesson in data["bai"] for c in lesson["cau"]] + data["cuoi_thua"]
    overwrite = "--ghi-de" in sys.argv[1:]
    made = skipped = 0
    with tempfile.TemporaryDirectory() as tmp:
        for item in items:
            target = (BACKEND / "uploads" / item["tep_audio"]).with_suffix(".wav")
            if target.is_file() and not overwrite:
                skipped += 1
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            parts = []
            for k, (who, said) in enumerate(turns(item["loi_nghe"])):
                engine.setProperty("voice", (female if who == "女" else male).id)
                part = Path(tmp) / f"{item['ma']}_{k}.wav"
                engine.save_to_file(said, str(part))
                engine.runAndWait()
                if not part.is_file() or part.stat().st_size < 1000:
                    print(f"✗ {item['ma']}: không tạo được âm thanh, dừng lại")
                    return 1
                parts.append(part)
            join_wavs(parts, target)
            made += 1
            print(f"  ✓ {target.name}")
    print(f"→ Tạo {made} tệp, bỏ qua {skipped} tệp đã có. Nghe kiểm tra rồi chạy seed_hsk1_nghe.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
