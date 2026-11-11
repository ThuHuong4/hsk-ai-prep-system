import { useEffect } from "react";

// Hiệu ứng trang chủ, chuyển từ bản mô phỏng đã duyệt:
// chuyển động theo prefers-reduced-motion, parallax hero, Xiang cày ruộng khi cuộn,
// kính lúp soi chữ, bấm Xiang để nhảy.
const SAY = [
  "再 là “lại”, 见 là “gặp”: hẹn gặp lại!",
  "Nói 谢谢 khi cảm ơn. Còn xin lỗi là 对不起.",
  "米 là gạo, 饭 là bữa ăn: 米饭 là cơm.",
  "老师 là giáo viên. Học sinh là 学生.",
  "喝 là uống, 茶 là trà: 喝茶 là uống trà.",
  "朋友 là bạn bè. Bạn thân là 好朋友.",
];
const MOO = [
  ["哞～", "Trâu kêu “mōu” đó!"],
  ["加油！", "jiāyóu · cố lên"],
  ["你好！", "nǐ hǎo · xin chào"],
];

export default function useHomeEffects(rootRef) {
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return undefined;
    const html = document.documentElement;
    const $ = (s) => root.querySelector(s);
    const $$ = (s, el = root) => Array.from(el.querySelectorAll(s));
    const cleanups = [];
    const on = (el, type, fn, opts) => {
      el.addEventListener(type, fn, opts);
      cleanups.push(() => el.removeEventListener(type, fn, opts));
    };

    /* ---------- Motion preference ---------- */
    const mq = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
    const applyMotion = () => html.classList.toggle("motion-ok", !(mq && mq.matches));
    applyMotion();
    if (mq && mq.addEventListener) on(mq, "change", applyMotion);
    const motionOK = () => html.classList.contains("motion-ok");

    /* ---------- Hero parallax ---------- */
    const stage = $("#stage");
    const hero = $(".h-hero");
    let heroRaf = 0;
    if (stage && hero && window.matchMedia && window.matchMedia("(pointer:fine)").matches) {
      let px = 0;
      let py = 0;
      on(hero, "pointermove", (e) => {
        if (!motionOK()) return;
        const r = stage.getBoundingClientRect();
        px = (e.clientX - (r.left + r.width / 2)) / r.width;
        py = (e.clientY - (r.top + r.height / 2)) / r.height;
        if (!heroRaf) {
          heroRaf = requestAnimationFrame(() => {
            heroRaf = 0;
            $$("[data-depth]", stage).forEach((l) => {
              const d = +l.getAttribute("data-depth") || 0;
              l.style.transform = l.classList.contains("xiang-main")
                ? `translateX(calc(-50% + ${px * d}px)) translateY(${py * d}px) rotate(${px * 8}deg)`
                : `translate(${px * d}px,${py * d}px)`;
            });
          });
        }
      });
      on(hero, "pointerleave", () => {
        $$("[data-depth]", stage).forEach((l) => { l.style.transform = ""; });
      });
    }

    /* ---------- Cuộn để cày ---------- */
    const plScene = $("#pl-scene");
    const plOx = $("#pl-ox");
    const plDone = $("#pl-done");
    let plRaf = 0;
    let plTickRaf = 0;
    if (plScene && plOx && plDone) {
      const plSps = $$(".sprout", plScene);
      const plLayers = $$("[data-par]", plScene);
      const plSun = plScene.querySelector(".pl-sun");
      let PTH = [0.13, 0.4, 0.67, 0.93];
      let plR = 66;
      let plCur = 0;
      let plTarget = 0;

      const plLayout = () => {
        const w = plScene.clientWidth || 1;
        plR = Math.max(36, 100 - (plOx.offsetWidth / w) * 100 - 4);
        const xs = [0.06, 0.3, 0.54, 0.78].map((f) => (w < 720 ? 2 : 7) + f * (plR - 8));
        plSps.forEach((sp, i) => sp.style.setProperty("--x", `${xs[i]}%`));
        PTH = xs.map((x) => Math.min(0.97, (x + 2) / plR));
      };
      const plRender = (p) => {
        plOx.style.left = `${p * plR}%`;
        plDone.style.width = `${p > 0.005 ? p * plR + 3 : 0}%`;
        if (p <= 0.01) plSps.forEach((sp) => sp.classList.remove("up"));
        else {
          plSps.forEach((sp, i) => {
            if (p >= PTH[i] && (i === 0 || plSps[i - 1].classList.contains("up"))) sp.classList.add("up");
          });
        }
        const w = plScene.clientWidth;
        plLayers.forEach((l) => {
          const d = +l.getAttribute("data-par");
          l.style.transform = `translateX(${(-p * d * w) / 1000}px)`;
        });
        if (plSun) plSun.style.transform = `translateY(${-p * 24}px)`;
      };
      const plLoop = () => {
        const diff = plTarget - plCur;
        if (Math.abs(diff) < 0.0015 || !motionOK()) {
          plCur = plTarget;
          plRender(plCur);
          plRaf = 0;
          plScene.classList.remove("walking");
          return;
        }
        plCur += diff * 0.12;
        plRender(plCur);
        plScene.classList.add("walking");
        plRaf = requestAnimationFrame(plLoop);
      };
      const plUpdate = () => {
        plTickRaf = 0;
        const r = plScene.getBoundingClientRect();
        const vh = window.innerHeight || 800;
        const start = vh * 0.92;
        const end = vh * 0.08;
        plTarget = Math.max(0, Math.min(1, (start - r.top) / (start - end)));
        if (!plRaf) plRaf = requestAnimationFrame(plLoop);
      };

      plLayout();
      on(window, "scroll", () => { if (!plTickRaf) plTickRaf = requestAnimationFrame(plUpdate); }, { passive: true });
      on(window, "resize", () => { plLayout(); plUpdate(); });
      plUpdate();
    }

    /* ---------- Kính lúp soi chữ ---------- */
    const night = $("#night");
    const nsay = $("#night-say");
    if (night && nsay) {
      const wds = $$(".wd", night);
      const light = (i) => {
        wds.forEach((w, k) => w.classList.toggle("lit", k === i));
        nsay.textContent = SAY[i];
      };
      const moveTo = (x, y) => {
        night.style.setProperty("--x", `${x}%`);
        night.style.setProperty("--y", `${y}%`);
      };
      on(night, "pointermove", (e) => {
        const r = night.getBoundingClientRect();
        const x = e.clientX - r.left;
        const y = e.clientY - r.top;
        moveTo((x / r.width) * 100, (y / r.height) * 100);
        let best = -1;
        let bd = 1e9;
        wds.forEach((w, k) => {
          const b = w.getBoundingClientRect();
          const cx = b.left + b.width / 2 - r.left;
          const cy = b.top + b.height / 2 - r.top;
          const d = (cx - x) * (cx - x) + (cy - y) * (cy - y);
          if (d < bd) { bd = d; best = k; }
        });
        if (best >= 0 && !wds[best].classList.contains("lit")) light(best);
      });
      wds.forEach((w, k) => {
        const at = () => {
          const r = night.getBoundingClientRect();
          const b = w.getBoundingClientRect();
          moveTo(((b.left + b.width / 2 - r.left) / r.width) * 100, ((b.top + b.height / 2 - r.top) / r.height) * 100);
          light(k);
        };
        on(w, "focus", at);
        on(w, "click", at);
      });
    }

    /* ---------- Bấm Xiang để nhảy ---------- */
    const xm = $(".xiang-main");
    const mooEl = $(".moo");
    let mooT = 0;
    if (xm && mooEl) {
      let mi = 0;
      on(xm, "click", () => {
        xm.classList.remove("hop");
        void xm.offsetWidth;
        xm.classList.add("hop");
        const m = MOO[mi++ % MOO.length];
        mooEl.innerHTML = "";
        const hz = document.createElement("span");
        hz.className = "hz";
        hz.textContent = m[0];
        mooEl.append(hz, ` ${m[1]}`);
        mooEl.hidden = false;
        clearTimeout(mooT);
        mooT = setTimeout(() => { mooEl.hidden = true; }, 2200);
      });
    }

    return () => {
      cleanups.forEach((fn) => fn());
      cancelAnimationFrame(heroRaf);
      cancelAnimationFrame(plRaf);
      cancelAnimationFrame(plTickRaf);
      clearTimeout(mooT);
      html.classList.remove("motion-ok");
    };
  }, [rootRef]);
}
