import { app } from "/scripts/app.js";

function detectLocale() {
  // RunningHub stores locale in localStorage as "AGL.Locale"
  try {
    const aglLocale = (window.top || window).localStorage.getItem("AGL.Locale");
    if (aglLocale) return aglLocale.startsWith("zh") ? "zh" : "en";
  } catch (_) {}

  // Fallback: standard ComfyUI reads navigator.language
  return (navigator.language || "en").startsWith("zh") ? "zh" : "en";
}

app.registerExtension({
  name: "RH.OpenAPI.Panel",
  _i18n: null,
  _locale: "en",

  rh: {
    type: "nodes",
    nodes: "all",
  },

  // init() runs BEFORE node registration — load translations here
  async init() {
    this._locale = detectLocale();
    try {
      const resp = await fetch(
        "/extensions/ComfyUI_RH_OpenAPI/js/panel_i18n.json"
      );
      if (resp.ok) this._i18n = await resp.json();
    } catch (e) {
      console.warn("[RH OpenAPI] Failed to load panel_i18n.json");
    }
  },

  // Called for each node BEFORE it is registered into LiteGraph.
  // Modifying nodeData.display_name here makes node.title use the translated name.
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (!this._i18n?.nodes) return;
    const nameMap = this._i18n.nodes[this._locale];
    if (nameMap && nameMap[nodeData.name]) {
      nodeData.display_name = nameMap[nodeData.name];
    }
  },

  // Called before node defs are pushed into the Vue nodeDefStore.
  // Patching display_name here makes the Vue search/library show translated names.
  beforeRegisterVueAppNodeDefs(nodeDefArray) {
    if (!this._i18n?.nodes) return;
    const nameMap = this._i18n.nodes[this._locale];
    if (!nameMap) return;
    for (const def of nodeDefArray) {
      if (nameMap[def.name]) {
        def.display_name = nameMap[def.name];
      }
    }
  },

  // Patch title when new node instances are created on the canvas
  nodeCreated(node) {
    if (!this._i18n?.nodes) return;
    const nameMap = this._i18n.nodes[this._locale];
    if (nameMap && nameMap[node.type]) {
      node.title = nameMap[node.type];
    }
  },

  // Patch title for nodes loaded from a saved workflow.
  // This fires AFTER node.configure() restores saved properties,
  // so it overrides any stale title persisted in the workflow JSON.
  loadedGraphNode(node) {
    if (!this._i18n?.nodes) return;
    const nameMap = this._i18n.nodes[this._locale];
    if (nameMap && nameMap[node.type]) {
      node.title = nameMap[node.type];
    }
  },

  async setup() {
    const locale = this._locale;
    const i18n = this._i18n || {};

    // Also inject into vue-i18n so that st() calls work for our nodes
    try {
      const vueRoot = document.querySelector("#vue-app")?.__vue_app__;
      const i18nInst = vueRoot?.config?.globalProperties?.$i18n;
      if (i18nInst?.mergeLocaleMessage && i18n.nodes) {
        for (const lang of ["en", "zh"]) {
          const names = i18n.nodes[lang];
          if (!names) continue;
          const payload = {};
          for (const [k, v] of Object.entries(names)) {
            payload[k] = { display_name: v };
          }
          i18nInst.mergeLocaleMessage(lang, { nodeDefs: payload });
        }
        console.log("[RH OpenAPI] Injected translations into vue-i18n");
      }
    } catch (e) {
      console.warn("[RH OpenAPI] vue-i18n injection skipped:", e.message);
    }

    // --- Panel UI ---

    const fallbackUI = {
      zh: {
        search_placeholder: "🔍 搜索节点...",
        stats: "共 {categories} 个分类，{nodes} 个节点 | Ctrl+Shift+R",
        no_results: "😕 未找到匹配的节点",
        tooltip: "RunningHub 节点面板 (Ctrl+Shift+R)",
      },
      en: {
        search_placeholder: "🔍 Search nodes...",
        stats: "{categories} categories, {nodes} nodes | Ctrl+Shift+R",
        no_results: "😕 No matching nodes found",
        tooltip: "RunningHub Node Panel (Ctrl+Shift+R)",
      },
    };

    const fallbackCategories = {
      zh: {
        "RHArt Image": "🖼️ RH 全能图像", "RHArt Video": "🎬 RH 全能视频",
        "RHArt Video G": "🎥 RH 全能视频G", "RHArt Text": "📝 RH 多模态文本",
        "Kling": "🎞️ 可灵 Kling", "Vidu": "📹 生数 Vidu",
        "Wan": "🌀 通义万相 Wan", "MiniMax": "🐚 MiniMax 海螺",
        "Seedream": "🌱 Seedream 图像", "Seedance": "💃 Seedance 视频",
        "Youchuan": "🚢 有船 Midjourney", "Audio": "🎵 音频生成",
        "Hunyuan3D": "🧊 混元 3D", "HiTem3D": "🔷 HiTem 3D",
        "TopazLabs": "💎 Topaz Labs",
        "Alibaba": "🎨 阿里 通义万相 Qwen",
        "PixVerse": "🎬 PixVerse 可灵替代",
        "SkyReels": "🎥 昆仑 SkyReels",
        "Higgsfield": "🎭 Higgsfield",
      },
      en: {
        "RHArt Image": "🖼️ RHArt Image", "RHArt Video": "🎬 RHArt Video",
        "RHArt Video G": "🎥 RHArt Video G", "RHArt Text": "📝 RHArt Text",
        "Kling": "🎞️ Kling", "Vidu": "📹 Vidu",
        "Wan": "🌀 Wan", "MiniMax": "🐚 MiniMax",
        "Seedream": "🌱 Seedream", "Seedance": "💃 Seedance",
        "Youchuan": "🚢 Midjourney", "Audio": "🎵 Audio",
        "Hunyuan3D": "🧊 Hunyuan 3D", "HiTem3D": "🔷 HiTem 3D",
        "TopazLabs": "💎 Topaz Labs",
        "Alibaba": "🎨 Alibaba Qwen",
        "PixVerse": "🎬 PixVerse",
        "SkyReels": "🎥 SkyReels",
        "Higgsfield": "🎭 Higgsfield",
      },
    };

    const categoryNameMap = (i18n.categories && i18n.categories[locale])
      || fallbackCategories[locale] || {};
    const nodeNameMap = (i18n.nodes && i18n.nodes[locale]) || {};
    const t = (key) =>
      ((i18n.ui && i18n.ui[locale]) || fallbackUI[locale] || fallbackUI.en)[key] || key;

    const categoryOrder = [
      "RHArt Image", "RHArt Video", "RHArt Video G", "RHArt Text",
      "Kling", "Vidu", "Wan", "MiniMax",
      "Seedream", "Seedance", "Youchuan", "Audio",
      "Hunyuan3D", "HiTem3D", "TopazLabs", "Alibaba",
      "PixVerse", "SkyReels", "Higgsfield",
    ];

    let allowedNodes = null;
    try {
      const resp = await fetch("/extensions/ComfyUI_RH_OpenAPI/js/node_list.json");
      if (resp.ok) allowedNodes = new Set(await resp.json());
    } catch (e) {
      console.warn("[RH OpenAPI] Failed to load node_list.json");
    }

    const discoverNodes = () => {
      const categories = {};

      for (const [nodeType, nodeClass] of Object.entries(LiteGraph.registered_node_types)) {
        if (allowedNodes && !allowedNodes.has(nodeType)) continue;
        const category = nodeClass.category;
        if (!category || !category.toLowerCase().startsWith("runninghub/")) continue;

        const categoryName = category.split("/").slice(1).join("/");
        const displayCategory = categoryNameMap[categoryName] || categoryName;

        if (!categories[categoryName]) {
          categories[categoryName] = { display: displayCategory, nodes: [] };
        }

        const displayName = nodeNameMap[nodeType]
          || nodeClass.display_name || nodeClass.title || nodeType;
        categories[categoryName].nodes.push({ name: nodeType, display: displayName });
      }

      const sorted = {};
      for (const key of categoryOrder) {
        if (categories[key]) sorted[key] = categories[key];
      }
      for (const key of Object.keys(categories)) {
        if (!sorted[key]) sorted[key] = categories[key];
      }
      return sorted;
    };

    const debounce = (func, wait) => {
      let timeout;
      return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func(...args), wait);
      };
    };

    const getPanelAwareNodePosition = (node, panelEl) => {
      const fallback = Array.isArray(app.canvas?.graph_mouse)
        ? [...app.canvas.graph_mouse]
        : [200, 200];

      const canvasEl = app.canvas?.canvas;
      const convertCanvasToOffset = app.canvas?.convertCanvasToOffset?.bind(app.canvas);
      if (!canvasEl || !convertCanvasToOffset) return fallback;

      const canvasRect = canvasEl.getBoundingClientRect();
      const panelRect = panelEl?.getBoundingClientRect?.();
      const panelOverlap = panelRect
        ? Math.max(0, Math.min(canvasRect.width, panelRect.right - canvasRect.left))
        : 0;
      const padding = 24;
      const visibleLeft = Math.min(canvasRect.width - padding, panelOverlap + padding);
      const visibleRight = Math.max(visibleLeft + padding, canvasRect.width - padding);
      const visibleTop = padding;
      const visibleBottom = Math.max(visibleTop + padding, canvasRect.height - padding);

      const targetCanvasPos = [
        visibleLeft + (visibleRight - visibleLeft) * 0.5,
        visibleTop + (visibleBottom - visibleTop) * 0.5,
      ];
      const targetGraphPos = convertCanvasToOffset(targetCanvasPos);
      const nodeWidth = node?.size?.[0] || 0;
      const nodeHeight = node?.size?.[1] || 0;
      const minGraphX = convertCanvasToOffset([visibleLeft, 0])[0];
      const maxGraphX = convertCanvasToOffset([visibleRight, 0])[0] - nodeWidth;
      const minGraphY = convertCanvasToOffset([0, visibleTop])[1];
      const maxGraphY = convertCanvasToOffset([0, visibleBottom])[1] - nodeHeight;
      const clamp = (value, min, max) => {
        if (max < min) return min;
        return Math.min(Math.max(value, min), max);
      };

      return [
        clamp(targetGraphPos[0] - nodeWidth * 0.5, minGraphX, maxGraphX),
        clamp(targetGraphPos[1] - nodeHeight * 0.5, minGraphY, maxGraphY),
      ];
    };

    app.extensionManager.registerSidebarTab({
      id: "rh-openapi-panel",
      icon: "pi pi-cloud",
      title: "RunningHub OpenAPI",
      tooltip: t("tooltip"),
      type: "custom",
      render: (el) => {
        el.style.cssText = `
          padding: 12px;
          color: inherit;
          font-family: inherit;
          height: 100%;
          overflow-y: auto;
          box-sizing: border-box;
        `;

        const closeSidebar = () => {
          for (const icon of document.querySelectorAll(".pi-cloud")) {
            const btn = icon.closest("button, [role='button']");
            if (btn) { btn.click(); return; }
          }
          const legacy = document.querySelector('[data-id="rh-openapi-panel"]');
          if (legacy) legacy.click();
        };

        const header = document.createElement("div");
        header.style.cssText = `
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
          padding-bottom: 8px;
          border-bottom: 1px solid rgba(128,128,128,0.2);
        `;

        const headerTitle = document.createElement("span");
        headerTitle.style.cssText = "font-size:14px;font-weight:600;opacity:0.85;";
        headerTitle.textContent = "RunningHub OpenAPI";

        const closeBtn = document.createElement("button");
        closeBtn.textContent = "\u00d7";
        closeBtn.style.cssText = "background:none;border:none;color:inherit;opacity:0.4;cursor:pointer;font-size:20px;line-height:1;transition:opacity 0.2s;";
        closeBtn.addEventListener("mouseenter", () => { closeBtn.style.opacity = "0.9"; });
        closeBtn.addEventListener("mouseleave", () => { closeBtn.style.opacity = "0.4"; });
        closeBtn.addEventListener("click", closeSidebar);

        header.append(headerTitle, closeBtn);
        el.appendChild(header);

        const searchContainer = document.createElement("div");
        searchContainer.style.cssText = "margin-bottom:12px;position:relative;";

        const searchInput = document.createElement("input");
        searchInput.type = "text";
        searchInput.placeholder = t("search_placeholder");
        searchInput.style.cssText = `
          width:100%;
          padding:8px 32px 8px 10px;
          background:rgba(128,128,128,0.08);
          border:1px solid rgba(128,128,128,0.2);
          border-radius:6px;
          color:inherit;
          font-size:13px;
          box-sizing:border-box;
          outline:none;
          transition:border-color 0.2s;
        `;
        searchInput.addEventListener("focus", () => { searchInput.style.borderColor = "rgba(128,128,128,0.5)"; });
        searchInput.addEventListener("blur", () => { searchInput.style.borderColor = "rgba(128,128,128,0.2)"; });

        const clearBtn = document.createElement("span");
        clearBtn.textContent = "×";
        clearBtn.style.cssText = `
          position:absolute;
          right:8px;
          top:50%;
          transform:translateY(-50%);
          color:inherit;
          opacity:0.4;
          cursor:pointer;
          font-size:16px;
          display:none;
          transition:opacity 0.2s;
        `;
        clearBtn.addEventListener("mouseenter", () => { clearBtn.style.opacity = "0.9"; });
        clearBtn.addEventListener("mouseleave", () => { clearBtn.style.opacity = "0.4"; });

        searchContainer.append(searchInput, clearBtn);
        el.appendChild(searchContainer);

        const statsBar = document.createElement("div");
        statsBar.style.cssText = "font-size:11px;margin-bottom:10px;text-align:center;opacity:0.4;";
        el.appendChild(statsBar);

        const nodesContainer = document.createElement("div");
        nodesContainer.id = "rh-nodes-container";
        el.appendChild(nodesContainer);

        const allNodes = discoverNodes();

        let totalNodes = 0;
        for (const cat of Object.values(allNodes)) totalNodes += cat.nodes.length;
        statsBar.textContent = t("stats")
          .replace("{categories}", Object.keys(allNodes).length)
          .replace("{nodes}", totalNodes);

        const renderNodes = (filter = "") => {
          nodesContainer.innerHTML = "";
          let hasResults = false;

          for (const [catKey, catData] of Object.entries(allNodes)) {
            const filteredItems = filter
              ? catData.nodes.filter(item =>
                  item.display.toLowerCase().includes(filter.toLowerCase()) ||
                  item.name.toLowerCase().includes(filter.toLowerCase())
                )
              : catData.nodes;

            if (filteredItems.length === 0) continue;
            hasResults = true;

            const categoryDiv = document.createElement("div");
            categoryDiv.style.marginBottom = "8px";

            const title = document.createElement("div");
            title.textContent = `${filter ? "\u25bc" : "\u25b6"} ${catData.display} (${filteredItems.length})`;
            title.style.cssText = `
              font-size: 13px;
              font-weight: 600;
              padding: 8px 10px;
              background: rgba(128,128,128,0.06);
              border-radius: 4px;
              cursor: pointer;
              user-select: none;
              transition: background 0.15s;
            `;
            title.addEventListener("mouseenter", () => {
              title.style.background = "rgba(128,128,128,0.12)";
            });
            title.addEventListener("mouseleave", () => {
              title.style.background = "rgba(128,128,128,0.06)";
            });

            const container = document.createElement("div");
            container.className = "rh-items-container";
            container.style.cssText = `
              display: ${filter ? "block" : "none"};
              margin-top: 6px;
              padding-left: 4px;
            `;

            filteredItems.forEach(({ name, display }) => {
              const btn = document.createElement("div");
              btn.textContent = display;
              btn.title = name;
              btn.style.cssText = `
                padding: 6px 12px;
                margin-bottom: 2px;
                cursor: pointer;
                font-size: 12px;
                border-radius: 4px;
                opacity: 0.75;
                transition: background 0.15s, opacity 0.15s;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
              `;
              btn.addEventListener("mouseenter", () => {
                btn.style.background = "rgba(128,128,128,0.12)";
                btn.style.opacity = "1";
              });
              btn.addEventListener("mouseleave", () => {
                btn.style.background = "transparent";
                btn.style.opacity = "0.75";
              });
              btn.addEventListener("click", () => {
                const node = LiteGraph.createNode(name);
                if (node) {
                  node.pos = getPanelAwareNodePosition(node, el);
                  app.graph.add(node);
                  node.title = display;
                  app.canvas.selectNode(node);
                  app.graph.setDirtyCanvas(true, true);
                  btn.style.background = "rgba(128,128,128,0.2)";
                  btn.style.opacity = "1";
                  setTimeout(() => {
                    btn.style.background = "transparent";
                    btn.style.opacity = "0.75";
                  }, 200);
                }
              });
              container.appendChild(btn);
            });

            title.addEventListener("click", () => {
              if (!filter) {
                nodesContainer.querySelectorAll(".rh-items-container").forEach(c => {
                  if (c !== container) {
                    c.style.display = "none";
                    const ti = c.previousSibling;
                    if (ti && ti.textContent) {
                      const m = ti.textContent.match(/^[▶▼]\s*(.+?)\s*\(\d+\)/);
                      if (m) {
                        const count = ti.textContent.match(/\(\d+\)/);
                        ti.textContent = `▶ ${m[1]} ${count ? count[0] : ""}`;
                      }
                    }
                  }
                });
                const isOpen = container.style.display === "block";
                container.style.display = isOpen ? "none" : "block";
                const m = title.textContent.match(/^[▶▼]\s*(.+?)\s*\(\d+\)/);
                if (m) {
                  const count = title.textContent.match(/\(\d+\)/);
                  title.textContent = isOpen
                    ? `▶ ${m[1]} ${count ? count[0] : ""}`
                    : `▼ ${m[1]} ${count ? count[0] : ""}`;
                }
              }
            });

            categoryDiv.append(title, container);
            nodesContainer.appendChild(categoryDiv);
          }

          if (!hasResults) {
            nodesContainer.innerHTML = `
              <div style="text-align:center;padding:20px;font-size:13px;opacity:0.4;">
                ${t("no_results")}
              </div>
            `;
          }
        };

        renderNodes();

        const handleSearch = debounce((value) => {
          clearBtn.style.display = value ? "block" : "none";
          renderNodes(value);
        }, 300);

        searchInput.addEventListener("input", (e) => handleSearch(e.target.value));

        clearBtn.addEventListener("click", () => {
          searchInput.value = "";
          clearBtn.style.display = "none";
          renderNodes("");
        });
      }
    });

    document.addEventListener("keydown", (e) => {
      if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === "r") {
        e.preventDefault();
        e.stopPropagation();
        for (const icon of document.querySelectorAll(".pi-cloud")) {
          const btn = icon.closest("button, [role='button']");
          if (btn) { btn.click(); return; }
        }
        const legacy = document.querySelector('[data-id="rh-openapi-panel"]');
        if (legacy) legacy.click();
      }
    });

    console.log(`[RH OpenAPI] Panel loaded (locale: ${locale})`);
  }
});
