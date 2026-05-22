export type Lang = "zh" | "en"

export type TranslationKey =
  | "app.title"
  | "app.description"
  | "nav.settings"
  | "nav.back"
  // Home page
  | "home.createTask"
  | "home.youtubeLabel"
  | "home.youtubePlaceholder"
  | "home.bilibiliLabel"
  | "home.bilibiliPlaceholder"
  | "home.create"
  | "home.submitting"
  | "home.taskHistory"
  | "home.noTasks"
  | "home.queuedRunning"
  | "home.status.queued"
  | "home.status.running"
  | "home.status.succeeded"
  | "home.status.failed"
  // Settings
  | "settings.title"
  | "settings.description"
  | "settings.youtubeCookie"
  | "settings.cookiePlaceholder"
  | "settings.proxyPort"
  | "settings.proxyPortPlaceholder"
  | "settings.ttsEngine"
  | "settings.ttsVoxCpm"
  | "settings.ttsGptSovits"
  | "settings.ttsIndexTts"
  | "settings.ttsCosyVoice"
  | "settings.ttsSuperTonic"
  | "settings.ttsMelo"
  | "settings.gptSovitsUrl"
  | "settings.gptSovitsUrlPlaceholder"
  | "settings.gptSovitsHint"
  | "settings.baseUrl"
  | "settings.apiKey"
  | "settings.apiKeyPlaceholder"
  | "settings.showKey"
  | "settings.hideKey"
  | "settings.model"
  | "settings.getModels"
  | "settings.loading"
  | "settings.translateConcurrency"
  | "settings.concurrencyHint"
  | "settings.save"
  | "settings.saved"
  | "settings.keySaved"
  | "settings.modelsLoaded"
  | "settings.noModels"
  | "settings.cookieSaved"
  // Task detail
  | "task.detail"
  | "task.overview"
  | "task.finalVideo"
  | "task.play"
  | "task.download"
  | "task.rerun"
  | "task.rerunTask"
  | "task.rerunning"
  | "task.confirmRerun"
  | "task.confirmRerunBtn"
  | "task.rerunDialogTitle"
  | "task.rerunDialogDesc"
  | "task.rerunHint"
  | "task.resume"
  | "task.resumeTask"
  | "task.resuming"
  | "task.resumeHint"
  | "task.delete"
  | "task.deleteTask"
  | "task.deleting"
  | "task.confirmDelete"
  | "task.confirmDeleteBtn"
  | "task.deleteDialogTitle"
  | "task.deleteDialogDesc"
  | "task.deleteHint"
  | "task.cannotDeleteRunning"
  | "task.runningHint"
  | "task.log"
  | "task.runLog"
  | "task.logPlaceholder"
  | "task.stage"
  | "task.stages"
  | "task.started"
  | "task.completed"
  | "task.duration"
  | "task.error"
  | "task.noVideo"
  | "task.loading"
  | "task.loadingTask"
  | "task.titleField"
  | "task.urlField"
  | "task.idField"
  | "task.createdField"
  | "task.sessionField"
  | "task.waiting"
  | "task.dangerZone"
  | "task.cancel"
  | "task.queuedRunning"
  | "task.failed"
  | "task.succeeded"

