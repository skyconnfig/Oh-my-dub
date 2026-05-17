"use client"

import Link from "next/link"
import { ArrowLeft } from "lucide-react"

import { Button } from "@/components/ui/button"
import { SettingsDialog } from "@/components/settings-dialog"
import { LanguageSwitcher } from "@/components/language-switcher"

export function AppHeader({ backHref }: { backHref?: string }) {
  return (
    <header className="flex flex-col gap-4 border-b border-[#00aeec]/25 pb-5 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-3">
        {backHref ? (
          <Button
            variant="ghost"
            size="icon-sm"
            nativeButton={false}
            render={<Link href={backHref} aria-label="Back" />}
          >
            <ArrowLeft className="size-4" />
          </Button>
        ) : null}
        <Link href="/" className="flex items-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/ohmy-dub-logo.svg"
            alt="OhMyDub"
            className="h-9 w-auto sm:h-11"
          />
        </Link>
      </div>
      <div className="flex items-center gap-2">
        <LanguageSwitcher />
        <SettingsDialog />
      </div>
    </header>
  )
}
