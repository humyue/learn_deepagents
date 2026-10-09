/* ============================================================
   Deep Agents 教学站 — 共享交互 (assets/course.js)
   提供：侧边导航开合、进度持久化、测验判定、掌握勾选
   全部基于 localStorage，离线可用，无依赖。
   站点数据由 build.py 注入到 window.SITE（见每个页面底部）。
   ============================================================ */
(function () {
  "use strict";

  var KEY_DONE = "da.lesson.done"; // { slug: 1 }
  var KEY_QUIZ = "da.quiz.score"; // { slug: {correct, total} }

  function read(key, fallback) {
    try {
      var raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch {
      // localStorage 不可用或内容损坏时退回默认值
      return fallback;
    }
  }

  function write(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // 隐私模式或配额满时静默降级：进度不保存，但不影响使用
    }
  }

  var done = read(KEY_DONE, {});
  var scores = read(KEY_QUIZ, {});

  function isElement(node) {
    return node instanceof Element;
  }

  /* ---------- 侧边导航 ---------- */
  function initNav() {
    var btn = document.querySelector(".menu-btn");
    if (btn) {
      btn.addEventListener("click", function () {
        document.body.classList.toggle("nav-open");
      });
    }

    document.addEventListener("click", function (event) {
      if (window.innerWidth > 1000) return;
      if (!document.body.classList.contains("nav-open")) return;
      if (!isElement(event.target)) return;
      if (event.target.closest(".sidebar")) return;
      if (event.target.closest(".menu-btn")) return;
      document.body.classList.remove("nav-open");
    });
  }

  /* ---------- 进度条 ---------- */
  function renderProgress() {
    var site = window.SITE;
    if (!site) return;

    var total = site.lessons.length;
    if (!total) return;

    var finished = 0;
    for (var key in done) {
      if (!Object.prototype.hasOwnProperty.call(done, key)) continue;
      for (var i = 0; i < site.lessons.length; i += 1) {
        if (site.lessons[i].slug === key) {
          finished += 1;
          break;
        }
      }
    }

    var pct = Math.round((finished / total) * 100);
    var bar = document.querySelector(".progress-pill .bar > i");
    var label = document.querySelector(".progress-pill .txt");
    if (bar) bar.style.width = pct + "%";
    if (label) label.textContent = finished + "/" + total + " · " + pct + "%";
  }

  /* ---------- 导航与首页卡片的高亮 ---------- */
  function markCompleted(selector) {
    var nodes = document.querySelectorAll(selector);
    for (var i = 0; i < nodes.length; i += 1) {
      var node = nodes[i];
      if (done[node.dataset.slug]) node.classList.add("done");
    }
  }

  /* ---------- 测验 ---------- */
  function makeQuestionHandler(quiz, question, index, state, paint) {
    var opts = question.querySelectorAll(".opts li");
    var correctIndex = Number.parseInt(question.dataset.answer, 10);

    function choose(chosen, chosenIndex) {
      if (state.answered.has(index)) return;
      state.answered.add(index);

      for (var i = 0; i < opts.length; i += 1) opts[i].classList.add("locked");

      if (chosenIndex === correctIndex) {
        chosen.classList.add("correct");
        state.correct += 1;
      } else {
        chosen.classList.add("wrong");
        if (opts[correctIndex]) opts[correctIndex].classList.add("correct");
      }

      var explain = question.querySelector(".explain");
      if (explain) explain.classList.add("show");

      paint();
      scores[quiz.dataset.slug] = { correct: state.correct, total: state.total };
      write(KEY_QUIZ, scores);

      if (state.answered.size === state.total) {
        var foot = quiz.querySelector(".quiz-foot .result");
        if (!foot) return;
        foot.textContent =
          state.correct === state.total
            ? "全部正确。可以把下面的「本课已掌握」勾上了。"
            : "答完 " +
              state.correct +
              "/" +
              state.total +
              "。回到上文找到漏掉的机制，再回来重做一遍。";
      }
    }

    for (var i = 0; i < opts.length; i += 1) {
      (function (option, optionIndex) {
        option.addEventListener("click", function () {
          choose(option, optionIndex);
        });
      })(opts[i], i);
    }
  }

  function initQuiz() {
    var quiz = document.querySelector(".quiz");
    if (!quiz) return;

    var questions = quiz.querySelectorAll(".q");
    var state = {
      answered: new Set(),
      correct: 0,
      total: questions.length,
    };
    var scoreEl = quiz.querySelector(".quiz-head .score");

    function paint() {
      if (scoreEl) scoreEl.textContent = state.correct + " / " + state.total + " 正确";
    }
    paint();

    for (var i = 0; i < questions.length; i += 1) {
      makeQuestionHandler(quiz, questions[i], i, state, paint);
    }

    var reset = quiz.querySelector(".quiz-foot button.reset");
    if (reset) {
      reset.addEventListener("click", function () {
        state.answered = new Set();
        state.correct = 0;

        var marked = quiz.querySelectorAll(".opts li");
        for (var j = 0; j < marked.length; j += 1) {
          marked[j].classList.remove("correct", "wrong", "locked");
        }
        var explains = quiz.querySelectorAll(".explain");
        for (var k = 0; k < explains.length; k += 1) {
          explains[k].classList.remove("show");
        }
        var foot = quiz.querySelector(".quiz-foot .result");
        if (foot) foot.textContent = "";

        paint();
      });
    }

    var reveal = quiz.querySelector(".quiz-foot button.reveal");
    if (reveal) {
      reveal.addEventListener("click", function () {
        var explains = quiz.querySelectorAll(".explain");
        for (var j = 0; j < explains.length; j += 1) {
          explains[j].classList.add("show");
        }
      });
    }
  }

  /* ---------- 掌握勾选 ---------- */
  function initMastery() {
    var box = document.querySelector(".mastery input");
    if (!box) return;

    var slug = box.dataset.slug;
    box.checked = Boolean(done[slug]);

    box.addEventListener("change", function () {
      if (box.checked) {
        done[slug] = 1;
      } else {
        delete done[slug];
      }
      write(KEY_DONE, done);
      renderProgress();
      markCompleted(".sidebar a[data-slug]");
      markCompleted(".card[data-slug]");
    });
  }

  function refreshAll() {
    renderProgress();
    markCompleted(".sidebar a[data-slug]");
    markCompleted(".card[data-slug]");
  }

  document.addEventListener("DOMContentLoaded", function () {
    initNav();
    refreshAll();
    initQuiz();
    initMastery();
  });
})();
