
import { createApp, ref, reactive, onMounted, onBeforeUnmount, watch } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';
import { DB } from './data.js';
import { apiInit, apiGenerate } from './infra/api.js';
import { createStore } from './app/store.js';
import { reducer, initialState } from './app/reducer.js';
import { selectViewModel } from './app/selectors.js';

// 3. 定义并导出主组件配置
export const AppConfig = {
  setup() {
    // --- 状态定义 ---
    const apiKey = ref('');
    const loading = ref(false);
    const history = ref([]);
    const errorMsg = ref('');
    const errorDetail = ref(null);
    const errorRequestId = ref("");
    const showErrorDetail = ref(false);
    const previewImage = ref(null);
    const hasSavedKey = ref(false);
    const currentViewImage = ref(null);
    const fileInput = ref(null);
    const finalPrompt = ref("");

    const store = createStore(reducer, initialState);

    // --- 表单状态（必须在 watch / syncFormFromStore 之前）---
    const form = reactive({
      style: '',
      aspectRatio: '',
      clothing: '',
      shot: '',
      accessory: '',
      body: '',
      cup: '',
      action: '',
      scene: '',
      effect: '',
      customText: ''
    });

    function syncFromStore() {
      const vm = selectViewModel(store.getState());
      loading.value = vm.loading;
      history.value = vm.history;
      errorMsg.value = vm.errorMsg;
      finalPrompt.value = vm.finalPrompt || "";
    }

    function syncFormFromStore() {
      const s = store.getState();
      const f = s.form || {};
      Object.keys(form).forEach((k) => {
        if (f[k] !== undefined) form[k] = f[k];
      });
    }

    let isSyncingForm = false;

    function syncFormFromStore() {
      const s = store.getState();
      const f = s.form || {};
      isSyncingForm = true;
      Object.keys(form).forEach((k) => {
        if (f[k] !== undefined) form[k] = f[k];
      });
      isSyncingForm = false;
    }

    watch(
      () => ({ ...form }),
      (newVal) => {
        if (isSyncingForm) return;
        store.dispatch({ type: "FORM_UPDATE", patch: newVal });
      },
      { deep: true }
    );

    store.subscribe(() => {
      syncFromStore();
      syncFormFromStore();
    });

    // ✅ 初次同步放这里（确保 form/finalPrompt 都已声明）
    syncFromStore();
    syncFormFromStore();


    // === 新增：画廊拖拽逻辑 ===
    const timelineRef = ref(null); // 绑定 DOM
    let isDown = false;
    let startX;
    let scrollLeft;
    const startDrag = (e) => {
      if (!timelineRef.value) return;
      isDown = true;
      startX = e.pageX - timelineRef.value.offsetLeft;
      scrollLeft = timelineRef.value.scrollLeft;
    };
    const stopDrag = () => {
      isDown = false;
    };
    const doDrag = (e) => {
      if (!isDown || !timelineRef.value) return;
      e.preventDefault();
      const x = e.pageX - timelineRef.value.offsetLeft;
      const walk = (x - startX) * 2;
      timelineRef.value.scrollLeft = scrollLeft - walk;
    };

    // === 新增：灵动岛通知逻辑 ===
    const notifyState = reactive({
      show: false,
      message: '',
      timer: null
    });
    const notify = (msg) => {
      // 如果有正在显示的，先清除
      if (notifyState.timer) clearTimeout(notifyState.timer);
      notifyState.message = msg;
      notifyState.show = true;

      // 1.5秒后自动消失
      notifyState.timer = setTimeout(() => {
        notifyState.show = false;
      }, 1500);
    };
    // --- 辅助函数 ---
    const clearFile = () => {
      previewImage.value = null;
      if (fileInput.value) fileInput.value.value = '';
    };
    function extractRequestId(text) {
      if (!text) return "";
      const m = String(text).match(/request id[:：]\s*([A-Za-z0-9_-]+)/i);
      return m ? m[1] : "";
    }
    async function handleBadResponse(res) {
      // reset（保持你原有行为一致）
      errorMsg.value = "";
      errorDetail.value = null;
      errorRequestId.value = "";
      showErrorDetail.value = false;
      const statusLine = `HTTP ${res.status}`;
      // 优先按 JSON 解析；失败再按 text
      try {
        const err = await res.json();
        const detail = err?.detail ?? err;
        errorDetail.value = detail;
        const bodyText =
          typeof detail === "string"
            ? detail
            : (detail?.body ?? JSON.stringify(detail));
        const rid = extractRequestId(bodyText);
        if (rid) errorRequestId.value = rid;
        const fallbackFlag =
          (typeof detail === "object" && detail?.fallback) ? "（已触发兼容重试）" : "";
        errorMsg.value = `${statusLine}${fallbackFlag}\n${bodyText}`;
      } catch (e) {
        const t = await res.text();
        errorDetail.value = t || null;
        errorRequestId.value = extractRequestId(t || "");
        errorMsg.value = `${statusLine}\n${t || "请求失败（无返回体）"}`;

      }
    }
    // --- 初始化 ---
    onMounted(async () => {
      store.dispatch({ type: "REQUEST_START" });
      try {
        const data = await apiInit();
        store.dispatch({ type: "INIT_SUCCESS", history: data.history || [] });
        // init 成功后结束 loading（因为 INIT_SUCCESS 不会关 loading）
        hasSavedKey.value = !!data.has_saved_key;
        apiKey.value = "";
      } catch (e) {
        const msg = e?.message || String(e);
        store.dispatch({ type: "REQUEST_ERROR", message: msg });
        console.error("Init failed", e);
      }
    });

    onBeforeUnmount(() => {
      if (notifyState.timer) clearTimeout(notifyState.timer);
    });

    // --- 事件处理 ---
    const handleFileUpload = (event) => {
      const file = event.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (e) => previewImage.value = e.target.result;
        reader.readAsDataURL(file);
      }
    };

    const generate = async () => {
      if (loading.value) return; // 防连点并发
      if (!apiKey.value && !hasSavedKey.value) {
        errorMsg.value = "Please enter API Key";
        return;
      }

      store.dispatch({ type: "REQUEST_START" });

      // 清理 UI 错误展示（保留你原有行为）
      errorMsg.value = "";
      errorDetail.value = null;
      errorRequestId.value = "";
      showErrorDetail.value = false;

      try {
        const payload = {
          ...(apiKey.value ? { api_key: apiKey.value } : {}),
          prompt: finalPrompt.value,
          style_tag: form.style,
          aspect_ratio: form.aspectRatio,
          ref_image: previewImage.value,
          metadata: { ...form }
        };

        const res = await apiGenerate(payload);

        if (!res.ok) {
          await handleBadResponse(res);
          // 关键：让 store 结束 loading
          store.dispatch({ type: "REQUEST_ERROR", message: errorMsg.value || `HTTP ${res.status}` });
          return;
        }

        const newItem = await res.json();

        // 关键：不要直接 history.unshift，交给 reducer 统一处理
        store.dispatch({ type: "GENERATE_SUCCESS", record: newItem });

        // 这是 UI 独有状态，继续在这里更新没问题
        currentViewImage.value = newItem;

      } catch (e) {
        const msg = e?.message || String(e);
        errorMsg.value = msg;
        store.dispatch({ type: "REQUEST_ERROR", message: msg });
      }
    };


    const downloadImage = (item) => {
      const link = document.createElement('a');
      link.href = item.url;
      link.download = item.filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    };

    // 复制提示词（画廊用）：复制成功后用灵动岛提示
    const copyPrompt = async (text) => {
      const content = String(text ?? "");

      try {
        // 优先使用 Clipboard API
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(content);
          notify("命令序列已复制");
          return;
        }
        throw new Error("clipboard_api_unavailable");
      } catch (e) {
        // 兼容模式：textarea + execCommand
        try {
          const ta = document.createElement("textarea");
          ta.value = content;
          ta.setAttribute("readonly", "");
          ta.style.position = "fixed";
          ta.style.left = "-9999px";
          ta.style.top = "0";
          document.body.appendChild(ta);
          ta.select();
          document.execCommand("copy");
          document.body.removeChild(ta);

          notify("命令序列已复制");
        } catch (e2) {
          notify("复制失败，请手动复制");
        }
      }
    };


    const restoreSettings = (item) => {
      if (item.metadata) {
        Object.keys(form).forEach(key => {
          if (item.metadata[key] !== undefined) {
            form[key] = item.metadata[key];
          }
        });
        // 🔴 替换 alert，改为 notify
        notify("神经连接已恢复");
      } else {
        notify("Data Corrupted: Legacy Ver.");
      }
    };

    // --- 导出给模板 ---
    return {
      apiKey, hasSavedKey, loading, history,
      errorMsg, errorDetail, errorRequestId, showErrorDetail,
      previewImage, form, db: DB, finalPrompt, currentViewImage,
      fileInput, clearFile, timelineRef, notifyState, notify,
      handleFileUpload, generate, downloadImage, copyPrompt, restoreSettings, startDrag, stopDrag, doDrag
    };
  }
};