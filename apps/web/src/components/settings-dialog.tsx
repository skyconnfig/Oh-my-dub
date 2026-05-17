"use client"

import { FormEvent, useEffect, useState } from "react"
import { Eye, EyeOff, RefreshCw, Settings } from "lucide-react"

import { useTranslation } from "@/lib/i18n"
import {
  getCookieInfo,
  getOpenAIModels,
  getOpenAISettings,
  getTtsSettings,
  getYtdlpSettings,
  saveCookie,
  saveOpenAISettings,
  saveTtsSettings,
  saveYtdlpSettings,
} from "@/lib/api"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"

type SettingsForm = {
  cookie: string
  baseUrl: string
  apiKey: string
  model: string
  translateConcurrency: string
  proxyPort: string
  engine: string
  gptSovitsApiUrl: string
}

const SAVED_API_KEY_MASK = "********"
const SAVED_COOKIE_MASK = "******** saved YouTube cookie ********"

const defaultSettings: SettingsForm = {
  cookie: "",
  baseUrl: "https://api.openai.com/v1",
  apiKey: "",
  model: "gpt-4o-mini",
  translateConcurrency: "50",
  proxyPort: "",
  engine: "voxcpm",
  gptSovitsApiUrl: "http://localhost:9880",
}

function uniqueModels(models: string[]) {
  return Array.from(new Set(models.map((model) => model.trim()).filter(Boolean)))
}

