/**
 * Bộ phát âm thanh Phòng thi chuẩn HSK máy tính thật (`ProctoredAudioPlayer.jsx` — HSK 机考音频控制):
 * - TUYỆT ĐỐI KHÔNG cho phép kéo thanh tua tới / tua lui (`seeking` bị khóa về đúng vị trí đang phát).
 * - Cố định tốc độ phát `1.0x` (`playbackRate = 1`), không có nút Tạm dừng giữa chừng như phòng thi thật.
 * - Hỗ trợ `autoPlay` khi vừa bước vào phần Nghe của kỳ thi thật (nếu trình duyệt chặn autoplay sau khi F5 thì hiện nút Tiếp tục phát 1 chạm từ đúng giây đang dở).
 * - Lưu vết lượt phát & giây đã phát vào `sessionStorage` theo `luotId` để bấm F5 không thể lợi dụng nghe lại từ đầu.
 */
import { useCallback, useEffect, useRef, useState } from "react";

import Icon from "../../../shared/components/Icon.jsx";
import { formatClock } from "../utils/paper.js";

export default function ProctoredAudioPlayer({
  src,
  storageKey,
  variant = "section",
  maxPlays = 1,
  autoPlay = false,
  onAllPlaysEnded = null,
}) {
  const audioRef = useRef(null);
  const allowedTimeRef = useRef(0);
  const playingRef = useRef(false);

  const readState = useCallback(() => {
    try {
      const raw = JSON.parse(sessionStorage.getItem(storageKey) || "{}");
      return {
        plays: Number(raw.plays || 0),
        pos: Number(raw.pos || 0),
        endedAll: Boolean(raw.endedAll),
      };
    } catch {
      return { plays: 0, pos: 0, endedAll: false };
    }
  }, [storageKey]);

  const init = readState();
  const [playing, setPlaying] = useState(false);
  const [playsUsed, setPlaysUsed] = useState(init.plays);
  const [endedAll, setEndedAll] = useState(init.endedAll);
  const [curSec, setCurSec] = useState(init.pos);
  const [durSec, setDurSec] = useState(0);
  const [volume, setVolume] = useState(1);

  const saveState = useCallback(
    (patch) => {
      try {
        const prev = readState();
        sessionStorage.setItem(storageKey, JSON.stringify({ ...prev, ...patch }));
      } catch {
        /* bỏ qua nếu trình duyệt chặn storage */
      }
    },
    [readState, storageKey]
  );

  const startPlayback = useCallback(() => {
    const el = audioRef.current;
    if (!el || playingRef.current) return;
    const saved = readState();
    if (saved.endedAll || (saved.plays >= maxPlays && saved.endedAll)) {
      setEndedAll(true);
      return;
    }

    el.playbackRate = 1.0;
    el.volume = volume;
    const targetPos = saved.pos > 0 && (!el.duration || saved.pos < el.duration - 0.5) ? saved.pos : 0;
    try {
      el.currentTime = targetPos;
    } catch {
      /* metadata chưa sẵn sàng: sẽ đồng bộ trong onLoadedMetadata */
    }
    allowedTimeRef.current = targetPos;

    const nextPlays = targetPos > 0 ? Math.max(1, saved.plays) : Math.min(maxPlays, saved.plays + 1);

    el.play()
      .then(() => {
        playingRef.current = true;
        setPlaying(true);
        setPlaysUsed(nextPlays);
        saveState({ plays: nextPlays, endedAll: false });
      })
      .catch(() => {
        // Trình duyệt yêu cầu tương tác chuột sau khi F5: giữ nguyên trạng thái để bấm nút Tiếp tục 1 chạm
        playingRef.current = false;
        setPlaying(false);
      });
  }, [maxPlays, readState, saveState, volume]);

  useEffect(() => {
    const saved = readState();
    allowedTimeRef.current = saved.pos || 0;
    setPlaysUsed(saved.plays || 0);
    setEndedAll(Boolean(saved.endedAll));
    setCurSec(saved.pos || 0);
    playingRef.current = false;
    setPlaying(false);

    if (autoPlay && !saved.endedAll) {
      const timer = setTimeout(() => startPlayback(), 120);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [storageKey, src, autoPlay, readState, startPlayback]);

  function onLoadedMetadata(e) {
    const d = e.currentTarget.duration || 0;
    setDurSec(d);
    const saved = readState();
    if (saved.pos > 0 && saved.pos < d - 0.5 && Math.abs(e.currentTarget.currentTime - saved.pos) > 1) {
      e.currentTarget.currentTime = saved.pos;
      allowedTimeRef.current = saved.pos;
    }
  }

  function onTimeUpdate() {
    const el = audioRef.current;
    if (!el) return;
    if (el.playbackRate !== 1.0) el.playbackRate = 1.0;
    if (Math.abs(el.currentTime - allowedTimeRef.current) < 1.8) {
      allowedTimeRef.current = el.currentTime;
      setCurSec(el.currentTime);
      saveState({ pos: el.currentTime });
    }
  }

  function onSeeking() {
    const el = audioRef.current;
    if (!el) return;
    if (Math.abs(el.currentTime - allowedTimeRef.current) > 0.8) {
      el.currentTime = allowedTimeRef.current;
    }
  }

  function onEnded() {
    playingRef.current = false;
    setPlaying(false);
    allowedTimeRef.current = 0;
    const saved = readState();
    const used = Math.max(playsUsed, saved.plays, 1);
    if (used >= maxPlays) {
      setEndedAll(true);
      saveState({ pos: 0, endedAll: true, plays: used });
      if (onAllPlaysEnded) onAllPlaysEnded();
    } else {
      setCurSec(0);
      saveState({ pos: 0, endedAll: false, plays: used });
    }
  }

  function handleVolume(e) {
    const v = Number(e.target.value);
    setVolume(v);
    if (audioRef.current) audioRef.current.volume = v;
  }

  const pct = durSec > 0 ? Math.min(100, Math.round((curSec / durSec) * 100)) : 0;
  const isCompact = variant === "item";

  return (
    <div className={`ibt-proctor-audio${isCompact ? " ibt-proctor-audio--item" : " ibt-proctor-audio--bar"}`}>
      <audio
        ref={audioRef}
        preload="auto"
        src={src}
        onLoadedMetadata={onLoadedMetadata}
        onTimeUpdate={onTimeUpdate}
        onSeeking={onSeeking}
        onRateChange={(e) => {
          if (e.currentTarget.playbackRate !== 1) e.currentTarget.playbackRate = 1;
        }}
        onEnded={onEnded}
      />

      <div className="ibt-proctor-audio__main">
        {!playing && !endedAll ? (
          <button type="button" className="xbtn xbtn--sm" onClick={startPlayback}>
            <Icon name="play" size={14} />{" "}
            {curSec > 1
              ? `Tiếp tục phát băng (${formatClock(curSec)})`
              : playsUsed > 0
                ? `Phát lượt ${playsUsed + 1}/${maxPlays}`
                : variant === "section"
                  ? "Phát băng Nghe"
                  : `Nghe câu này (${maxPlays} lượt)`}
          </button>
        ) : playing ? (
          <span className="ibt-audio-live-pill">
            <span className="wm-pulse wm-pulse--live" />{" "}
            {variant === "section" ? "Đang phát băng Nghe · Không tua" : `Đang phát (${playsUsed}/${maxPlays})`}
          </span>
        ) : (
          <span className="ibt-audio-done-pill">
            ✓ Đã kết thúc băng nghe ({maxPlays}/{maxPlays})
          </span>
        )}

        <div className="ibt-proctor-audio__track" aria-label="Tiến trình âm thanh (không tua)">
          <i style={{ width: `${endedAll ? 100 : pct}%` }} />
        </div>

        <span className="ibt-proctor-audio__clock">
          {formatClock(curSec)} / {formatClock(durSec)}
        </span>
      </div>

      <label className="ibt-proctor-audio__vol" title="Âm lượng tai nghe" aria-label="Âm lượng tai nghe">
        <Icon name="audio" size={15} />
        <input type="range" min="0" max="1" step="0.05" value={volume} onChange={handleVolume} />
      </label>
    </div>
  );
}
