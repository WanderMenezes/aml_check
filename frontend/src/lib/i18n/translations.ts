import en from "@/locales/en.json";
import pt from "@/locales/pt.json";

export type Locale = "pt" | "en";

export const translations = { pt, en } as const;

export type TranslationKey = keyof typeof pt;
