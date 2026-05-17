"use client"

import { useTranslation } from "@/lib/i18n"
import type { Lang } from "@/lib/translations"

const options: { value: Lang; label: string }[] = [
  { value: "zh", label: "中" },
  { value: "en", label: "EN" },
]

export function LanguageSwitcher() {
  const { lang, setLang } = useTranslation()

  return (
    <div
      role="radiogroup"
      aria-label="Language"
      className="flex items-center rounded-lg border border-border/60 bg-muted/30 p-0.5 text-xs font-medium transition-colors duration-200"
    >
      {options.map((opt) => {
        const active = lang === opt.value
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => setLang(opt.value)}
            className={`
              relative cursor-pointer rounded-md px-2.5 py-1 tracking-wide transition-all duration-200 select-none
              ${
                active
                  ? "bg-white text-foreground shadow-xs ring-1 ring-border/40"
                  : "text-muted-foreground hover:text-foreground"
              }
            `}
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}