export const translations: Record<TranslationKey, Record<Lang, string>> = {
  "app.title": { zh: "OhMyDub", en: "OhMyDub" },
  "app.description": { zh: "视频翻译配音工具", en: "Video dubbing console" },
  "nav.settings": { zh: "设置", en: "Settings" },
  "nav.back": { zh: "返回", en: "Back" },
  // Home
  "home.createTask": { zh: "创建新任务", en: "Create new task" },
  "home.youtubeLabel": { zh: "YouTube 链接（英文 → 中文）", en: "YouTube URL (English → Chinese)" },
  "home.youtubePlaceholder": { zh: "https://www.youtube.com/watch?v=...", en: "https://www.youtube.com/watch?v=..." },
  "home.bilibiliLabel": { zh: "Bilibili 链接（中文 → 英文）", en: "Bilibili URL (Chinese → English)" },
  "home.bilibiliPlaceholder": { zh: "https://www.bilibili.com/video/BV...", en: "https://www.bilibili.com/video/BV..." },
  "home.create": { zh: "创建任务", en: "Create task" },
  "home.submitting": { zh: "提交中", en: "Submitting" },
  "home.taskHistory": { zh: "任务历史", en: "Task history" },
  "home.noTasks": { zh: "暂无任务，请在上方提交 YouTube 或 Bilibili 链接开始。", en: "No tasks yet. Submit a YouTube or Bilibili URL above to start." },
  "home.queuedRunning": { zh: "个任务排队/运行中", en: "task(s) queued / running" },
  "home.status.queued": { zh: "排队中", en: "queued" },
  "home.status.running": { zh: "运行中", en: "running" },
  "home.status.succeeded": { zh: "已完成", en: "succeeded" },
  "home.status.failed": { zh: "失败", en: "failed" },
  // Settings
  "settings.title": { zh: "运行时设置", en: "Runtime settings" },
  "settings.description": { zh: "设置由后端 FastAPI 存储。", en: "Stored locally by the FastAPI backend." },
  "settings.youtubeCookie": { zh: "YouTube Cookie", en: "YouTube cookie" },
  "settings.cookiePlaceholder": { zh: "粘贴 Netscape 格式的 Cookie 内容", en: "Paste Netscape cookie content" },
  "settings.proxyPort": { zh: "yt-dlp 代理端口", en: "yt-dlp proxy port" },
  "settings.proxyPortPlaceholder": { zh: "7890", en: "7890" },
  "settings.ttsEngine": { zh: "TTS 引擎", en: "TTS engine" },
  "settings.ttsVoxCpm": { zh: "VoxCPM", en: "VoxCPM" },
  "settings.ttsGptSovits": { zh: "GPT-SoVITS", en: "GPT-SoVITS" },
  "settings.ttsIndexTts": { zh: "IndexTTS-2", en: "IndexTTS-2" },
  "settings.ttsCosyVoice": { zh: "CosyVoice2", en: "CosyVoice2" },
  "settings.ttsSuperTonic": { zh: "SuperTonic", en: "SuperTonic" },
  "settings.ttsMelo": { zh: "MeloTTS", en: "MeloTTS" },
  "settings.gptSovitsUrl": { zh: "GPT-SoVITS API 地址", en: "GPT-SoVITS API URL" },
  "settings.gptSovitsUrlPlaceholder": { zh: "http://localhost:9880", en: "http://localhost:9880" },
  "settings.gptSovitsHint": { zh: "api_v2.py 端点。启动方式：python api_v2.py -a 127.0.0.1 -p 9880", en: "The api_v2.py endpoint. Start with: python api_v2.py -a 127.0.0.1 -p 9880" },
  "settings.baseUrl": { zh: "OpenAI 接口地址", en: "OpenAI base URL" },
  "settings.apiKey": { zh: "OpenAI API 密钥", en: "OpenAI API key" },
  "settings.apiKeyPlaceholder": { zh: "留空则保留已有密钥", en: "Leave blank to keep existing key" },
  "settings.showKey": { zh: "显示密钥", en: "Show API key" },
  "settings.hideKey": { zh: "隐藏密钥", en: "Hide API key" },
  "settings.model": { zh: "模型", en: "Model" },
  "settings.getModels": { zh: "获取模型列表", en: "Get models" },
  "settings.loading": { zh: "加载中", en: "Loading" },
  "settings.translateConcurrency": { zh: "翻译并发数", en: "Translate concurrency" },
  "settings.concurrencyHint": { zh: "翻译阶段的并行 OpenAI 请求数。如果 API 允许可以提高此值。", en: "Parallel OpenAI requests during the translate stage. Increase if your provider allows it." },
  "settings.save": { zh: "保存设置", en: "Save settings" },
  "settings.saved": { zh: "设置已保存。", en: "Settings saved." },
  "settings.keySaved": { zh: "OpenAI 密钥已保存。", en: "OpenAI key is saved." },
  "settings.modelsLoaded": { zh: "个模型已加载。", en: "models loaded." },
  "settings.noModels": { zh: "未返回模型。", en: "No models returned." },
  "settings.cookieSaved": { zh: "Cookie 已保存。", en: "Cookie saved." },
  // Task detail
  "task.detail": { zh: "任务详情", en: "Task details" },
  "task.overview": { zh: "任务概览", en: "Task overview" },
  "task.finalVideo": { zh: "最终视频", en: "Final video" },
  "task.play": { zh: "播放", en: "Play" },
  "task.download": { zh: "下载", en: "Download" },
  "task.rerun": { zh: "重新运行", en: "Rerun" },
  "task.rerunTask": { zh: "重新运行任务", en: "Rerun task" },
  "task.rerunning": { zh: "重新运行中", en: "Rerunning" },
  "task.confirmRerun": { zh: "确认重新运行？这将清空之前的输出。", en: "Rerun? This will clear previous output." },
  "task.confirmRerunBtn": { zh: "确认重新运行", en: "Confirm rerun" },
  "task.rerunDialogTitle": { zh: "重新运行此任务？", en: "Rerun this task?" },
  "task.rerunDialogDesc": { zh: "现有日志、会话目录和最终视频将被删除，然后同一链接将以相同的任务 ID 重新进入队列。", en: "Existing log, session directory and final video will be deleted, then the same URL is re-queued under the same task id." },
  "task.rerunHint": { zh: "清除会话目录，从头重新运行此链接。", en: "Wipe the session directory and run this URL again from scratch." },
  "task.resume": { zh: "恢复", en: "Resume" },
  "task.resumeTask": { zh: "恢复任务", en: "Resume task" },
  "task.resuming": { zh: "恢复中", en: "Resuming" },
  "task.resumeHint": { zh: "从失败的阶段恢复，已完成的步骤将从缓存复用。", en: "Resume from the failed stage. Already-succeeded stages will be reused from cache." },
  "task.delete": { zh: "删除", en: "Delete" },
  "task.deleteTask": { zh: "删除任务", en: "Delete task" },
  "task.deleting": { zh: "删除中", en: "Deleting" },
  "task.confirmDelete": { zh: "确认删除此任务及其所有文件？", en: "Delete this task and all its files?" },
  "task.confirmDeleteBtn": { zh: "确认删除", en: "Confirm delete" },
  "task.deleteDialogTitle": { zh: "删除此任务？", en: "Delete this task?" },
  "task.deleteDialogDesc": { zh: "此操作将永久删除任务记录、日志文件和整个会话目录，无法撤销。", en: "This permanently removes the task record, its log file, and the entire session directory. This action cannot be undone." },
  "task.deleteHint": { zh: "删除此任务、运行日志及 workfolder/ 下的整个会话目录。", en: "Delete this task, its run log, and the entire session directory under workfolder/." },
  "task.cannotDeleteRunning": { zh: "无法删除运行中的任务。", en: "Cannot delete a running task." },
  "task.runningHint": { zh: "运行中的任务无法重新运行或删除，请等待完成或失败。", en: "Running tasks cannot be rerun or deleted. Wait until it finishes or fails." },
  "task.log": { zh: "日志", en: "Log" },
  "task.runLog": { zh: "运行日志", en: "Run log" },
  "task.logPlaceholder": { zh: "任务开始后将显示日志。", en: "Logs will appear once the task starts." },
  "task.stage": { zh: "阶段", en: "Stage" },
  "task.stages": { zh: "处理阶段", en: "Stages" },
  "task.started": { zh: "开始时间", en: "Started" },
  "task.completed": { zh: "完成时间", en: "Completed" },
  "task.duration": { zh: "耗时", en: "Duration" },
  "task.error": { zh: "错误信息", en: "Error" },
  "task.noVideo": { zh: "视频暂不可用。", en: "Video is not available yet." },
  "task.loading": { zh: "加载中", en: "Loading" },
  "task.loadingTask": { zh: "加载任务中…", en: "Loading task…" },
  "task.titleField": { zh: "标题", en: "Title" },
  "task.urlField": { zh: "链接", en: "URL" },
  "task.idField": { zh: "任务 ID", en: "Task ID" },
  "task.createdField": { zh: "创建时间", en: "Created" },
  "task.sessionField": { zh: "会话路径", en: "Session" },
  "task.waiting": { zh: "等待中", en: "Waiting" },
  "task.dangerZone": { zh: "危险操作", en: "Danger zone" },
  "task.cancel": { zh: "取消", en: "Cancel" },
  "task.queuedRunning": { zh: "排队/运行中", en: "queued/running" },
  "task.failed": { zh: "失败", en: "Failed" },
  "task.succeeded": { zh: "已完成", en: "Succeeded" },
}
