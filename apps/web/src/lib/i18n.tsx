"use client"

import { createContext, useCallback, useContext, useEffect, useState } from "react"
import type { Lang, TranslationKey } from "./translations"
import { translations } from "./translations"

type I18nContextType = {
  lang: Lang
  setLang: (lang: Lang) => void
  t: (key: TranslationKey, fallback?: string) => string
}

const I18nContext = createContext<I18nContextType | null>(null)

const STORAGE_KEY = "ohmy-dub-lang"

function detectLang(): Lang {
  if (typeof window === "undefined") return "en"
  const stored = localStorage.getItem(STORAGE_KEY) as Lang | null
  if (stored === "zh" || stored === "en") return stored
  return navigator.language.startsWith("zh") ? "zh" : "en"
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en")

  useEffect(() => {
    setLangState(detectLang())
  }, [])

  const setLang = useCallback((next: Lang) => {
    setLangState(next)
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      /* noop */
    }
  }, [])

  const t: I18nContextType["t"] = useCallback(
    (key, fallback) => {
      return translations[key]?.[lang] ?? fallback ?? key
    },
    [lang],
  )

  return (
    <I18nContext.Provider value={{ lang, setLang, t }}>
      {children}
    </I18nContext.Provider>
  )
}

export function useTranslation() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error("useTranslation must be used within I18nProvider")
  return ctx
}