export function SettingsDialog() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [settings, setSettings] = useState(defaultSettings)
  const [message, setMessage] = useState("")
  const [modelOptions, setModelOptions] = useState<string[]>([])
  const [modelsLoaded, setModelsLoaded] = useState(false)
  const [modelsLoading, setModelsLoading] = useState(false)
  const [showApiKey, setShowApiKey] = useState(false)
  const [cookieDirty, setCookieDirty] = useState(false)
  const [apiKeyDirty, setApiKeyDirty] = useState(false)

  useEffect(() => {
    if (!open) return
    Promise.all([getCookieInfo(), getOpenAISettings(), getYtdlpSettings(), getTtsSettings()])
      .then(([cookie, openai, ytdlp, tts]) => {
        setSettings({
          cookie: cookie.exists ? SAVED_COOKIE_MASK : "",
          baseUrl: openai.base_url,
          apiKey: openai.has_api_key ? openai.api_key || SAVED_API_KEY_MASK : "",
          model: openai.model,
          translateConcurrency: openai.translate_concurrency || "50",
          proxyPort: ytdlp.proxy_port,
          engine: tts.engine,
          gptSovitsApiUrl: tts.gpt_sovits_api_url,
        })
        setModelOptions(uniqueModels([openai.model]))
        setModelsLoaded(false)
        setShowApiKey(false)
        setCookieDirty(false)
        setApiKeyDirty(false)
        setMessage(openai.has_api_key ? t("settings.keySaved") : "")
      })
      .catch((err) => setMessage(err.message))
  }, [open, t])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setMessage("")
    try {
      const cookie = cookieDirty ? await saveCookie(settings.cookie) : null
      const openai = await saveOpenAISettings({
        base_url: settings.baseUrl,
        api_key: apiKeyDirty ? settings.apiKey : "",
        model: settings.model,
        translate_concurrency: settings.translateConcurrency,
      })
      const ytdlp = await saveYtdlpSettings({ proxy_port: settings.proxyPort })
      const tts = await saveTtsSettings({
        engine: settings.engine,
        gpt_sovits_api_url: settings.gptSovitsApiUrl,
      })
      setMessage(t("settings.saved"))
      setSettings((current) => ({
        ...current,
        apiKey: openai.has_api_key ? openai.api_key || SAVED_API_KEY_MASK : "",
        cookie: cookieDirty ? (cookie?.exists ? SAVED_COOKIE_MASK : "") : current.cookie,
        translateConcurrency: openai.translate_concurrency || current.translateConcurrency,
        proxyPort: ytdlp.proxy_port,
        engine: tts.engine,
        gptSovitsApiUrl: tts.gpt_sovits_api_url,
      }))
      setCookieDirty(false)
      setApiKeyDirty(false)
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed to save settings")
    }
  }

  async function fetchModels() {
    setMessage("")
    setModelsLoading(true)
    try {
      const response = await getOpenAIModels({
        base_url: settings.baseUrl,
        api_key: apiKeyDirty ? settings.apiKey : "",
      })
      const models = uniqueModels([settings.model, ...response.models])
      setModelOptions(models)
      setModelsLoaded(true)
      setSettings((current) => ({ ...current, model: current.model || models[0] || "" }))
      setMessage(models.length ? `${models.length} ${t("settings.modelsLoaded")}` : t("settings.noModels"))
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed to load models")
    } finally {
      setModelsLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant="outline" />}>
        <Settings className="size-4" />
        {t("nav.settings")}
      </DialogTrigger>
      <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-hidden sm:max-w-2xl">
        <form onSubmit={submit} className="flex max-h-[calc(100dvh-4rem)] min-h-0 flex-col">
          <DialogHeader className="shrink-0 pr-8">
            <DialogTitle>{t("settings.title")}</DialogTitle>
            <DialogDescription>{t("settings.description")}</DialogDescription>
          </DialogHeader>
          <div className="mt-4 min-h-0 overflow-y-auto pr-1">
            <div className="grid gap-4 pb-4">
              <div className="grid gap-2">
                <Label htmlFor="cookie">{t("settings.youtubeCookie")}</Label>
                <Textarea
                  id="cookie"
                  value={settings.cookie}
                  onFocus={(event) => {
                    if (!cookieDirty && settings.cookie === SAVED_COOKIE_MASK) {
                      event.currentTarget.select()
                    }
                  }}
                  onChange={(event) => {
                    setCookieDirty(true)
                    setSettings((current) => ({
                      ...current,
                      cookie: event.target.value.replace(SAVED_COOKIE_MASK, ""),
                    }))
                  }}
                  placeholder={t("settings.cookiePlaceholder")}
                  className="min-h-44 max-h-[42dvh] overflow-auto font-mono text-xs leading-relaxed"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="proxyPort">{t("settings.proxyPort")}</Label>
                <Input
                  id="proxyPort"
                  inputMode="numeric"
                  value={settings.proxyPort}
                  onChange={(event) =>
                    setSettings((current) => ({ ...current, proxyPort: event.target.value }))
                  }
                  placeholder={t("settings.proxyPortPlaceholder")}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="engine">{t("settings.ttsEngine")}</Label>
                <Select
                  value={settings.engine}
                  onValueChange={(value) =>
                    setSettings((current) => ({ ...current, engine: value || current.engine }))
                  }
                >
                  <SelectTrigger id="engine">
                    <SelectValue placeholder={t("settings.ttsEngine")} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="voxcpm">{t("settings.ttsVoxCpm")}</SelectItem>
                    <SelectItem value="gpt_sovits">{t("settings.ttsGptSovits")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {settings.engine === "gpt_sovits" ? (
                <div className="grid gap-2">
                  <Label htmlFor="gptSovitsApiUrl">{t("settings.gptSovitsUrl")}</Label>
                  <Input
                    id="gptSovitsApiUrl"
                    value={settings.gptSovitsApiUrl}
                    onChange={(event) =>
                      setSettings((current) => ({ ...current, gptSovitsApiUrl: event.target.value }))
                    }
                    placeholder={t("settings.gptSovitsUrlPlaceholder")}
                  />
                  <p className="text-xs text-muted-foreground">
                    {t("settings.gptSovitsHint")}
                  </p>
                </div>
              ) : null}
              <div className="grid gap-2">
                <Label htmlFor="baseUrl">{t("settings.baseUrl")}</Label>
                <Input
                  id="baseUrl"
                  value={settings.baseUrl}
                  onChange={(event) =>
                    setSettings((current) => ({ ...current, baseUrl: event.target.value }))
                  }
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="apiKey">{t("settings.apiKey")}</Label>
                <div className="relative">
                  <Input
                    id="apiKey"
                    type={showApiKey ? "text" : "password"}
                    value={settings.apiKey}
                    onFocus={(event) => {
                      if (!apiKeyDirty && settings.apiKey === SAVED_API_KEY_MASK) {
                        event.currentTarget.select()
                      }
                    }}
                    onChange={(event) => {
                      setApiKeyDirty(true)
                      setSettings((current) => ({
                        ...current,
                        apiKey: event.target.value.replace(SAVED_API_KEY_MASK, ""),
                      }))
                    }}
                    placeholder={t("settings.apiKeyPlaceholder")}
                    className="pr-9"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    className="absolute top-0.5 right-0.5"
                    onClick={() => setShowApiKey((current) => !current)}
                  >
                    {showApiKey ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                    <span className="sr-only">{showApiKey ? t("settings.hideKey") : t("settings.showKey")}</span>
                  </Button>
                </div>
              </div>
              <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
                <div className="grid gap-2">
                  <Label htmlFor="model">{t("settings.model")}</Label>
                  {modelsLoaded && modelOptions.length > 0 ? (
                    <Select
                      value={settings.model}
                      onValueChange={(value) =>
                        setSettings((current) => ({ ...current, model: value || "" }))
                      }
                    >
                      <SelectTrigger id="model">
                        <SelectValue placeholder={t("settings.model")} />
                      </SelectTrigger>
                      <SelectContent>
                        {modelOptions.map((model) => (
                          <SelectItem key={model} value={model}>
                            {model}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Input
                      id="model"
                      value={settings.model}
                      onChange={(event) =>
                        setSettings((current) => ({ ...current, model: event.target.value }))
                      }
                    />
                  )}
                </div>
                <div className="grid gap-2 sm:self-end">
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={fetchModels}
                    disabled={modelsLoading || !settings.baseUrl.trim()}
                  >
                    <RefreshCw className="size-4" />
                    {modelsLoading ? t("settings.loading") : t("settings.getModels")}
                  </Button>
                </div>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="translateConcurrency">{t("settings.translateConcurrency")}</Label>
                <Input
                  id="translateConcurrency"
                  inputMode="numeric"
                  value={settings.translateConcurrency}
                  onChange={(event) =>
                    setSettings((current) => ({
                      ...current,
                      translateConcurrency: event.target.value.replace(/[^0-9]/g, ""),
                    }))
                  }
                  placeholder="50"
                />
                <p className="text-xs text-muted-foreground">
                  {t("settings.concurrencyHint")}
                </p>
              </div>
              {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}
            </div>
          </div>
          <DialogFooter className="shrink-0">
            <Button type="submit">{t("settings.save")}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
